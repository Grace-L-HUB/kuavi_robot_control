"""
机器人统一控制器

整合底盘、手臂、夹爪、头部等所有子系统，
通过 ActionExecutor 状态机驱动抓取递送动作。
"""
from ..communication.robot_api import WooshApi
from .gripper_controller import GripperController
from .arm_controller import ArmController
from .head_controller import HeadController
from .pose_library import PoseLibrary
from .action_model import ActionExecutor
import logging

logger = logging.getLogger(__name__)


class RobotController:
    """机器人统一控制器"""

    def __init__(self, config: dict):
        """初始化控制器

        Args:
            config: 配置字典，包含 IP、端口、动作参数等
        """
        self.config = config
        self.chassis = None           # WooshApi 实例
        self.gripper = None           # GripperController 实例
        self.arm = None               # ArmController 实例
        self.head = None              # HeadController 实例
        self.pose_library = None      # PoseLibrary 实例
        self.action_executor = None   # ActionExecutor 实例

    def initialize(self) -> bool:
        """初始化所有连接和子系统

        Returns:
            bool: 底盘连接成功返回 True（其它子系统为可选）
        """
        try:
            # 初始化底盘控制（必需）
            websocket_config = self.config.get("robot", {}).get("websocket", {})
            ip = websocket_config.get("ip", "192.168.1.100")
            port = websocket_config.get("port", 8080)
            url = f"ws://{ip}:{port}/"

            self.chassis = WooshApi(url)
            if not self.chassis.connect():
                logger.error("Failed to connect to chassis")
                return False

            # 初始化夹爪控制器（可选）
            try:
                self.gripper = GripperController(self.config)
            except Exception as e:
                logger.warning(f"Failed to initialize gripper: {e}")
                self.gripper = None

            # 初始化机械臂控制器（可选）
            try:
                self.arm = ArmController(self.config)
            except Exception as e:
                logger.warning(f"Failed to initialize arm: {e}")
                self.arm = None

            # 初始化头部控制器（可选）
            try:
                self.head = HeadController(self.config)
            except Exception as e:
                logger.warning(f"Failed to initialize head: {e}")
                self.head = None

            # 初始化姿态库
            self.pose_library = PoseLibrary(self.config)

            # 初始化动作执行器
            self.action_executor = ActionExecutor(self, self.config)

            logger.info("Robot controller initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing robot controller: {e}")
            return False

    # ==================== 底盘控制 ====================

    def move_to(self, x: float, y: float, theta: float = 0) -> bool:
        """移动底盘到指定位置"""
        if not self.chassis:
            logger.error("Chassis not initialized")
            return False
        try:
            return self.chassis.robot_go_to(x, y, theta)
        except Exception as e:
            logger.error(f"Error moving to position: {e}")
            return False

    # ==================== 抓取递送（状态机驱动） ====================

    def pick_object(self, x: float, y: float, z: float,
                    hand: str = "left", **kwargs) -> bool:
        """在指定位置抓取物体（状态机驱动）

        Args:
            x, y, z: 物体在机器人坐标系下的位置
            hand: 使用哪只手 "left" / "right"
            **kwargs: 可选参数 grasp_width, grasp_effort

        Returns:
            bool: 抓取成功返回 True
        """
        if not self.action_executor:
            logger.error("Action executor not initialized")
            return False
        return self.action_executor.execute_pickup(
            (x, y, z), hand=hand, **kwargs
        )

    def place_object(self, x: float, y: float, z: float) -> bool:
        """将物体放置到指定位置（状态机驱动）

        Args:
            x, y, z: 放置位置坐标

        Returns:
            bool: 放置成功返回 True
        """
        if not self.action_executor:
            logger.error("Action executor not initialized")
            return False
        return self.action_executor.execute_delivery((x, y, z))

    def pickup_and_deliver(self, pickup_pos: tuple, delivery_pos: tuple,
                           hand: str = "left", **kwargs) -> bool:
        """完整的抓取-递送流程

        Args:
            pickup_pos: 抓取位置 (x, y, z)
            delivery_pos: 递送位置 (x, y, z)
            hand: 使用哪只手
            **kwargs: 可选参数 grasp_width, grasp_effort

        Returns:
            bool: 全流程成功返回 True
        """
        if not self.action_executor:
            logger.error("Action executor not initialized")
            return False
        return self.action_executor.execute_pickup_and_deliver(
            pickup_pos, delivery_pos, hand=hand, **kwargs
        )

    # ==================== 紧急控制 ====================

    def emergency_stop(self):
        """紧急停止所有动作"""
        logger.warning("Emergency stop triggered")
        if self.action_executor:
            self.action_executor.abort()
        if self.chassis:
            self.chassis.robot_stop()

    # ==================== 状态查询 ====================

    def get_status(self) -> dict:
        """获取机器人完整状态

        Returns:
            dict: 包含各子系统状态
        """
        try:
            status = {}

            if self.chassis:
                status["chassis"] = {
                    "state": self.chassis.robot_state(),
                    "pose": self.chassis.robot_pose_speed(),
                    "battery": self.chassis.robot_battery()
                }

            if self.gripper:
                status["gripper"] = self.gripper.get_state()

            if self.arm:
                status["arm"] = "initialized"

            if self.head:
                status["head"] = "initialized"

            if self.action_executor:
                action_state = self.action_executor.get_state()
                status["action"] = action_state.name if action_state else "idle"

            return status
        except Exception as e:
            logger.error(f"Error getting robot status: {e}")
            return {}
