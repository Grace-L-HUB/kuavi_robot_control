#!/usr/bin/env python3
"""离线计算抓取坐标并更新 grasp_target.json / wheeled_head_camera.yaml"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys_path = str(ROOT)
import sys

if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

from vision_lim.camera_info_parser import load_intrinsics_from_camera_info_files
from vision_lim.coordinate_transform import pixel_to_camera_coord
from vision_lim.wheeled_camera_transform import resolve_grasp_poses_arm_base

INSTANCE = ROOT / "instance"
CONFIG_PATH = ROOT / "vision_lim" / "config" / "wheeled_head_camera.yaml"


def depth_at(depth: np.ndarray, u: int, v: int, r: int = 4) -> float:
    vals = []
    for du in range(-r, r + 1):
        for dv in range(-r, r + 1):
            uu, vv = u + du, v + dv
            if 0 <= vv < depth.shape[0] and 0 <= uu < depth.shape[1]:
                d = depth[vv, uu]
                if hasattr(d, "item"):
                    d = d.item()
                if d > 0:
                    vals.append(float(d))
    return float(np.median(vals)) if vals else 0.0


def estimate_pitch_from_side(side_path: Path) -> float:
    """侧视照片估计相机光轴相对水平面向下俯角（度）。"""
    side = cv2.imread(str(side_path))
    if side is None:
        return 42.0
    h, w = side.shape[:2]
    roi = side[int(h * 0.08) : int(h * 0.52), int(w * 0.08) : int(w * 0.55)]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, 60, minLineLength=100, maxLineGap=15
    )
    tilts = []
    if lines is not None:
        for x1, y1, x2, y2 in lines[:, 0]:
            ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
            length = math.hypot(x2 - x1, y2 - y1)
            if length > 120 and 25 < abs(ang) < 65:
                tilts.append(abs(ang))
    if tilts:
        return float(np.clip(np.median(tilts), 35.0, 52.0))
    return 42.0


def main() -> None:
    color = cv2.imread(str(INSTANCE / "color_image.png"))
    depth = cv2.imread(str(INSTANCE / "depth_image.png"), cv2.IMREAD_UNCHANGED)
    ci, di = load_intrinsics_from_camera_info_files(
        str(INSTANCE / "camera_info.txt"),
        str(INSTANCE / "camera_info1.txt"),
    )

    # 水瓶在彩色图中心（瓶盖处深度常无效，在邻域取有效深度）
    u_c, v_c = 320, 255
    u_d0 = int(round(u_c + (di["cx"] - ci["cx"])))
    v_d0 = int(round(v_c + (di["cy"] - ci["cy"])))
    dmm, u_d, v_d = 0.0, u_d0, v_d0
    for dv in range(0, 35, 2):
        for du in (-6, -3, 0, 3, 6):
            cand_u, cand_v = u_d0 + du, v_d0 + dv
            val = depth_at(depth, cand_u, cand_v, r=3)
            if val > 0:
                dmm, u_d, v_d = val, cand_u, cand_v
                break
        if dmm > 0:
            break
    if dmm <= 0:
        raise RuntimeError(f"深度无效，pixel_depth 邻域 ({u_d0},{v_d0}) 无有效值")

    z = dmm / 1000.0
    cam = (
        (u_d - di["cx"]) * z / di["fx"],
        (v_d - di["cy"]) * z / di["fy"],
        z,
    )

    side_pitch = estimate_pitch_from_side(
        INSTANCE / "微信图片_20260606153542_138_67.jpg"
    )

    # Kuavo 4 Pro 轮臂：头部 yaw=0，俯仰由侧视 + 头部关节范围约束
    # camera_position_in_base: 相机在 base_link 前方/高度近似（轮臂 IK 基座）
    cfg = {
        "camera_frame": "camera_depth_optical_frame",
        "ik_target_frames": ["base_link", "torso", "pelvis", "odom", "base"],
        "static_transform": {
            "pitch_deg": round(side_pitch, 1),
            "camera_position_in_base": [0.10, 0.0, 0.58],
            "lateral_sign": -1.0,
            "forward_depth_scale": 1.0,
            "height_from_depth_scale": 0.95,
        },
        "grasp_offsets": {
            "forward_extra_m": 0.02,
            "depth_forward_scale": 1.0,
            "center_y_bias": 0.02,
            "grasp_z_bias": 0.0,
            "symmetric_mirror_y": True,
            "left_grasp_z_from_inactive": True,
            "left_y_fine": 0.0,
            "left_z_tip_offset": -0.10,
            "left_z_fine": -0.05,
            "left_y_fine": 0.0,
            "left_x_fine": -0.12,
            "grasp_depth_z": 0.0,
            "pre_grasp_back_m": 0.12,
            "pre_grasp_lift_z": 0.02,
            "retreat_back_m": 0.08,
            "retreat_lift_z": 0.04,
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

    poses = resolve_grasp_poses_arm_base(cam, cfg, hand="right")

    grasp_json = {
        "pixel_color": [u_c, v_c],
        "pixel_depth": [u_d, v_d],
        "depth_m": round(z, 4),
        "camera_coord_m": [round(x, 4) for x in cam],
        "arm_coord_m": [round(x, 4) for x in poses["grasp"]],
        "transform_method": poses["transform_method"],
        "static_transform": cfg["static_transform"],
        "grasp_offsets": cfg["grasp_offsets"],
        "color_intrinsics": ci,
        "depth_intrinsics": di,
        "grasp_plan": {
            "pre_grasp": [round(x, 4) for x in poses["pre_grasp"]],
            "grasp": [round(x, 4) for x in poses["grasp"]],
            "retreat": [round(x, 4) for x in poses["retreat"]],
        },
        "grasp_quat_xyzw": poses["grasp_quat_xyzw"],
        "note": f"Kuavo4Pro 轮臂; head yaw=0; pitch={side_pitch:.1f}deg from side photo",
    }

    (INSTANCE / "grasp_target.json").write_text(
        json.dumps(grasp_json, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(
            cfg,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )

    print("side_pitch_deg", side_pitch)
    print("camera_coord_m", cam)
    print("grasp", poses["grasp"])
    print("pre_grasp", poses["pre_grasp"])
    print("retreat", poses["retreat"])


if __name__ == "__main__":
    main()
