"""
轮臂机器人头顶下倾相机：相机 optical 坐标 -> 机械臂 IK 基座坐标。
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

DEFAULT_CONFIG = Path(__file__).parent / "config" / "wheeled_head_camera.yaml"

DEFAULT_CAMERA_POINT = (
    -0.013972711859484142,
    0.0325017152875609,
    0.772,
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
        "grasp_offsets": {
            "forward_extra_m": 0.22,
            "depth_forward_scale": 1.05,
            "right_y_bias": -0.18,
            "left_y_bias": 0.18,
            "left_grasp_z_bias": -0.17,
            "right_grasp_z_bias": 0.0,
            "pre_grasp_back_m": 0.14,
            "pre_grasp_lift_z": 0.05,
            "retreat_back_m": 0.12,
            "retreat_lift_z": 0.08,
            "grasp_depth_z": 0.0,
        },
        "end_effector_orientation": {
            "palm_down": [0.0, -0.70682518, 0.0, 0.70738827],
            "right": {"quat_xyzw": [-0.5002, -0.4998, -0.4998, 0.5002]},
            "left": {"quat_xyzw": [0.5002, -0.4998, -0.4998, 0.5002]},
        },
        "inactive_arm_pose": {
            "left": [0.45, 0.25, 0.11988012],
            "right": [0.45, -0.25, 0.11988012],
        },
    }


def get_grasp_quat(hand: str, config: Optional[Dict] = None) -> List[float]:
    cfg = config or load_wheeled_camera_config()
    eo = cfg.get("end_effector_orientation", {})
    key = "right" if hand == "right" else "left"
    block = eo.get(key, {})
    if isinstance(block, dict) and block.get("quat_xyzw"):
        return list(block["quat_xyzw"])
    return list(eo.get("palm_down", [0.0, -0.70682518, 0.0, 0.70738827]))


def get_inactive_arm_pose(hand: str, config: Optional[Dict] = None) -> List[float]:
    """返回非抓取侧待机位置。"""
    cfg = config or load_wheeled_camera_config()
    poses = cfg.get("inactive_arm_pose", {})
    if hand == "right":
        return list(poses.get("left", [0.45, 0.25, 0.11988012]))
    return list(poses.get("right", [0.45, -0.25, 0.11988012]))


def camera_optical_to_base_static(
    point_cam: Tuple[float, float, float],
    pitch_deg: float,
    camera_position_in_base: Tuple[float, float, float],
    lateral_sign: float = -1.0,
    st_extra: Optional[Dict] = None,
) -> Tuple[float, float, float]:
    x_c, y_c, z_c = point_cam
    cx, cy, cz = camera_position_in_base
    p = math.radians(pitch_deg)
    c, s = math.cos(p), math.sin(p)
    st = st_extra or {}

    fwd_scale = float(st.get("forward_depth_scale", 1.08))
    h_scale = float(st.get("height_from_depth_scale", 1.0))

    x_b = cx + z_c * c * fwd_scale + y_c * s * 0.5
    y_b = cy + lateral_sign * x_c
    # 俯视深度主要转为“前方”，高度仅保留一部分，避免抬过高
    z_b = cz - z_c * s * h_scale + y_c * c * 0.15

    return (x_b, y_b, z_b)


def _vision_base_target(
    arm: Tuple[float, float, float],
    off: Dict,
) -> Tuple[float, float, float]:
    """视觉/static 变换得到的居中目标点（尚未分左/右手）。"""
    scale = float(off.get("depth_forward_scale", 1.0))
    cx, cy, cz = arm[0], arm[1], arm[2]
    forward_part = cx - float(off.get("_cam_x0", 0.12))
    gx = float(off.get("_cam_x0", 0.12)) + forward_part * scale
    gx += float(off.get("forward_extra_m", 0.0))
    gy = cy + float(off.get("center_y_bias", 0.0))
    gz = cz + float(off.get("grasp_depth_z", 0.0)) + float(off.get("grasp_z_bias", 0.0))
    return (gx, gy, gz)


def _official_hand_grasp_pose(
    base: Tuple[float, float, float],
    hand: str,
    off: Dict,
) -> Tuple[float, float, float]:
    """
    官方 apriltag/水瓶抓取：同一目标点，temp_x 负向，offset_z 负向（偏下），
    Y 方向 temp_y 左加右减（interface 案例文档）。
    """
    x, y, z = base
    tx = float(off.get("temp_x", off.get("temp_x_l", -0.05)))
    ty = float(off.get("temp_y", off.get("temp_y_l", 0.05)))
    tz = float(off.get("offset_z", -0.10))
    if hand == "left":
        return (x + tx, y + ty, z + tz)
    return (x + tx, y - ty, z + tz)


def camera_optical_to_base_tf(
    point_cam: Tuple[float, float, float],
    source_frame: str,
    target_frames: List[str],
    timeout_sec: float = 3.0,
) -> Tuple[Tuple[float, float, float], str]:
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
            out = buffer.transform(pt, target, rospy.Duration(timeout_sec))
            return ((out.point.x, out.point.y, out.point.z), target)
        except Exception as e:
            last_err = e
    raise RuntimeError(f"tf 变换失败: {last_err}")


def resolve_grasp_poses_arm_base(
    point_cam: Tuple[float, float, float],
    config: Optional[Dict] = None,
    use_tf: bool = False,
    hand: str = "right",
) -> Dict:
    cfg = config or load_wheeled_camera_config()
    st = cfg.get("static_transform", {})
    off = dict(cfg.get("grasp_offsets", {}))
    cam_pos = st.get("camera_position_in_base", [0.12, 0.0, 0.55])
    off["_cam_x0"] = float(cam_pos[0])

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
        arm = camera_optical_to_base_static(
            point_cam,
            float(st.get("pitch_deg", 48.0)),
            (float(cam_pos[0]), float(cam_pos[1]), float(cam_pos[2])),
            float(st.get("lateral_sign", -1.0)),
            st_extra=st,
        )
        method = "static_pitch"

    base = _vision_base_target(arm, off)
    grasp = _official_hand_grasp_pose(base, hand, off)
    method = f"{method}_official_hand"

    pre_back = float(off.get("pre_grasp_back_m", 0.14))
    ret_back = float(off.get("retreat_back_m", 0.12))
    pre_lift = float(off.get("pre_grasp_lift_z", 0.05))
    ret_lift = float(off.get("retreat_lift_z", 0.08))

    # 水平抓取：预抓取在后方，沿 +X 前伸到抓取点
    pre = (grasp[0] - pre_back, grasp[1], grasp[2] + pre_lift)
    retreat = (grasp[0] - ret_back, grasp[1], grasp[2] + ret_lift)

    return {
        "camera_coord_m": list(point_cam),
        "base_target_m": list(base),
        "arm_coord_m": list(grasp),
        "pre_grasp": list(pre),
        "grasp": list(grasp),
        "retreat": list(retreat),
        "transform_method": method,
        "grasp_quat_xyzw": get_grasp_quat(hand, cfg),
        "inactive_arm_pose": get_inactive_arm_pose(hand, cfg),
    }
