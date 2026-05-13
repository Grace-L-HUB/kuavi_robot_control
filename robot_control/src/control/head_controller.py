"""
头部注视控制器

通过 /robot_head_motion_data ROS topic 控制机器人头部的偏航角和俯仰角，
用于抓取时低头观察目标、搬运时正视前方等场景。
"""
import time
import logging

try:
    import rospy
    ROS_AVAILABLE = True
except ImportError:
    ROS_AVAILABLE = False

# 尝试导入 Kuavo 自定义消息类型
try:
    from kuavo_sdk.msg import robotHeadMotionData
    KUAVO_HEAD_MSG = True
except ImportError:
    robotHeadMotionData = None
    KUAVO_HEAD_MSG = False

logger = logging.getLogger(__name__)


class HeadController:
    """机器人头部注视控制器

    通过发布 /robot_head_motion_data 话题控制头部运动。
    消息包含 joint_data = [yaw, pitch]：
      - yaw:   偏航角，范围 [-30, 30] 度，正值=左转
      - pitch: 俯仰角，范围 [-25, 25] 度，正值=抬头（负值=低头）
    """

    TOPIC = '/robot_head_motion_data'
    YAW_MIN, YAW_MAX = -30.0, 30.0
    PITCH_MIN, PITCH_MAX = -25.0, 25.0
    DEFAULT_SETTLE_TIME = 0.5  # 发布后等待稳定时间（秒）

    def __init__(self, config: dict = None):
        """初始化 ROS 发布者

        Args:
            config: 可选配置字典，可包含 'head' 键定义自定义参数
        """
        self._publisher = None
        self._settle_time = self.DEFAULT_SETTLE_TIME

        if config:
            head_config = config.get("head", {})
            if isinstance(head_config, dict):
                self._settle_time = head_config.get("settle_time", self.DEFAULT_SETTLE_TIME)

        if not ROS_AVAILABLE:
            logger.warning("ROS not available; head controller will be non-functional")
            return

        try:
            if not rospy.core.is_initialized():
                rospy.init_node('head_controller', anonymous=True)

            if KUAVO_HEAD_MSG:
                self._publisher = rospy.Publisher(
                    self.TOPIC, robotHeadMotionData, queue_size=10
                )
                logger.info("Head controller initialized with kuavo_sdk message type")
            else:
                # 回退方案：使用 Float64MultiArray
                from std_msgs.msg import Float64MultiArray
                self._publisher = rospy.Publisher(
                    self.TOPIC, Float64MultiArray, queue_size=10
                )
                logger.warning("Head controller using Float64MultiArray fallback "
                               "(kuavo_sdk.msg.robotHeadMotionData not available)")

        except Exception as e:
            logger.error(f"Failed to initialize head controller: {e}")
            self._publisher = None

    def _clamp(self, value: float, min_val: float, max_val: float) -> float:
        """限幅"""
        return max(min_val, min(max_val, value))

    def set_gaze(self, yaw: float, pitch: float, wait: bool = True) -> bool:
        """设置头部偏航角和俯仰角

        Args:
            yaw: 偏航角（度），[-30, 30]，正值=左转
            pitch: 俯仰角（度），[-25, 25]，正值=抬头
            wait: 是否等待稳定时间

        Returns:
            bool: 成功返回 True
        """
        if self._publisher is None:
            logger.warning("Head publisher not initialized, skipping gaze command")
            return False

        yaw = self._clamp(yaw, self.YAW_MIN, self.YAW_MAX)
        pitch = self._clamp(pitch, self.PITCH_MIN, self.PITCH_MAX)

        try:
            if KUAVO_HEAD_MSG:
                msg = robotHeadMotionData()
                msg.joint_data = [yaw, pitch]
            else:
                from std_msgs.msg import Float64MultiArray
                msg = Float64MultiArray()
                msg.data = [yaw, pitch]

            self._publisher.publish(msg)
            logger.info(f"Head gaze set to yaw={yaw:.1f}, pitch={pitch:.1f}")

            if wait and ROS_AVAILABLE:
                rospy.sleep(self._settle_time)

            return True
        except Exception as e:
            logger.error(f"Error setting head gaze: {e}")
            return False

    def look_forward(self) -> bool:
        """头部正视前方（yaw=0, pitch=0）"""
        return self.set_gaze(0.0, 0.0)

    def look_down(self, pitch: float = -20.0) -> bool:
        """头部低头观察抓取区域

        Args:
            pitch: 俯仰角（度），默认 -20 度
        """
        return self.set_gaze(0.0, pitch)

    def look_at_hand(self, hand: str = "left") -> bool:
        """注视指定手的工作区域

        Args:
            hand: "left" 或 "right"
        """
        if hand == "left":
            return self.set_gaze(15.0, -15.0)
        elif hand == "right":
            return self.set_gaze(-15.0, -15.0)
        else:
            logger.error(f"Invalid hand: {hand}. Use 'left' or 'right'")
            return False

    def look_at_target(self, yaw: float, pitch: float) -> bool:
        """注视指定方向的目标

        Args:
            yaw: 目标方向偏航角（度）
            pitch: 目标方向俯仰角（度）
        """
        return self.set_gaze(yaw, pitch)
