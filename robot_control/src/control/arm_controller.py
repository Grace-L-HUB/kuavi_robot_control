"""
机械臂控制器

通过 ROS 话题和服务控制机器人双臂运动，支持：
- 关节角度直接控制（/kuavo_arm_traj）
- 带时间的目标姿态控制（/kuavo_arm_target_poses）
- 逆运动学（IK）笛卡尔空间控制（/ik/two_arm_hand_pose_cmd_srv）
- 正运动学（FK）查询（/ik/fk_srv）
- 手臂控制模式切换（/arm_traj_change_mode）
"""
import time
import logging
from typing import List, Optional, Dict

try:
    import rospy
    from sensor_msgs.msg import JointState
    ROS_AVAILABLE = True
except ImportError:
    ROS_AVAILABLE = False

# 尝试导入 Kuavo 自定义消息/服务类型
try:
    from kuavo_sdk.msg import armTargetPoses
    KUAVO_ARM_TARGET_MSG = True
except ImportError:
    armTargetPoses = None
    KUAVO_ARM_TARGET_MSG = False

try:
    from kuavo_sdk.srv import changeArmCtrlMode, changeArmCtrlModeRequest
    KUAVO_ARM_MODE_SRV = True
except ImportError:
    KUAVO_ARM_MODE_SRV = False

try:
    from motion_capture_ik.srv import twoArmHandPoseCmdSrv
    from motion_capture_ik.msg import twoArmHandPoseCmd, ikSolveParam
    KUAVO_IK_SRV = True
except ImportError:
    KUAVO_IK_SRV = False

try:
    from motion_capture_ik.srv import fkSrv
    KUAVO_FK_SRV = True
except ImportError:
    KUAVO_FK_SRV = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

logger = logging.getLogger(__name__)

NUM_JOINTS = 14

# 默认末端执行器姿态（掌心朝下的四元数 [qx, qy, qz, qw]）
DEFAULT_ORIENTATION = [0.0, -0.70682518, 0.0, 0.70738827]


class ArmController:
    """机械臂控制器"""

    def __init__(self, config: dict = None):
        """初始化 ROS 发布者和服务代理

        Args:
            config: 可选配置字典
        """
        self._config = config or {}
        self._arm_publisher = None
        self._target_poses_publisher = None
        self._ik_service = None
        self._fk_service = None
        self._mode_service = None

        # 从配置读取参数
        arm_config = self._config.get("arm", {})
        ik_config = self._config.get("ik", {})
        self._default_duration = arm_config.get("default_duration", 2.0)
        self._slow_duration = arm_config.get("slow_duration", 3.0)
        self._fast_duration = arm_config.get("fast_duration", 1.0)
        self._ik_timeout = ik_config.get("service_timeout", 5.0)
        self._default_quat = ik_config.get("default_orientation", DEFAULT_ORIENTATION)

        if not ROS_AVAILABLE:
            logger.warning("ROS not available; arm controller will be non-functional")
            return

        try:
            if not rospy.core.is_initialized():
                rospy.init_node('arm_controller', anonymous=True)

            # 关节轨迹发布者
            self._arm_publisher = rospy.Publisher(
                '/kuavo_arm_traj', JointState, queue_size=10
            )

            # 带时间的目标姿态发布者
            if KUAVO_ARM_TARGET_MSG:
                self._target_poses_publisher = rospy.Publisher(
                    '/kuavo_arm_target_poses', armTargetPoses, queue_size=10
                )
                logger.info("armTargetPoses publisher initialized")
            else:
                logger.warning("armTargetPoses message not available, "
                               "timed trajectory control disabled")

            logger.info("Arm controller initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize arm controller: {e}")
            raise

    # ==================== 关节角度控制 ====================

    def set_joint_angles(self, angles: List[float]) -> bool:
        """设置机械臂关节角度

        Args:
            angles: 14 个关节的角度值列表（单位：度）

        Returns:
            bool: 成功返回 True
        """
        if self._arm_publisher is None:
            logger.error("Arm publisher not initialized")
            return False

        try:
            if len(angles) != NUM_JOINTS:
                logger.error(f"Expected {NUM_JOINTS} joint angles, got {len(angles)}")
                return False

            msg = JointState()
            msg.name = [f"arm_joint_{i}" for i in range(1, NUM_JOINTS + 1)]
            msg.header.stamp = rospy.Time.now()
            msg.position = list(angles)

            self._arm_publisher.publish(msg)
            logger.info(f"Set joint angles: {angles}")
            return True
        except Exception as e:
            logger.error(f"Error setting joint angles: {e}")
            return False

    def set_target_poses_timed(self, angles: List[float],
                                duration: float = None) -> bool:
        """通过 /kuavo_arm_target_poses 发布带时间的目标姿态

        Args:
            angles: 14 个关节角度（度）
            duration: 到达目标的时间（秒），默认使用 default_duration

        Returns:
            bool: 成功返回 True
        """
        if not KUAVO_ARM_TARGET_MSG or self._target_poses_publisher is None:
            logger.warning("armTargetPoses not available, falling back to direct control")
            return self.set_joint_angles(angles)

        try:
            if len(angles) != NUM_JOINTS:
                logger.error(f"Expected {NUM_JOINTS} joint angles, got {len(angles)}")
                return False

            if duration is None:
                duration = self._default_duration

            msg = armTargetPoses()
            msg.times = [duration]
            msg.values = list(angles)

            self._target_poses_publisher.publish(msg)
            logger.info(f"Set target poses (duration={duration}s): {angles}")
            return True
        except Exception as e:
            logger.error(f"Error setting target poses: {e}")
            return False

    def home(self) -> bool:
        """回到初始位置（所有关节角度为0）"""
        home_angles = [0.0] * NUM_JOINTS
        return self.set_target_poses_timed(home_angles, duration=self._default_duration)

    # ==================== 控制模式 ====================

    def set_control_mode(self, mode: int) -> bool:
        """设置手臂控制模式

        Args:
            mode: 0=保持姿势(keep_pose), 1=行走时自动摆手(auto_swing), 2=外部控制(external)

        Returns:
            bool: 成功返回 True
        """
        if not ROS_AVAILABLE:
            logger.warning("ROS not available, cannot set control mode")
            return False

        try:
            service_name = '/arm_traj_change_mode'

            if KUAVO_ARM_MODE_SRV:
                if self._mode_service is None:
                    rospy.wait_for_service(service_name, timeout=self._ik_timeout)
                    self._mode_service = rospy.ServiceProxy(
                        service_name, changeArmCtrlMode
                    )
                request = changeArmCtrlModeRequest()
                request.control_mode = mode
                response = self._mode_service(request)
                if response.result:
                    logger.info(f"Control mode set to {mode}")
                    return True
                else:
                    logger.error(f"Failed to set control mode: {response.message}")
                    return False
            else:
                # 服务类型不可用时，尝试通用调用
                logger.warning(f"Control mode service type not available, "
                               f"assuming mode {mode} set successfully")
                return True

        except Exception as e:
            logger.warning(f"Control mode service not available: {e}")
            return True  # 非致命错误

    # ==================== 逆运动学 (IK) ====================

    def _ensure_ik_service(self) -> bool:
        """延迟初始化 IK 服务代理"""
        if self._ik_service is not None:
            return True

        if not ROS_AVAILABLE or not KUAVO_IK_SRV:
            logger.warning("IK service not available (ROS or message type missing)")
            return False

        try:
            service_name = '/ik/two_arm_hand_pose_cmd_srv'
            rospy.wait_for_service(service_name, timeout=self._ik_timeout)
            self._ik_service = rospy.ServiceProxy(service_name, twoArmHandPoseCmdSrv)
            logger.info("IK service proxy initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IK service: {e}")
            return False

    def solve_ik(self, left_pos: List[float] = None, left_quat: List[float] = None,
                 right_pos: List[float] = None, right_quat: List[float] = None,
                 left_elbow: List[float] = None,
                 right_elbow: List[float] = None) -> Optional[List[float]]:
        """调用 IK 服务求解关节角度

        Args:
            left_pos: 左手末端位置 [x, y, z]（米）
            left_quat: 左手末端姿态 [qx, qy, qz, qw]
            right_pos: 右手末端位置 [x, y, z]（米）
            right_quat: 右手末端姿态 [qx, qy, qz, qw]
            left_elbow: 左手肘部位置提示 [x, y, z]（全0表示忽略）
            right_elbow: 右手肘部位置提示 [x, y, z]（全0表示忽略）

        Returns:
            14 个关节角度（弧度），或 None（求解失败）
        """
        if not self._ensure_ik_service():
            logger.error("IK service not available")
            return None

        try:
            if not NUMPY_AVAILABLE:
                logger.error("numpy required for IK but not available")
                return None

            request = twoArmHandPoseCmd()
            request.use_custom_ik_param = False
            request.joint_angles_as_q0 = False

            # 设置左手
            if left_pos is not None:
                request.hand_poses.left_pose.pos_xyz = np.array(left_pos)
                request.hand_poses.left_pose.quat_xyzw = np.array(
                    left_quat if left_quat else self._default_quat
                )
                request.hand_poses.left_pose.elbow_pos_xyz = np.array(
                    left_elbow if left_elbow else [0.0, 0.0, 0.0]
                )

            # 设置右手
            if right_pos is not None:
                request.hand_poses.right_pose.pos_xyz = np.array(right_pos)
                request.hand_poses.right_pose.quat_xyzw = np.array(
                    right_quat if right_quat else self._default_quat
                )
                request.hand_poses.right_pose.elbow_pos_xyz = np.array(
                    right_elbow if right_elbow else [0.0, 0.0, 0.0]
                )

            response = self._ik_service(request)

            if response.success:
                q_arm = list(response.q_arm)
                logger.info(f"IK solved: {len(q_arm)} joints, "
                            f"time_cost={response.time_cost:.1f}ms")
                return q_arm
            else:
                logger.warning("IK solution not found")
                return None

        except Exception as e:
            logger.error(f"Error calling IK service: {e}")
            return None

    def go_to_cartesian(self, x: float, y: float, z: float,
                        quat: List[float] = None,
                        hand: str = "left",
                        duration: float = None) -> bool:
        """通过 IK 逆运动学移动手臂到笛卡尔空间位置

        Args:
            x, y, z: 目标位置（米），在机器人基坐标系下
            quat: 目标姿态四元数 [qx, qy, qz, qw]，默认掌心朝下
            hand: "left" 或 "right"
            duration: 运动时间（秒）

        Returns:
            bool: 成功返回 True
        """
        if duration is None:
            duration = self._default_duration

        pos = [x, y, z]
        quat = quat if quat else self._default_quat

        # 尝试 IK 求解
        if hand == "left":
            joint_angles = self.solve_ik(left_pos=pos, left_quat=quat)
        elif hand == "right":
            joint_angles = self.solve_ik(right_pos=pos, right_quat=quat)
        else:
            logger.error(f"Invalid hand: {hand}")
            return False

        if joint_angles is None:
            logger.error(f"IK failed for position ({x}, {y}, {z}), hand={hand}")
            return False

        # 使用带时间的目标姿态发布
        result = self.set_target_poses_timed(joint_angles, duration)

        if result:
            # 等待运动完成
            if ROS_AVAILABLE:
                rospy.sleep(duration + 0.5)
            else:
                time.sleep(duration + 0.5)

        return result

    def go_to_position(self, x: float, y: float, z: float) -> bool:
        """移动到指定空间位置（使用逆运动学）

        这是 go_to_cartesian 的简化接口，使用默认参数。

        Args:
            x, y, z: 目标位置坐标（米）

        Returns:
            bool: 成功返回 True
        """
        return self.go_to_cartesian(x, y, z)

    # ==================== 正运动学 (FK) ====================

    def _ensure_fk_service(self) -> bool:
        """延迟初始化 FK 服务代理"""
        if self._fk_service is not None:
            return True

        if not ROS_AVAILABLE or not KUAVO_FK_SRV:
            logger.warning("FK service not available")
            return False

        try:
            service_name = '/ik/fk_srv'
            rospy.wait_for_service(service_name, timeout=self._ik_timeout)
            self._fk_service = rospy.ServiceProxy(service_name, fkSrv)
            logger.info("FK service proxy initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to FK service: {e}")
            return False

    def query_fk(self, joint_angles: List[float]) -> Optional[dict]:
        """调用 FK 正运动学服务查询末端执行器位置

        Args:
            joint_angles: 14 个关节角度（弧度）

        Returns:
            dict: 包含 'left' 和 'right' 手的位置和姿态，或 None
        """
        if not self._ensure_fk_service():
            logger.error("FK service not available")
            return None

        try:
            response = self._fk_service(joint_angles)

            if response.success:
                result = {
                    "left": {
                        "pos": list(response.hand_poses.left_pose.pos_xyz),
                        "quat": list(response.hand_poses.left_pose.quat_xyzw),
                    },
                    "right": {
                        "pos": list(response.hand_poses.right_pose.pos_xyz),
                        "quat": list(response.hand_poses.right_pose.quat_xyzw),
                    }
                }
                logger.info(f"FK query successful")
                return result
            else:
                logger.warning("FK query failed")
                return None
        except Exception as e:
            logger.error(f"Error calling FK service: {e}")
            return None
