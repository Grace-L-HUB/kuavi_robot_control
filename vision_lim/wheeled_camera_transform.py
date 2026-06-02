"""
轮臂机器人头顶下倾相机：相机 optical 坐标 -> 机械臂 IK 基座坐标。

优先使用 ROS tf（与 ros_interface 发布的 /tf 一致）；
无 tf 时使用静态俯仰模型（见 config/wheeled_head_camera.yaml）。
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

DEFAULT_CONFIG = Path(__file__).parent / "config" / "wheeled_head_camera.yaml"

# 来自 grasp_target.json 的相机系三维点（米）
DEFAULT_CAMERA_POINT = (
    -0.044330238372661326,
    0.08261372036424994,
    0.64,
)


def load_wheeled_camera_config(path: Optional[str] = None) -> Dict:
    p = Path(path) if path else DEFAULT_CONFIG
    if not p.is_file():
        return _default_config_dict()
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or _default_config_dict()


def _default_config_dict() -> Dict:
    return {
        "camera_frame": "camera_depth_optical_frame",
        "ik_target_frames": ["base_link", "torso", "pelvis"],
        "static_transform": {
            "pitch_deg": 48.0,
            "camera_position_in_base": [0.12, 0.0, 0.55],
            "lateral_sign": -1.0,
        },
        "grasp_offsets": {"pre_grasp_z": 0.10, "grasp_depth_z": 0.0},
    }


def camera_optical_to_base_static(
    point_cam: Tuple[float, float, float],
    pitch_deg: float,
    camera_position_in_base: Tuple[float, float, float],
    lateral_sign: float = -1.0,
) -> Tuple[float, float, float]:
    """
    头顶相机向下俯仰的静态近似（无 tf 时）。

    相机 optical: X 右, Y 下, Z 前（深度）。
    基座: X 前, Y 左, Z 上。

    将深度 Z 分解为前方与下方分量；图像 X 映射为基座横向。
    """
    x_c, y_c, z_c = point_cam
    cx, cy, cz = camera_position_in_base
    p = math.radians(pitch_deg)
    c, s = math.cos(p), math.sin(p)

    x_b = cx + z_c * c + y_c * s
    y_b = cy + lateral_sign * x_c
    z_b = cz - z_c * s + y_c * c * 0.35

    return (x_b, y_b, z_b)


def camera_optical_to_base_tf(
    point_cam: Tuple[float, float, float],
    source_frame: str,
    target_frames: List[str],
    timeout_sec: float = 3.0,
) -> Tuple[Tuple[float, float, float], str]:
    """通过 tf2 将点变换到 IK 基座系（与 ros_application /tf 一致）。"""
    import rospy
    import tf2_ros
    from geometry_msgs.msg import PointStamped

    buffer = tf2_ros.Buffer()
    listener = tf2_ros.TransformListener(buffer)
    rospy.sleep(0.5)

    pt = PointStamped()
    pt.header.frame_id = source_frame
    pt.header.stamp = rospy.Time(0)
    pt.point.x = float(point_cam[0])
    pt.point.y = float(point_cam[1])
    pt.point.z = float(point_cam[2])

    last_err = None
    for target in target_frames:
        try:
            out = buffer.transform(
                pt, target, rospy.Duration(timeout_sec)
            )
            return (
                (out.point.x, out.point.y, out.point.z),
                target,
            )
        except Exception as e:
            last_err = e
    raise RuntimeError(f"tf 变换失败 {source_frame} -> {target_frames}: {last_err}")


def resolve_grasp_poses_arm_base(
    point_cam: Tuple[float, float, float],
    config: Optional[Dict] = None,
    use_tf: bool = False,
) -> Dict:
    """
    返回 pre_grasp / grasp / retreat（米，IK 基座系）。
    """
    cfg = config or load_wheeled_camera_config()
    st = cfg.get("static_transform", {})
    off = cfg.get("grasp_offsets", {})

    if use_tf:
        import rospy

        if not rospy.core.is_initialized():
            rospy.init_node("wheeled_cam_tf_lookup", anonymous=True)
        arm, frame = camera_optical_to_base_tf(
            point_cam,
            cfg.get("camera_frame", "camera_depth_optical_frame"),
            cfg.get("ik_target_frames", ["base_link"]),
        )
        method = f"tf->{frame}"
    else:
        pos = st.get("camera_position_in_base", [0.12, 0.0, 0.55])
        arm = camera_optical_to_base_static(
            point_cam,
            float(st.get("pitch_deg", 48.0)),
            (float(pos[0]), float(pos[1]), float(pos[2])),
            float(st.get("lateral_sign", -1.0)),
        )
        method = "static_pitch"

    pre_z = float(off.get("pre_grasp_z", 0.10))
    grasp_dz = float(off.get("grasp_depth_z", 0.0))

    grasp = (arm[0], arm[1], arm[2] + grasp_dz)
    pre = (grasp[0], grasp[1], grasp[2] + pre_z)
    retreat = pre

    return {
        "camera_coord_m": list(point_cam),
        "arm_coord_m": list(grasp),
        "pre_grasp": list(pre),
        "grasp": list(grasp),
        "retreat": list(retreat),
        "transform_method": method,
    }


def print_transform_debug(point_cam: Tuple[float, float, float], config_path: Optional[str] = None) -> None:
    cfg = load_wheeled_camera_config(config_path)
    static_arm = camera_optical_to_base_static(
        point_cam,
        float(cfg["static_transform"]["pitch_deg"]),
        tuple(cfg["static_transform"]["camera_position_in_base"]),
        float(cfg["static_transform"].get("lateral_sign", -1.0)),
    )
    print("相机 optical (m):", point_cam)
    print("静态变换 -> 基座 (m):", static_arm)
    print("  (旧错误: 直接把相机 Z 当高度 -> 会举到头顶)")
    poses = resolve_grasp_poses_arm_base(point_cam, cfg, use_tf=False)
    print("抓取规划:", poses)
