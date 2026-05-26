"""坐标变换模块：像素坐标 -> 相机坐标系 -> 机械臂基座坐标系。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import yaml

logger = logging.getLogger(__name__)

# 配置默认值
DEFAULT_COLOR_INTRINSICS = {
    "fx": 361.1151123046875,
    "fy": 361.1151123046875,
    "cx": 321.2451477050781,
    "cy": 180.9050750732422,
}

DEFAULT_DEPTH_INTRINSICS = {
    "fx": 192.194091796875,
    "fy": 192.194091796875,
    "cx": 154.92611694335938,
    "cy": 119.32855224609375,
}


def load_intrinsics_from_yaml(yaml_path: str) -> Dict[str, Dict]:
    """
    从YAML文件加载相机内参

    Args:
        yaml_path: 配置文件路径

    Returns:
        包含 color_camera 和 depth_camera 内参的字典
    """
    path = Path(yaml_path)
    if not path.is_file():
        logger.warning(f"Config file not found: {yaml_path}, using defaults")
        return {
            "color_camera": DEFAULT_COLOR_INTRINSICS,
            "depth_camera": DEFAULT_DEPTH_INTRINSICS,
        }

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    result = {}

    # 解析彩色相机内参
    if "color_camera" in config:
        cc = config["color_camera"]
        result["color_camera"] = {
            "fx": cc.get("fx", DEFAULT_COLOR_INTRINSICS["fx"]),
            "fy": cc.get("fy", DEFAULT_COLOR_INTRINSICS["fy"]),
            "cx": cc.get("cx", DEFAULT_COLOR_INTRINSICS["cx"]),
            "cy": cc.get("cy", DEFAULT_COLOR_INTRINSICS["cy"]),
        }
    else:
        result["color_camera"] = DEFAULT_COLOR_INTRINSICS.copy()

    # 解析深度相机内参
    if "depth_camera" in config:
        dc = config["depth_camera"]
        result["depth_camera"] = {
            "fx": dc.get("fx", DEFAULT_DEPTH_INTRINSICS["fx"]),
            "fy": dc.get("fy", DEFAULT_DEPTH_INTRINSICS["fy"]),
            "cx": dc.get("cx", DEFAULT_DEPTH_INTRINSICS["cx"]),
            "cy": dc.get("cy", DEFAULT_DEPTH_INTRINSICS["cy"]),
        }
    else:
        result["depth_camera"] = DEFAULT_DEPTH_INTRINSICS.copy()

    return result


def pixel_to_camera_coord(
    u: int,
    v: int,
    depth_m: float,
    intrinsics: Dict[str, float],
) -> Tuple[float, float, float]:
    """
    像素坐标转相机坐标系3D坐标

    公式:
        X = (u - cx) * Z / fx
        Y = (v - cy) * Z / fy
        Z = depth_m

    Args:
        u, v: 像素坐标
        depth_m: 深度值（单位：米）
        intrinsics: 相机内参字典，包含 'fx', 'fy', 'cx', 'cy'

    Returns:
        (X, Y, Z) 相机坐标系下的坐标（单位：米）
    """
    fx = intrinsics.get("fx", DEFAULT_COLOR_INTRINSICS["fx"])
    fy = intrinsics.get("fy", DEFAULT_COLOR_INTRINSICS["fy"])
    cx = intrinsics.get("cx", DEFAULT_COLOR_INTRINSICS["cx"])
    cy = intrinsics.get("cy", DEFAULT_COLOR_INTRINSICS["cy"])

    Z = depth_m
    X = (u - cx) * Z / fx
    Y = (v - cy) * Z / fy

    return (X, Y, Z)


def camera_to_arm_base(
    point_cam: Tuple[float, float, float],
    T_cam_to_arm: np.ndarray,
) -> Tuple[float, float, float]:
    """
    相机坐标系 -> 机械臂基座坐标系

    公式:
        P_arm = R * P_cam + t

    Args:
        point_cam: (X, Y, Z) 相机坐标系坐标
        T_cam_to_arm: 4x4 齐次变换矩阵 [R t; 0 1]

    Returns:
        (X_arm, Y_arm, Z_arm) 机械臂基座坐标系坐标
    """
    # 确保变换矩阵是正确的格式
    if T_cam_to_arm.shape != (4, 4):
        logger.error(f"Invalid transformation matrix shape: {T_cam_to_arm.shape}")
        return point_cam

    # 提取旋转矩阵和平移向量
    R = T_cam_to_arm[:3, :3]
    t = T_cam_to_arm[:3, 3]

    # 齐次坐标
    p_cam = np.array([point_cam[0], point_cam[1], point_cam[2], 1.0])

    # 变换
    p_arm = R @ p_cam[:3] + t

    return tuple(p_arm)


def transform_point(
    point: Tuple[float, float, float],
    transform: np.ndarray,
) -> Tuple[float, float, float]:
    """
    应用4x4齐次变换矩阵

    Args:
        point: 输入点 (x, y, z)
        transform: 4x4变换矩阵

    Returns:
        变换后的点
    """
    if transform.shape != (4, 4):
        raise ValueError(f"Transform must be 4x4, got {transform.shape}")

    p = np.array([point[0], point[1], point[2], 1.0])
    result = transform @ p
    return (result[0], result[1], result[2])


def load_hand_eye_calibration(npy_path: str) -> Optional[np.ndarray]:
    """
    加载手眼标定矩阵

    Args:
        npy_path: .npy文件路径

    Returns:
        4x4齐次变换矩阵，或None（加载失败时）
    """
    path = Path(npy_path)
    if not path.is_file():
        logger.warning(f"Hand-eye calibration file not found: {npy_path}")
        return None

    try:
        T = np.load(path)
        if T.shape != (4, 4):
            logger.error(f"Invalid calibration matrix shape: {T.shape}")
            return None
        logger.info(f"Loaded hand-eye calibration from {npy_path}")
        return T
    except Exception as e:
        logger.error(f"Failed to load calibration matrix: {e}")
        return None


def create_identity_transform() -> np.ndarray:
    """创建单位变换矩阵"""
    return np.eye(4)


class CoordinateTransformer:
    """坐标变换器：封装内参和手眼标定矩阵"""

    def __init__(
        self,
        color_intrinsics: Optional[Dict[str, float]] = None,
        depth_intrinsics: Optional[Dict[str, float]] = None,
        T_cam_to_arm: Optional[np.ndarray] = None,
        config_path: Optional[str] = None,
    ):
        """
        初始化坐标变换器

        Args:
            color_intrinsics: 彩色相机内参
            depth_intrinsics: 深度相机内参
            T_cam_to_arm: 手眼标定矩阵
            config_path: 配置文件路径（可从此文件加载所有参数）
        """
        # 加载配置
        if config_path:
            configs = load_intrinsics_from_yaml(config_path)
            self._color_intrinsics = configs.get("color_camera", DEFAULT_COLOR_INTRINSICS)
            self._depth_intrinsics = configs.get("depth_camera", DEFAULT_DEPTH_INTRINSICS)

            # 加载手眼标定矩阵
            yaml_path = Path(config_path)
            npy_path = yaml_path.parent.parent / "T_cam_to_arm.npy"
            self._T_cam_to_arm = load_hand_eye_calibration(str(npy_path))
        else:
            self._color_intrinsics = color_intrinsics or DEFAULT_COLOR_INTRINSICS.copy()
            self._depth_intrinsics = depth_intrinsics or DEFAULT_DEPTH_INTRINSICS.copy()
            self._T_cam_to_arm = T_cam_to_arm

        # 如果没有标定矩阵，使用单位矩阵
        if self._T_cam_to_arm is None:
            self._T_cam_to_arm = create_identity_transform()
            logger.warning("No hand-eye calibration, using identity transform")

    @property
    def color_intrinsics(self) -> Dict[str, float]:
        """获取彩色相机内参"""
        return self._color_intrinsics.copy()

    @property
    def depth_intrinsics(self) -> Dict[str, float]:
        """获取深度相机内参"""
        return self._depth_intrinsics.copy()

    @property
    def T_cam_to_arm(self) -> np.ndarray:
        """获取手眼标定矩阵"""
        return self._T_cam_to_arm.copy()

    def set_hand_eye_calibration(self, T: np.ndarray):
        """设置手眼标定矩阵"""
        if T.shape != (4, 4):
            raise ValueError("Transform matrix must be 4x4")
        self._T_cam_to_arm = T.copy()
        logger.info("Hand-eye calibration matrix updated")

    def pixel_to_arm_base(
        self,
        u: int,
        v: int,
        depth_m: float,
        use_depth_intrinsics: bool = False,
    ) -> Tuple[float, float, float]:
        """
        像素坐标直接转换为机械臂基座坐标

        Args:
            u, v: 像素坐标
            depth_m: 深度值（米）
            use_depth_intrinsics: 是否使用深度相机内参（彩色图和深度图内参不同时）

        Returns:
            (X, Y, Z) 机械臂基座坐标系下的坐标
        """
        # 选择内参
        intrinsics = self._depth_intrinsics if use_depth_intrinsics else self._color_intrinsics

        # 像素 -> 相机坐标
        point_cam = pixel_to_camera_coord(u, v, depth_m, intrinsics)

        # 相机坐标 -> 机械臂基座坐标
        point_arm = camera_to_arm_base(point_cam, self._T_cam_to_arm)

        return point_arm

    def transform_to_arm_base(
        self,
        point_cam: Tuple[float, float, float],
    ) -> Tuple[float, float, float]:
        """
        将相机坐标系下的点转换到机械臂基座坐标系

        Args:
            point_cam: 相机坐标系下的坐标

        Returns:
            机械臂基座坐标系下的坐标
        """
        return camera_to_arm_base(point_cam, self._T_cam_to_arm)


class TargetPosition:
    """目标位置数据结构"""
    class_name: str                              # 物体类别
    pixel_coord: Tuple[int, int]                 # 像素坐标 (u, v)
    depth_m: float                                # 深度值（米）
    camera_coord: Tuple[float, float, float]      # 相机坐标系坐标
    arm_coord: Tuple[float, float, float]        # 机械臂基座坐标
    confidence: float = 1.0                       # 置信度

    def to_dict(self) -> dict:
        return {
            "class_name": self.class_name,
            "pixel_coord": list(self.pixel_coord),
            "depth_m": self.depth_m,
            "camera_coord": list(self.camera_coord),
            "arm_coord": list(self.arm_coord),
            "confidence": self.confidence,
        }

    def __repr__(self) -> str:
        return (f"TargetPosition(class={self.class_name}, "
                f"pixel={self.pixel_coord}, depth={self.depth_m:.3f}m, "
                f"arm=({self.arm_coord[0]:.3f}, {self.arm_coord[1]:.3f}, {self.arm_coord[2]:.3f}))")


def compute_target_position(
    detection: "Detection",  # type: ignore # noqa: F821
    depth_m: float,
    transformer: CoordinateTransformer,
    use_depth_intrinsics: bool = False,
) -> TargetPosition:
    """
    从检测结果和深度值计算目标位置

    Args:
        detection: 检测结果对象
        depth_m: 深度值（米）
        transformer: 坐标变换器
        use_depth_intrinsics: 是否使用深度相机内参

    Returns:
        TargetPosition对象
    """
    u, v = detection.bbox_center

    # 像素坐标 -> 相机坐标
    camera_coord = pixel_to_camera_coord(u, v, depth_m, transformer.color_intrinsics)

    # 相机坐标 -> 机械臂基座坐标
    arm_coord = transformer.transform_to_arm_base(camera_coord)

    return TargetPosition(
        class_name=detection.class_name,
        pixel_coord=(u, v),
        depth_m=depth_m,
        camera_coord=camera_coord,
        arm_coord=arm_coord,
        confidence=detection.confidence,
    )
