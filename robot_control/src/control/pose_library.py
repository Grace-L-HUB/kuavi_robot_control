"""
预定义姿态库

存储和管理机器人手臂的预定义姿态（14关节角度），
支持从配置文件加载自定义姿态和姿态间线性插值。

关节排列（14个关节，单位：度）：
  1-7  左臂: l_arm_pitch, l_arm_roll, l_arm_yaw, l_forearm_pitch, l_hand_yaw, l_hand_pitch, l_hand_roll
  8-14 右臂: r_arm_pitch, r_arm_roll, r_arm_yaw, r_forearm_pitch, r_hand_yaw, r_hand_pitch, r_hand_roll
"""
import copy
import logging
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

# 默认姿态定义（14关节角度，单位：度）
DEFAULT_POSES: Dict[str, List[float]] = {
    # 初始位：双臂自然下垂
    "home": [
        0, 0, 0, 0, 0, 0, 0,       # 左臂
        0, 0, 0, 0, 0, 0, 0,       # 右臂
    ],

    # 准备位：手臂微前倾弯曲，准备工作
    "ready": [
        -15, 10, 0, -30, 0, -15, 0,   # 左臂
        -15, -10, 0, -30, 0, -15, 0,  # 右臂
    ],

    # 预抓取位（前方）：手臂前伸到桌面上方
    "pre_grasp_front": [
        -45, 15, 0, -60, 0, -30, 0,   # 左臂
        -45, -15, 0, -60, 0, -30, 0,  # 右臂
    ],

    # 抓取位（低位）：手臂下降到桌面高度
    "grasp_low": [
        -60, 15, 0, -45, 0, -45, 0,   # 左臂
        -60, -15, 0, -45, 0, -45, 0,  # 右臂
    ],

    # 搬运位：前臂水平内收，安全搬运
    "transport": [
        -30, 20, 0, -90, 0, -30, 0,   # 左臂
        -30, -20, 0, -90, 0, -30, 0,  # 右臂
    ],

    # 递送位（前方）：手臂前伸准备放置（与预抓取对称）
    "deliver_front": [
        -45, 15, 0, -60, 0, -30, 0,   # 左臂
        -45, -15, 0, -60, 0, -30, 0,  # 右臂
    ],

    # 展示位：手臂前伸展示物体
    "present": [
        -30, 30, 0, -60, 0, -20, 0,   # 左臂
        -30, -30, 0, -60, 0, -20, 0,  # 右臂
    ],
}

NUM_JOINTS = 14


class PoseLibrary:
    """机器人手臂预定义姿态库"""

    def __init__(self, config: dict = None):
        """初始化姿态库

        Args:
            config: 配置字典，可包含 'poses' 键覆盖默认姿态
        """
        self._poses: Dict[str, List[float]] = copy.deepcopy(DEFAULT_POSES)

        # 从配置文件加载自定义姿态
        if config:
            custom_poses = config.get("poses", {})
            if isinstance(custom_poses, dict):
                for name, angles in custom_poses.items():
                    if self._validate_pose(name, angles):
                        self._poses[name] = list(angles)
                        logger.debug(f"Loaded custom pose: {name}")

        logger.info(f"Pose library initialized with {len(self._poses)} poses: "
                     f"{list(self._poses.keys())}")

    def _validate_pose(self, name: str, angles) -> bool:
        """验证姿态角度数据合法性"""
        if not isinstance(angles, (list, tuple)):
            logger.warning(f"Pose '{name}' must be a list, got {type(angles)}")
            return False
        if len(angles) != NUM_JOINTS:
            logger.warning(f"Pose '{name}' has {len(angles)} joints, expected {NUM_JOINTS}")
            return False
        for i, a in enumerate(angles):
            if not isinstance(a, (int, float)):
                logger.warning(f"Pose '{name}' joint {i} is not a number: {a}")
                return False
        return True

    def get(self, name: str) -> Optional[List[float]]:
        """获取指定名称的姿态角度

        Args:
            name: 姿态名称

        Returns:
            14个关节角度的列表（度），不存在返回 None
        """
        pose = self._poses.get(name)
        if pose is None:
            logger.error(f"Pose '{name}' not found. Available: {list(self._poses.keys())}")
            return None
        return list(pose)  # 返回副本

    def get_for_hand(self, name: str, hand: str = "left") -> Optional[List[float]]:
        """获取指定手的7个关节角度

        Args:
            name: 姿态名称
            hand: "left"（关节1-7）或 "right"（关节8-14）

        Returns:
            7个关节角度的列表（度），不存在返回 None
        """
        pose = self.get(name)
        if pose is None:
            return None
        if hand == "left":
            return pose[:7]
        elif hand == "right":
            return pose[7:]
        else:
            logger.error(f"Invalid hand: {hand}. Use 'left' or 'right'")
            return None

    def interpolate(self, start_name: str, end_name: str,
                    steps: int = 5) -> Optional[List[List[float]]]:
        """在两个姿态之间线性插值生成平滑轨迹

        Args:
            start_name: 起始姿态名称
            end_name: 目标姿态名称
            steps: 插值步数（不含起始点，含终点）

        Returns:
            姿态列表，每个元素为14关节角度。None 表示姿态不存在。
        """
        start = self.get(start_name)
        end = self.get(end_name)
        if start is None or end is None:
            return None
        return self.interpolate_angles(start, end, steps)

    @staticmethod
    def interpolate_angles(start: List[float], end: List[float],
                           steps: int = 5) -> List[List[float]]:
        """在两组关节角度之间线性插值

        Args:
            start: 起始关节角度（14个）
            end: 目标关节角度（14个）
            steps: 插值步数（不含起始点，含终点）

        Returns:
            姿态列表，从 start 后的第一步到 end
        """
        if steps < 1:
            return [list(end)]

        trajectory = []
        for step in range(1, steps + 1):
            t = step / steps
            waypoint = [
                s + (e - s) * t
                for s, e in zip(start, end)
            ]
            trajectory.append(waypoint)
        return trajectory

    def add_pose(self, name: str, angles: List[float]) -> bool:
        """添加或更新自定义姿态

        Args:
            name: 姿态名称
            angles: 14个关节角度

        Returns:
            成功返回 True
        """
        if not self._validate_pose(name, angles):
            return False
        self._poses[name] = list(angles)
        logger.info(f"Added pose: {name}")
        return True

    def list_poses(self) -> List[str]:
        """返回所有可用的姿态名称"""
        return list(self._poses.keys())

    def has_pose(self, name: str) -> bool:
        """检查姿态是否存在"""
        return name in self._poses
