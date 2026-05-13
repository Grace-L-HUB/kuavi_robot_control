"""
夹爪控制器

通过 ROS 服务和话题控制机器人二指夹爪（Leju Claw），支持：
- 夹爪开合控制（/control_robot_leju_claw 服务）
- 夹爪状态实时监控（/leju_claw_state 话题订阅）
- 抓取验证（等待 state=3 确认抓住物体）

夹爪状态码：
  -1: Error    错误
   0: Unknown  未知（初始化默认）
   1: Moving   移动中
   2: Reached  已到达目标位置
   3: Grabbed  已抓住物体
"""
import time
import threading
import logging
from typing import Optional

try:
    import rospy
    ROS_AVAILABLE = True
except ImportError:
    ROS_AVAILABLE = False

# 尝试导入 Kuavo 服务类型
try:
    from kuavo_sdk.srv import controlLejuClaw, controlLejuClawRequest
    KUAVO_CLAW_SRV = True
except ImportError:
    KUAVO_CLAW_SRV = False

# 尝试导入 Kuavo 夹爪状态消息
try:
    from kuavo_sdk.msg import lejuClawState
    KUAVO_CLAW_STATE_MSG = True
except ImportError:
    KUAVO_CLAW_STATE_MSG = False

logger = logging.getLogger(__name__)

# 夹爪状态常量
CLAW_STATE_ERROR = -1
CLAW_STATE_UNKNOWN = 0
CLAW_STATE_MOVING = 1
CLAW_STATE_REACHED = 2
CLAW_STATE_GRABBED = 3


class GripperController:
    """机器人夹爪控制器"""

    def __init__(self, config: dict = None):
        """初始化 ROS 服务代理和状态订阅

        Args:
            config: 可选配置字典
        """
        self._config = config or {}
        self._gripper_service = None
        self._state_subscriber = None
        self._state_lock = threading.Lock()

        # 夹爪实时状态
        self._claw_state = {
            "left": {"state": CLAW_STATE_UNKNOWN, "position": 0, "velocity": 0, "effort": 0},
            "right": {"state": CLAW_STATE_UNKNOWN, "position": 0, "velocity": 0, "effort": 0},
        }

        # 从配置读取默认参数
        grasp_config = self._config.get("actions", {}).get("gripper", {})
        self._default_position = grasp_config.get("default_close_position", 90)
        self._default_velocity = grasp_config.get("default_velocity", 50)
        self._default_effort = grasp_config.get("default_effort", 1.5)

        if not ROS_AVAILABLE:
            logger.warning("ROS not available; gripper controller will be non-functional")
            return

        try:
            if not rospy.core.is_initialized():
                rospy.init_node('gripper_controller', anonymous=True)

            # 初始化夹爪控制服务
            service_name = '/control_robot_leju_claw'
            if KUAVO_CLAW_SRV:
                rospy.wait_for_service(service_name, timeout=10.0)
                self._gripper_service = rospy.ServiceProxy(service_name, controlLejuClaw)
                logger.info("Gripper control service initialized")
            else:
                logger.warning("controlLejuClaw service type not available")

            # 订阅夹爪状态话题
            if KUAVO_CLAW_STATE_MSG:
                self._state_subscriber = rospy.Subscriber(
                    '/leju_claw_state', lejuClawState,
                    self._claw_state_callback
                )
                logger.info("Claw state subscriber initialized")
            else:
                logger.warning("lejuClawState message not available; "
                               "grasp verification will use time-based fallback")

            logger.info("Gripper controller initialized successfully")
        except rospy.ROSException as e:
            logger.error(f"Failed to initialize gripper controller: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error initializing gripper controller: {e}")
            raise

    def _claw_state_callback(self, msg):
        """处理夹爪状态订阅消息

        Args:
            msg: lejuClawState 消息，包含 state[2] 和 data
        """
        with self._state_lock:
            try:
                if hasattr(msg, 'state') and len(msg.state) >= 2:
                    self._claw_state["left"]["state"] = int(msg.state[0])
                    self._claw_state["right"]["state"] = int(msg.state[1])

                if hasattr(msg, 'data'):
                    data = msg.data
                    if hasattr(data, 'position') and len(data.position) >= 2:
                        self._claw_state["left"]["position"] = data.position[0]
                        self._claw_state["right"]["position"] = data.position[1]
                    if hasattr(data, 'velocity') and len(data.velocity) >= 2:
                        self._claw_state["left"]["velocity"] = data.velocity[0]
                        self._claw_state["right"]["velocity"] = data.velocity[1]
                    if hasattr(data, 'effort') and len(data.effort) >= 2:
                        self._claw_state["left"]["effort"] = data.effort[0]
                        self._claw_state["right"]["effort"] = data.effort[1]
            except Exception as e:
                logger.error(f"Error parsing claw state message: {e}")

    # ==================== 基础控制 ====================

    def close(self, position: int = None, velocity: int = None,
              effort: float = None) -> bool:
        """闭合双侧夹爪

        Args:
            position: 闭合程度 0-100 (0=张开, 100=完全闭合)
            velocity: 速度 0-100
            effort: 力矩限制 1.0-2.0A

        Returns:
            bool: 成功返回 True
        """
        if position is None:
            position = self._default_position
        if velocity is None:
            velocity = self._default_velocity
        if effort is None:
            effort = self._default_effort

        return self._send_command(
            names=['left_claw', 'right_claw'],
            positions=[position, position],
            velocities=[velocity, velocity],
            efforts=[effort, effort]
        )

    def close_hand(self, hand: str = "left", position: int = None,
                   velocity: int = None, effort: float = None) -> bool:
        """闭合指定侧夹爪

        Args:
            hand: "left" 或 "right"
            position: 闭合程度 0-100
            velocity: 速度 0-100
            effort: 力矩 1.0-2.0A
        """
        if position is None:
            position = self._default_position
        if velocity is None:
            velocity = self._default_velocity
        if effort is None:
            effort = self._default_effort

        claw_name = f"{hand}_claw"
        if claw_name not in ('left_claw', 'right_claw'):
            logger.error(f"Invalid hand: {hand}. Use 'left' or 'right'")
            return False

        return self._send_command(
            names=[claw_name],
            positions=[position],
            velocities=[velocity],
            efforts=[effort]
        )

    def open(self) -> bool:
        """完全张开双侧夹爪"""
        return self._send_command(
            names=['left_claw', 'right_claw'],
            positions=[0, 0],
            velocities=[self._default_velocity, self._default_velocity],
            efforts=[self._default_effort, self._default_effort]
        )

    def open_hand(self, hand: str = "left") -> bool:
        """完全张开指定侧夹爪"""
        claw_name = f"{hand}_claw"
        if claw_name not in ('left_claw', 'right_claw'):
            logger.error(f"Invalid hand: {hand}")
            return False
        return self._send_command(
            names=[claw_name],
            positions=[0],
            velocities=[self._default_velocity],
            efforts=[self._default_effort]
        )

    def _send_command(self, names: list, positions: list,
                      velocities: list, efforts: list) -> bool:
        """发送夹爪控制指令"""
        if self._gripper_service is None:
            logger.error("Gripper service not initialized")
            return False

        try:
            req = controlLejuClawRequest()
            req.data.name = names
            req.data.position = positions
            req.data.velocity = velocities
            req.data.effort = efforts

            response = self._gripper_service(req)
            if response.success:
                logger.info(f"Gripper command sent: {names} pos={positions}")
                return True
            else:
                logger.error(f"Gripper command failed: {response.message}")
                return False
        except Exception as e:
            logger.error(f"Error sending gripper command: {e}")
            return False

    # ==================== 状态查询 ====================

    def get_state(self) -> dict:
        """获取夹爪实时状态

        Returns:
            dict: 包含 'left' 和 'right' 的状态字典，每个包含：
                  state (int), position (float), velocity (float), effort (float)
        """
        with self._state_lock:
            # 返回深拷贝
            return {
                "left": dict(self._claw_state["left"]),
                "right": dict(self._claw_state["right"]),
            }

    def get_claw_state_code(self, hand: str = "left") -> int:
        """获取指定手的夹爪状态码

        Returns:
            -1=Error, 0=Unknown, 1=Moving, 2=Reached, 3=Grabbed
        """
        with self._state_lock:
            return self._claw_state.get(hand, {}).get("state", CLAW_STATE_UNKNOWN)

    def is_grasping(self, hand: str = "left") -> bool:
        """检查指定手是否已抓住物体"""
        return self.get_claw_state_code(hand) == CLAW_STATE_GRABBED

    # ==================== 抓取验证 ====================

    def wait_for_grasp(self, hand: str = "left", timeout: float = 3.0) -> bool:
        """阻塞等待抓取确认

        轮询夹爪状态，直到状态为 GRABBED(3) 或超时。

        Args:
            hand: "left" 或 "right"
            timeout: 超时时间（秒）

        Returns:
            bool: 抓取确认返回 True，超时或错误返回 False
        """
        if not KUAVO_CLAW_STATE_MSG or self._state_subscriber is None:
            # 回退：基于时间的估算
            logger.warning("Claw state not available, using time-based fallback "
                           f"(waiting {timeout * 0.3:.1f}s)")
            if ROS_AVAILABLE:
                rospy.sleep(timeout * 0.3)
            else:
                time.sleep(timeout * 0.3)
            return True  # 假设成功

        start_time = time.time()
        poll_interval = 0.1  # 10Hz 轮询

        while time.time() - start_time < timeout:
            state_code = self.get_claw_state_code(hand)

            if state_code == CLAW_STATE_GRABBED:
                logger.info(f"Grasp confirmed for {hand} hand "
                            f"(took {time.time() - start_time:.2f}s)")
                return True

            if state_code == CLAW_STATE_ERROR:
                logger.error(f"Claw error detected for {hand} hand")
                return False

            if ROS_AVAILABLE:
                rospy.sleep(poll_interval)
            else:
                time.sleep(poll_interval)

        logger.warning(f"Grasp verification timed out for {hand} hand "
                       f"(waited {timeout}s, last state={self.get_claw_state_code(hand)})")
        return False

    def wait_for_position(self, hand: str = "left", timeout: float = 3.0) -> bool:
        """等待夹爪到达目标位置

        Args:
            hand: "left" 或 "right"
            timeout: 超时时间（秒）

        Returns:
            bool: 到达返回 True
        """
        if not KUAVO_CLAW_STATE_MSG or self._state_subscriber is None:
            if ROS_AVAILABLE:
                rospy.sleep(1.0)
            else:
                time.sleep(1.0)
            return True

        start_time = time.time()
        while time.time() - start_time < timeout:
            state_code = self.get_claw_state_code(hand)
            if state_code in (CLAW_STATE_REACHED, CLAW_STATE_GRABBED):
                return True
            if state_code == CLAW_STATE_ERROR:
                return False
            if ROS_AVAILABLE:
                rospy.sleep(0.1)
            else:
                time.sleep(0.1)

        return False
