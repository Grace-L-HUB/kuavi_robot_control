#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
固定坐标抓取（单文件，可单独拷到 kuavo-ros-opensource/scripts/ 运行）。

【必做】source ROS + Kuavo 工作空间:
  source /opt/ros/noetic/setup.bash
  source /home/lab/kuavo-ros-opensource/devel/setup.bash

【运行】
  cd /path/to/kuavo-ros-opensource/scripts
  python3 grasp_from_offline_vision.py --dry-coords --hand right
  python3 grasp_from_offline_vision.py --hand right

  # --hand left：左手 IK 双臂就位，三段位姿（左上方→正上方→下降）后 left_claw 抓取
  python3 grasp_from_offline_vision.py --hand left
  python3 grasp_from_offline_vision.py --hand left --dry-coords

【调参】只改下方 ===== 用户参数区 =====，保存后重跑 --dry-coords 预览坐标。
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_SCRIPT_DIR = Path(__file__).resolve().parent

# =============================================================================
# 用户参数区 — 单独部署时只改这里
# =============================================================================

# 相机 optical 坐标 (m)，无 grasp_target.json 时使用
# instance 2026-06-02 新位置：color(178,298) 瓶身中心偏下，depth≈582mm
CAMERA_POINT_M = (-0.213, 0.074, 0.582)

# 相机 -> base_link 静态变换（轮臂头顶俯视）
PITCH_DEG = 51.0
CAMERA_POSITION_IN_BASE = (0.10, 0.0, 0.58)
LATERAL_SIGN = -1.0
FORWARD_DEPTH_SCALE = 1.0
HEIGHT_FROM_DEPTH_SCALE = 0.95

# 官方抓取偏置：同一视觉中心，temp_y 左加右减，offset_z 负=抓偏下物体
FORWARD_EXTRA_M = 0.02
DEPTH_FORWARD_SCALE = 1.0
CENTER_Y_BIAS = 0.0
GRASP_Z_BIAS = 0.0
TEMP_X = -0.05
TEMP_Y = 0.05
OFFSET_Z = -0.12

# 左手抓取微调（在官方 temp 偏置之后再叠加，右手不受影响）
# +X 前伸；-Y 向右/向中心；-Z 压低
LEFT_GRASP_X_BIAS = 0.027
LEFT_GRASP_Y_BIAS = -0.035
LEFT_GRASP_Z_BIAS = -0.645

# 预抓取 / 后撤（沿 base X：预抓取在抓取点后方 -X）
PRE_GRASP_BACK_M = 0.10
PRE_GRASP_LIFT_Z = 0.03
RETREAT_BACK_M = 0.08
RETREAT_LIFT_Z = 0.05
# 夹紧后：上提至正上方 → 保持 → 下放回抓取点 → 安全放开（水平后撤 → 松爪 → 上提 → 回零）
POST_GRASP_HORIZONTAL_RELEASE = True
POST_GRASP_LIFT_TO_ABOVE_DURATION_S = 4.0
POST_GRASP_LIFT_MID_DURATION_S = 2.5
POST_GRASP_HOLD_AT_ABOVE_S = 2.0
POST_GRASP_LOWER_TO_GRASP_DURATION_S = 3.0
POST_GRASP_MIN_LIFT_M = 0.20
RELEASE_RETREAT_BACK_M = 0.12
RELEASE_RETREAT_DURATION_S = 2.5
RELEASE_LIFT_DURATION_S = 3.0
# 正上方/上提高度：取「绝对高度」与「抓取点上方 clearance」中较低者（更在 IK 范围内）
APPROACH_ABOVE_Z_TARGET = -0.170
APPROACH_ABOVE_CLEARANCE_M = 0.18
APPROACH_ABOVE_Z = 0.30
# 第一段「左上方」：须与正上方在 X/Y/Z 上均有明显差值，否则从待机位看去像直达正上方
USE_THREE_STAGE_APPROACH = True
APPROACH_UPPER_LEFT_LATERAL_M = 0.22   # left 手 +Y 外扩（更靠机器人左侧）
APPROACH_UPPER_LEFT_BACK_M = 0.10      # -X 后退，从瓶身左后上方切入
APPROACH_UPPER_LEFT_EXTRA_Z = 0.12     # 比正上方再高一段，形成「高→低→抓」
APPROACH_STAGE_HOLD_S = 2.0            # 每段到位后停顿 (s)，便于观察
APPROACH_STAGE1_DURATION_S = 5.0
APPROACH_STAGE2_DURATION_S = 3.5
APPROACH_STAGE3_DURATION_S = 2.5
# 夹紧后上提：与上方就位同高（APPROACH_ABOVE_Z_TARGET）；否则用相对偏移 POST_GRASP_LIFT_Z
POST_GRASP_LIFT_MATCH_APPROACH = True
POST_GRASP_LIFT_Z = 0.22
# 是否执行旧版后方预抓取（与三段位姿互斥，一般保持 False）
USE_PRE_GRASP = False

# 抓取结束后：放开夹爪 + 双臂回零位（等同 rostopic pub /kuavo_arm_target_poses ... values 全 0）
POST_GRASP_RELEASE_AND_HOME = True
ARM_HOME_DURATION_S = 2.0
ARM_HOME_JOINT_DEG = [0.0] * 14

# 姿态 quat_xyzw（相对 IK 基座）
PALM_DOWN_QUAT = [0.0, -0.70682518, 0.0, 0.70738827]
GRASP_QUAT_RIGHT = [-0.5002, -0.4998, -0.4998, 0.5002]
GRASP_QUAT_LEFT = [0.5002, -0.4998, -0.4998, 0.5002]

# 非抓取侧待机位（interface.md 官方示例）
INACTIVE_LEFT_POS = [0.45, 0.25, 0.11988012]
INACTIVE_RIGHT_POS = [0.45, -0.25, 0.11988012]

# 夹爪 / IK
GRASP_WIDTH = 90
GRASP_EFFORT = 1.5
GRASP_CLAW_VELOCITY = 50
IK_WAIT_TIMEOUT = 15.0
IK_SERVICE_CANDIDATES = (
    "/ik/two_arm_hand_pose_cmd_srv",
    "two_arm_hand_pose_cmd_srv",
)

# 默认同目录 grasp_target.json（可选，覆盖 CAMERA_POINT_M）
DEFAULT_GRASP_JSON = _SCRIPT_DIR / "grasp_target.json"

# =============================================================================
# 运行时变量（由坐标解算填充）
# =============================================================================

PRE_GRASP: Tuple[float, float, float] = (0.0, 0.0, 0.0)
APPROACH_UPPER_LEFT: Tuple[float, float, float] = (0.0, 0.0, 0.0)
APPROACH_ABOVE_TRANSIT: Tuple[float, float, float] = (0.0, 0.0, 0.0)
APPROACH_ABOVE: Tuple[float, float, float] = (0.0, 0.0, 0.0)
GRASP_POS: Tuple[float, float, float] = (0.0, 0.0, 0.0)
POST_GRASP_LIFT_MID: Tuple[float, float, float] = (0.0, 0.0, 0.0)
POST_GRASP_LIFT: Tuple[float, float, float] = (0.0, 0.0, 0.0)
RELEASE_RETREAT: Tuple[float, float, float] = (0.0, 0.0, 0.0)
RELEASE_LIFT: Tuple[float, float, float] = (0.0, 0.0, 0.0)
LIFT_POS: Tuple[float, float, float] = (0.0, 0.0, 0.0)
RETREAT: Tuple[float, float, float] = (0.0, 0.0, 0.0)
ACTIVE_GRASP_QUAT = list(GRASP_QUAT_RIGHT)
_LAST_IK_Q_ARM: Optional[List[float]] = None


def _grasp_claw_hand(hand: str) -> str:
    """抓取侧夹爪与 --hand 一致（left 模式闭合 left_claw）。"""
    return hand


def _build_config_dict() -> Dict:
    return {
        "static_transform": {
            "pitch_deg": PITCH_DEG,
            "camera_position_in_base": list(CAMERA_POSITION_IN_BASE),
            "lateral_sign": LATERAL_SIGN,
            "forward_depth_scale": FORWARD_DEPTH_SCALE,
            "height_from_depth_scale": HEIGHT_FROM_DEPTH_SCALE,
        },
        "grasp_offsets": {
            "forward_extra_m": FORWARD_EXTRA_M,
            "depth_forward_scale": DEPTH_FORWARD_SCALE,
            "center_y_bias": CENTER_Y_BIAS,
            "grasp_z_bias": GRASP_Z_BIAS,
            "temp_x": TEMP_X,
            "temp_y": TEMP_Y,
            "offset_z": OFFSET_Z,
            "left_grasp_x_bias": LEFT_GRASP_X_BIAS,
            "left_grasp_y_bias": LEFT_GRASP_Y_BIAS,
            "left_grasp_z_bias": LEFT_GRASP_Z_BIAS,
            "pre_grasp_back_m": PRE_GRASP_BACK_M,
            "pre_grasp_lift_z": PRE_GRASP_LIFT_Z,
            "retreat_back_m": RETREAT_BACK_M,
            "retreat_lift_z": RETREAT_LIFT_Z,
            "release_retreat_back_m": RELEASE_RETREAT_BACK_M,
            "post_grasp_min_lift_m": POST_GRASP_MIN_LIFT_M,
            "approach_above_z": APPROACH_ABOVE_Z,
            "approach_above_z_target": APPROACH_ABOVE_Z_TARGET,
            "approach_above_clearance_m": APPROACH_ABOVE_CLEARANCE_M,
            "use_three_stage_approach": USE_THREE_STAGE_APPROACH,
            "approach_upper_left_lateral_m": APPROACH_UPPER_LEFT_LATERAL_M,
            "approach_upper_left_back_m": APPROACH_UPPER_LEFT_BACK_M,
            "approach_upper_left_extra_z": APPROACH_UPPER_LEFT_EXTRA_Z,
            "post_grasp_lift_z": POST_GRASP_LIFT_Z,
            "post_grasp_lift_match_approach": POST_GRASP_LIFT_MATCH_APPROACH,
        },
        "end_effector_orientation": {
            "palm_down": list(PALM_DOWN_QUAT),
            "right": {"quat_xyzw": list(GRASP_QUAT_RIGHT)},
            "left": {"quat_xyzw": list(GRASP_QUAT_LEFT)},
        },
        "inactive_arm_pose": {
            "left": list(INACTIVE_LEFT_POS),
            "right": list(INACTIVE_RIGHT_POS),
        },
    }


def get_grasp_quat(hand: str, config: Optional[Dict] = None) -> List[float]:
    eo = (config or _build_config_dict())["end_effector_orientation"]
    key = "left" if hand == "left" else "right"
    return list(eo[key]["quat_xyzw"])


def get_inactive_arm_pose(hand: str, config: Optional[Dict] = None) -> List[float]:
    poses = (config or _build_config_dict())["inactive_arm_pose"]
    if hand == "right":
        return list(poses["left"])
    return list(poses["right"])


def _camera_optical_to_base_static(
    point_cam: Tuple[float, float, float],
    st: Dict,
) -> Tuple[float, float, float]:
    x_c, y_c, z_c = point_cam
    cx, cy, cz = st["camera_position_in_base"]
    p = math.radians(float(st["pitch_deg"]))
    c, s = math.cos(p), math.sin(p)
    fwd = float(st.get("forward_depth_scale", 1.0))
    h_scale = float(st.get("height_from_depth_scale", 1.0))
    x_b = cx + z_c * c * fwd + y_c * s * 0.5
    y_b = cy + float(st.get("lateral_sign", -1.0)) * x_c
    z_b = cz - z_c * s * h_scale + y_c * c * 0.15
    return (x_b, y_b, z_b)


def _vision_base_target(
    arm: Tuple[float, float, float],
    off: Dict,
    cam_x0: float,
) -> Tuple[float, float, float]:
    scale = float(off.get("depth_forward_scale", 1.0))
    cx, cy, cz = arm
    forward_part = cx - cam_x0
    gx = cam_x0 + forward_part * scale + float(off.get("forward_extra_m", 0.0))
    gy = cy + float(off.get("center_y_bias", 0.0))
    gz = cz + float(off.get("grasp_z_bias", 0.0))
    return (gx, gy, gz)


def _official_hand_grasp_pose(
    base: Tuple[float, float, float],
    hand: str,
    off: Dict,
) -> Tuple[float, float, float]:
    x, y, z = base
    tx = float(off.get("temp_x", -0.05))
    ty = float(off.get("temp_y", 0.05))
    tz = float(off.get("offset_z", -0.12))
    if hand == "left":
        lx = float(off.get("left_grasp_x_bias", 0.0))
        ly = float(off.get("left_grasp_y_bias", 0.0))
        lz = float(off.get("left_grasp_z_bias", 0.0))
        return (x + tx + lx, y + ty + ly, z + tz + lz)
    return (x + tx, y - ty, z + tz)


def resolve_grasp_poses_arm_base(
    point_cam: Tuple[float, float, float],
    hand: str = "right",
) -> Dict:
    cfg = _build_config_dict()
    st = cfg["static_transform"]
    off = cfg["grasp_offsets"]
    cam_x0 = float(st["camera_position_in_base"][0])

    arm = _camera_optical_to_base_static(point_cam, st)
    base = _vision_base_target(arm, off, cam_x0)
    grasp = _official_hand_grasp_pose(base, hand, off)

    pre_back = float(off["pre_grasp_back_m"])
    pre_lift = float(off["pre_grasp_lift_z"])
    ret_back = float(off["retreat_back_m"])
    ret_lift = float(off["retreat_lift_z"])
    post_lift = float(off.get("post_grasp_lift_z", 0.0))
    above_z = float(off.get("approach_above_z", 0.0))
    above_target = off.get("approach_above_z_target")

    pre = (grasp[0] - pre_back, grasp[1], grasp[2] + pre_lift)
    clearance = float(off.get("approach_above_clearance_m", 0.18))
    z_from_grasp = grasp[2] + clearance
    if above_target is not None:
        z_abs = float(above_target)
        approach_z = min(z_abs, z_from_grasp)
        approach_above = (grasp[0], grasp[1], approach_z)
    else:
        approach_above = (grasp[0], grasp[1], grasp[2] + above_z)

    match_approach = bool(off.get("post_grasp_lift_match_approach", False))
    if match_approach and above_target is not None:
        lift = (grasp[0], grasp[1], approach_above[2])
    else:
        lift = (grasp[0], grasp[1], grasp[2] + post_lift)
    retreat = (grasp[0] - ret_back, grasp[1], lift[2] + ret_lift)
    rel_back = float(off.get("release_retreat_back_m", 0.12))
    min_lift = float(off.get("post_grasp_min_lift_m", 0.20))
    lift_z = max(approach_above[2], grasp[2] + min_lift)
    post_grasp_lift = (grasp[0], grasp[1], lift_z)
    mid_lift_z = grasp[2] + min_lift * 0.5
    post_grasp_lift_mid = (grasp[0], grasp[1], mid_lift_z)
    release_retreat = (grasp[0] - rel_back, grasp[1], grasp[2])

    use_three = bool(off.get("use_three_stage_approach", True))
    lateral = float(off.get("approach_upper_left_lateral_m", 0.22))
    back_m = float(off.get("approach_upper_left_back_m", 0.10))
    extra_z = float(off.get("approach_upper_left_extra_z", 0.12))
    lat_sign = 1.0 if hand == "left" else -1.0
    if use_three:
        approach_upper_left = (
            grasp[0] - back_m,
            grasp[1] + lat_sign * lateral,
            approach_above[2] + extra_z,
        )
    else:
        approach_upper_left = approach_above

    approach_above_transit = (
        grasp[0],
        grasp[1],
        approach_upper_left[2] if use_three else approach_above[2],
    )

    return {
        "camera_coord_m": list(point_cam),
        "base_target_m": list(base),
        "arm_coord_m": list(grasp),
        "pre_grasp": list(pre),
        "approach_upper_left": list(approach_upper_left),
        "approach_above_transit": list(approach_above_transit),
        "approach_above": list(approach_above),
        "grasp": list(grasp),
        "post_grasp_lift_mid": list(post_grasp_lift_mid),
        "post_grasp_lift": list(post_grasp_lift),
        "release_retreat": list(release_retreat),
        "lift": list(lift),
        "retreat": list(retreat),
        "transform_method": "embedded_static_pitch",
        "grasp_quat_xyzw": get_grasp_quat(hand),
        "inactive_arm_pose": get_inactive_arm_pose(hand),
    }


def _log(msg: str) -> None:
    print(msg, flush=True)


def _bootstrap_kuavo_python_path() -> None:
    candidates = []
    if os.environ.get("PYTHONPATH"):
        candidates.extend(p for p in os.environ["PYTHONPATH"].split(":") if p)
    home = os.path.expanduser("~")
    for base in ("/home/lab", home, "/opt"):
        if os.path.isdir(base):
            candidates.extend(glob.glob(
                os.path.join(base, "*", "devel", "lib", "python3", "dist-packages")
            ))
    for fixed in (
        "/home/lab/kuavo-ros-opensource/devel/lib/python3/dist-packages",
        "/home/lab/kuavo-ros-control/devel/lib/python3/dist-packages",
        os.path.join(home, "kuavo-ros-opensource/devel/lib/python3/dist-packages"),
    ):
        candidates.append(fixed)

    added = []
    seen = set()
    for p in candidates:
        if p and p not in seen and os.path.isdir(p) and p not in sys.path:
            seen.add(p)
            sys.path.insert(0, p)
            added.append(p)
    if added:
        _log("[环境] 已添加 Python 路径:")
        for p in added:
            _log(f"       {p}")


def _check_ros_packages() -> None:
    _bootstrap_kuavo_python_path()
    missing = []
    for mod in ("kuavo_sdk", "motion_capture_ik"):
        try:
            __import__(mod)
            _log(f"[环境] {mod} OK")
        except ImportError:
            missing.append(mod)
    if missing:
        _log("[错误] 缺少: " + ", ".join(missing))
        _log("请先: source /opt/ros/noetic/setup.bash")
        _log("      source .../kuavo-ros-opensource/devel/setup.bash")
        raise SystemExit(1)


def _rad_to_deg_14(q_rad) -> list:
    return [math.degrees(float(x)) for x in q_rad[:14]]


def _call_with_retry(fn, label: str, retries: int = 3, pause: float = 1.0):
    import rospy

    last_err = None
    for i in range(retries):
        try:
            return fn()
        except rospy.exceptions.ROSException as e:
            last_err = e
            _log(f"[{label}] 失败 ({i + 1}/{retries}): {e}")
            if i + 1 < retries:
                rospy.sleep(pause)
    raise last_err


def _wait_for_connections(pub, timeout: float = 5.0) -> bool:
    import rospy

    t0 = rospy.Time.now().to_sec()
    while pub.get_num_connections() == 0:
        if rospy.Time.now().to_sec() - t0 > timeout:
            return False
        rospy.sleep(0.05)
    return True


def _resolve_ik_proxy():
    import rospy
    from motion_capture_ik.srv import twoArmHandPoseCmdSrv

    last_err = None
    for name in IK_SERVICE_CANDIDATES:
        try:
            _log(f"[IK] 等待服务: {name}")
            rospy.wait_for_service(name, timeout=IK_WAIT_TIMEOUT)
            proxy = rospy.ServiceProxy(name, twoArmHandPoseCmdSrv)
            _log(f"[IK] 已连接: {name}")
            return proxy
        except Exception as e:
            last_err = e
            _log(f"[IK] 不可用 {name}: {e}")
    raise RuntimeError(f"未找到 IK 服务: {last_err}")

def _solve_ik(ik_proxy, pos, hand: str, *, use_prev_q0: bool = True, use_grasp_quat: bool = True):
    global _LAST_IK_Q_ARM
    import numpy as np
    from motion_capture_ik.msg import twoArmHandPoseCmd

    req = twoArmHandPoseCmd()
    req.use_custom_ik_param = False
    req.joint_angles_as_q0 = False
    zero3 = np.zeros(3)

    grasp_q = np.array(ACTIVE_GRASP_QUAT, dtype=float)
    down_q = np.array(PALM_DOWN_QUAT, dtype=float)
    active_q = grasp_q if use_grasp_quat else down_q

    left_pos = list(INACTIVE_LEFT_POS)
    right_pos = list(INACTIVE_RIGHT_POS)
    if hand == "left":
        left_pos = list(pos)
        left_q = active_q
        right_q = down_q
        q0_slice = slice(0, 7)
    else:
        right_pos = list(pos)
        right_q = active_q
        left_q = down_q
        q0_slice = slice(7, 14)

    req.hand_poses.left_pose.pos_xyz = np.array(left_pos, dtype=float)
    req.hand_poses.left_pose.quat_xyzw = left_q
    req.hand_poses.left_pose.elbow_pos_xyz = zero3
    req.hand_poses.right_pose.pos_xyz = np.array(right_pos, dtype=float)
    req.hand_poses.right_pose.quat_xyzw = right_q
    req.hand_poses.right_pose.elbow_pos_xyz = zero3

    if use_prev_q0 and _LAST_IK_Q_ARM is not None and len(_LAST_IK_Q_ARM) >= 14:
        req.joint_angles_as_q0 = True
        seed = np.array(_LAST_IK_Q_ARM[q0_slice], dtype=float)
        if hand == "left":
            req.hand_poses.left_pose.joint_angles = seed
        else:
            req.hand_poses.right_pose.joint_angles = seed

    try:
        resp = _call_with_retry(lambda: ik_proxy(req), "IK", retries=2, pause=1.5)
    except Exception as e:
        _log(f"[IK] 服务通信失败 pos={pos}: {e}")
        return None

    if not resp.success:
        _log(f"[IK] 求解失败 pos={pos}")
        return None
    _log(f"[IK] 成功 time_cost={getattr(resp, 'time_cost', '?')}ms")
    _LAST_IK_Q_ARM = list(resp.q_arm)
    return list(resp.q_arm)


def _set_arm_mode_external() -> bool:
    import subprocess
    import rospy
    from kuavo_sdk.srv import changeArmCtrlMode, changeArmCtrlModeRequest

    _log("[1] 调用 /arm_traj_change_mode (mode=2) ...")

    def _do_call():
        rospy.wait_for_service("/arm_traj_change_mode", timeout=8.0)
        cli = rospy.ServiceProxy("/arm_traj_change_mode", changeArmCtrlMode)
        req = changeArmCtrlModeRequest()
        req.control_mode = 2
        return cli(req)

    try:
        res = _call_with_retry(_do_call, "arm_traj_change_mode", retries=2)
        if not res.result:
            _log(f"[手臂] mode 失败: {res.message}")
            return False
        _log("[手臂] 外部控制 mode=2 OK")
        return True
    except Exception as e:
        _log(f"[手臂] mode 失败: {e}")
        try:
            subprocess.run(
                ["rosservice", "call", "/arm_traj_change_mode", "control_mode: 2"],
                check=True, timeout=15, capture_output=True, text=True,
            )
            return True
        except Exception:
            return False


def _publish_arm_timed(pub, q_rad, duration: float) -> None:
    import rospy
    from kuavo_sdk.msg import armTargetPoses

    msg = armTargetPoses()
    msg.times = [float(duration)]
    msg.values = _rad_to_deg_14(q_rad)
    for _ in range(3):
        pub.publish(msg)
        rospy.sleep(0.05)
    rospy.sleep(duration + 0.5)


def _move_vertical_lift(
    ik_proxy, arm_pub, pos, hand: str, duration: float, label: str,
    use_target_poses: bool, from_pos: tuple,
) -> bool:
    """夹紧后纯垂直上提：先中点再目标，抓取姿态失败时尝试掌心朝下。"""
    import rospy

    dz = pos[2] - from_pos[2]
    _log(f"[运动] {label} -> ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f}) ΔZ={dz:+.3f}m")
    for use_grasp in (True, False):
        q = _solve_ik(
            ik_proxy, pos, hand,
            use_prev_q0=use_grasp,
            use_grasp_quat=use_grasp,
        )
        if q is not None:
            if not use_grasp:
                _log(f"[运动] {label} 使用掌心朝下 IK")
            if use_target_poses and arm_pub is not None:
                _publish_arm_timed(arm_pub, q, duration)
            else:
                _publish_arm_traj(q, duration)
            return True
    return False


def _publish_arm_traj(q_rad, duration: float) -> None:
    import rospy
    from sensor_msgs.msg import JointState

    pub = rospy.Publisher("/kuavo_arm_traj", JointState, queue_size=10, latch=True)
    _wait_for_connections(pub, timeout=5.0)
    msg = JointState()
    msg.name = [f"arm_joint_{i}" for i in range(1, 15)]
    msg.header.stamp = rospy.Time.now()
    msg.position = _rad_to_deg_14(q_rad)
    for _ in range(3):
        pub.publish(msg)
        rospy.sleep(0.1)
    rospy.sleep(duration)


def _publish_arm_home(arm_pub, use_target_poses: bool, duration: float) -> None:
    """发布双臂回零位目标（14 关节角全 0°，与官方 rostopic 示例一致）。"""
    import rospy

    home_deg = list(ARM_HOME_JOINT_DEG)
    _log(f"[结束] 双臂回零位 times=[{duration}] values={home_deg}")
    if use_target_poses and arm_pub is not None:
        from kuavo_sdk.msg import armTargetPoses

        msg = armTargetPoses()
        msg.times = [float(duration)]
        msg.values = home_deg
        for _ in range(3):
            arm_pub.publish(msg)
            rospy.sleep(0.05)
        rospy.sleep(duration + 0.5)
        return

    from sensor_msgs.msg import JointState

    pub = rospy.Publisher("/kuavo_arm_traj", JointState, queue_size=10, latch=True)
    _wait_for_connections(pub, timeout=5.0)
    msg = JointState()
    msg.name = [f"arm_joint_{i}" for i in range(1, 15)]
    msg.header.stamp = rospy.Time.now()
    msg.position = home_deg
    for _ in range(3):
        pub.publish(msg)
        rospy.sleep(0.1)
    rospy.sleep(duration)
    _log("[结束] 已通过 /kuavo_arm_traj 回零位")


def _finish_release_and_home(
    claw_hand: str,
    arm_pub,
    use_target_poses: bool,
    skip_gripper: bool,
    *,
    open_claw: bool = True,
) -> None:
    import rospy

    if not POST_GRASP_RELEASE_AND_HOME:
        return
    _log("========== 结束：双臂回零位 ==========")
    if open_claw and not skip_gripper:
        _claw_cmd(claw_hand, 0)
        rospy.sleep(0.5)
    _publish_arm_home(arm_pub, use_target_poses, ARM_HOME_DURATION_S)


def _log_waypoint_delta(a: tuple, b: tuple, label: str) -> None:
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    dz = b[2] - a[2]
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    _log(f"[路径] {label}: ΔX={dx:+.3f} ΔY={dy:+.3f} ΔZ={dz:+.3f} 距离={dist:.3f}m")


def _move_to(ik_proxy, arm_pub, pos, hand: str, duration: float, label: str,
             use_target_poses: bool, hold_s: float = 0.0) -> bool:
    import rospy

    _log(f"[运动] {label} -> ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")
    q = _solve_ik(ik_proxy, pos, hand, use_prev_q0=True)
    if q is None:
        return False
    if use_target_poses and arm_pub is not None:
        _publish_arm_timed(arm_pub, q, duration)
    else:
        _publish_arm_traj(q, duration)
    if hold_s > 0.0:
        _log(f"[运动] {label} 到位，保持 {hold_s:.1f}s ...")
        rospy.sleep(hold_s)
    return True


def _claw_cmd(hand: str, position: int, velocity: int = GRASP_CLAW_VELOCITY,
              effort: float = GRASP_EFFORT) -> bool:
    import rospy
    from kuavo_sdk.srv import controlLejuClaw, controlLejuClawRequest

    claw = f"{hand}_claw"

    def _do_claw():
        rospy.wait_for_service("/control_robot_leju_claw", timeout=8.0)
        cli = rospy.ServiceProxy("/control_robot_leju_claw", controlLejuClaw)
        req = controlLejuClawRequest()
        req.data.name = [claw]
        req.data.position = [float(position)]
        req.data.velocity = [float(velocity)]
        req.data.effort = [float(effort)]
        return cli(req)

    try:
        res = _call_with_retry(_do_claw, "夹爪", retries=2)
    except Exception as e:
        _log(f"[夹爪] 失败: {e}")
        return False
    if not res.success:
        return False
    _log(f"[夹爪] {claw} pos={position}")
    return True


def _load_camera_point_from_json(path: Path) -> tuple:
    data = json.loads(path.read_text(encoding="utf-8"))
    cc = data.get("camera_coord_m")
    if cc and len(cc) >= 3:
        return (float(cc[0]), float(cc[1]), float(cc[2]))
    raise ValueError(f"{path} 缺少 camera_coord_m")


def _apply_grasp_coordinates(camera_point: tuple, hand: str) -> None:
    global PRE_GRASP, APPROACH_UPPER_LEFT, APPROACH_ABOVE_TRANSIT, APPROACH_ABOVE
    global GRASP_POS, POST_GRASP_LIFT_MID, POST_GRASP_LIFT, RELEASE_RETREAT, RELEASE_LIFT, LIFT_POS, RETREAT
    global ACTIVE_GRASP_QUAT, INACTIVE_LEFT_POS, INACTIVE_RIGHT_POS

    poses = resolve_grasp_poses_arm_base(camera_point, hand=hand)
    PRE_GRASP = tuple(poses["pre_grasp"])
    APPROACH_UPPER_LEFT = tuple(poses["approach_upper_left"])
    APPROACH_ABOVE_TRANSIT = tuple(poses["approach_above_transit"])
    APPROACH_ABOVE = tuple(poses["approach_above"])
    GRASP_POS = tuple(poses["grasp"])
    POST_GRASP_LIFT_MID = tuple(poses["post_grasp_lift_mid"])
    POST_GRASP_LIFT = tuple(poses["post_grasp_lift"])
    RELEASE_RETREAT = tuple(poses["release_retreat"])
    LIFT_POS = tuple(poses["lift"])
    RELEASE_LIFT = (RELEASE_RETREAT[0], RELEASE_RETREAT[1], LIFT_POS[2])
    RETREAT = tuple(poses["retreat"])
    ACTIVE_GRASP_QUAT = list(poses["grasp_quat_xyzw"])

    inact = poses["inactive_arm_pose"]
    if hand == "right":
        INACTIVE_LEFT_POS = list(inact)
    else:
        INACTIVE_RIGHT_POS = list(inact)

    _log(f"[坐标] 手: {hand}")
    _log(f"[坐标] 相机 optical (m): {camera_point}")
    _log(f"[坐标] 视觉中心 (m): {poses['base_target_m']}")
    _log(f"[坐标] 抓取点 (m): {GRASP_POS}")
    if POST_GRASP_HORIZONTAL_RELEASE:
        _log(f"[坐标] 夹紧后上提中点 (m): {POST_GRASP_LIFT_MID}")
        _log(f"[坐标] 夹紧后上提正上方 (m): {POST_GRASP_LIFT}")
        _log(f"[坐标] 下放抓取点 (m): {GRASP_POS}")
        _log(f"[坐标] 水平后撤放开 (m): {RELEASE_RETREAT}")
        _log(f"[坐标] 松爪后上提 (m): {RELEASE_LIFT}")
    _log(f"[坐标] 预抓取 (m): {PRE_GRASP}")
    if USE_THREE_STAGE_APPROACH:
        _log(f"[坐标] 左上方就位 (m): {APPROACH_UPPER_LEFT}")
        _log(f"[坐标] 正上方平移 (m): {APPROACH_ABOVE_TRANSIT}")
        _log(f"[坐标] 正上方就位 (m): {APPROACH_ABOVE}")
        _log_waypoint_delta(APPROACH_UPPER_LEFT, APPROACH_ABOVE_TRANSIT, "左上方→正上方平移")
        _log_waypoint_delta(APPROACH_ABOVE_TRANSIT, APPROACH_ABOVE, "正上方平移→正上方就位")
        _log_waypoint_delta(APPROACH_ABOVE, GRASP_POS, "正上方→抓取点")
    else:
        _log(f"[坐标] 正上方就位 (m): {APPROACH_ABOVE}")
    _log(f"[坐标] 上提 (m): {LIFT_POS}")
    _log(f"[坐标] 后撤 (m): {RETREAT}")
    _log(f"[姿态] quat_xyzw: {ACTIVE_GRASP_QUAT}")
    _log("[提示] 调参请编辑本文件顶部「用户参数区」")


def run_grasp(hand: str, grasp_width: int, grasp_effort: float,
              skip_gripper: bool, skip_arm_mode: bool,
              camera_point: tuple) -> bool:
    global _LAST_IK_Q_ARM
    import rospy

    _LAST_IK_Q_ARM = None
    claw_hand = _grasp_claw_hand(hand)
    rospy.init_node("grasp_from_offline_vision", anonymous=True)
    _apply_grasp_coordinates(camera_point, hand)

    if hand == "left":
        _log("[策略] --hand left：左手 IK 双臂运动，抓取由 left_claw 开合")
    if USE_THREE_STAGE_APPROACH:
        _log("[策略] 三段位姿：… → 闭合 → 上提正上方 → 下放抓取点 → 水平后撤放开 → 回零")
        _log(
            f"[策略] 全程抓取姿态 quat={ACTIVE_GRASP_QUAT}；段间停顿 {APPROACH_STAGE_HOLD_S}s"
        )
    else:
        _log("[策略] 垂直流程：正上方 → 下降抓取 → 闭合 → 向上提起 → 后撤")
    if POST_GRASP_RELEASE_AND_HOME:
        _log(f"[策略] 结束后回零位 ({ARM_HOME_DURATION_S}s)")
    if POST_GRASP_HORIZONTAL_RELEASE:
        _log(
            f"[策略] 夹紧后上提至正上方，保持 {POST_GRASP_HOLD_AT_ABOVE_S}s，"
            f"下放抓取点，再水平后撤 {RELEASE_RETREAT_BACK_M}m 后松爪"
        )

    if not skip_arm_mode:
        _set_arm_mode_external()
        rospy.sleep(0.5)

    use_target_poses = False
    arm_pub = None
    try:
        from kuavo_sdk.msg import armTargetPoses
        arm_pub = rospy.Publisher(
            "/kuavo_arm_target_poses", armTargetPoses, queue_size=10, latch=True
        )
        if _wait_for_connections(arm_pub, timeout=3.0):
            use_target_poses = True
            _log("[手臂] /kuavo_arm_target_poses")
    except Exception:
        _log("[手臂] 改用 /kuavo_arm_traj")

    ik_proxy = _resolve_ik_proxy()

    if not skip_gripper:
        _claw_cmd(claw_hand, 0)
        rospy.sleep(0.8)

    hold = APPROACH_STAGE_HOLD_S if USE_THREE_STAGE_APPROACH else 0.0

    if USE_PRE_GRASP and not USE_THREE_STAGE_APPROACH:
        if not _move_to(ik_proxy, arm_pub, PRE_GRASP, hand, 2.0, "后方就位", use_target_poses):
            return False
    if USE_THREE_STAGE_APPROACH:
        _log("========== 第 1/3 段：左上方（高 + 左 + 后） ==========")
        if not _move_to(
            ik_proxy, arm_pub, APPROACH_UPPER_LEFT, hand, APPROACH_STAGE1_DURATION_S,
            "左上方就位", use_target_poses, hold_s=hold,
        ):
            return False
        _log("========== 第 2/3 段：平移至物品正上方 ==========")
        if not _move_to(
            ik_proxy, arm_pub, APPROACH_ABOVE_TRANSIT, hand, APPROACH_STAGE2_DURATION_S * 0.6,
            "平移至正上方(高位)", use_target_poses,
        ):
            return False
        if not _move_to(
            ik_proxy, arm_pub, APPROACH_ABOVE, hand, APPROACH_STAGE2_DURATION_S * 0.4,
            "正上方就位", use_target_poses, hold_s=hold,
        ):
            return False
        _log("========== 第 3/3 段：垂直下降抓取 ==========")
        if not _move_to(
            ik_proxy, arm_pub, GRASP_POS, hand, APPROACH_STAGE3_DURATION_S,
            "垂直下降抓取", use_target_poses,
        ):
            return False
    else:
        if not _move_to(ik_proxy, arm_pub, APPROACH_ABOVE, hand, 3.5, "正上方就位", use_target_poses):
            return False
        if not _move_to(ik_proxy, arm_pub, GRASP_POS, hand, 3.5, "垂直下降抓取", use_target_poses):
            return False

    if not skip_gripper:
        _claw_cmd(claw_hand, grasp_width, effort=grasp_effort)
        rospy.sleep(1.5)

    if POST_GRASP_HORIZONTAL_RELEASE:
        _log("========== 夹紧后上提至正上方（展示抓稳） ==========")
        if not _move_vertical_lift(
            ik_proxy, arm_pub, POST_GRASP_LIFT_MID, hand, POST_GRASP_LIFT_MID_DURATION_S,
            "垂直上提(中点)", use_target_poses, GRASP_POS,
        ):
            return False
        if not _move_vertical_lift(
            ik_proxy, arm_pub, POST_GRASP_LIFT, hand, POST_GRASP_LIFT_TO_ABOVE_DURATION_S,
            "垂直上提(正上方)", use_target_poses, POST_GRASP_LIFT_MID,
        ):
            return False
        _log(f"[运动] 正上方就位，保持 {POST_GRASP_HOLD_AT_ABOVE_S}s ...")
        rospy.sleep(POST_GRASP_HOLD_AT_ABOVE_S)
        _log("========== 下放回抓取点 ==========")
        if not _move_to(
            ik_proxy, arm_pub, GRASP_POS, hand, POST_GRASP_LOWER_TO_GRASP_DURATION_S,
            "下放至抓取点", use_target_poses,
        ):
            return False
        _log("========== 安全放开：水平后撤（保持抓取高度） ==========")
        if not _move_to(
            ik_proxy, arm_pub, RELEASE_RETREAT, hand, RELEASE_RETREAT_DURATION_S,
            "水平后撤", use_target_poses,
        ):
            return False
        if not skip_gripper:
            _claw_cmd(claw_hand, 0)
            rospy.sleep(0.8)
        _log("========== 松爪后上提 ==========")
        if not _move_to(
            ik_proxy, arm_pub, RELEASE_LIFT, hand, RELEASE_LIFT_DURATION_S,
            "松爪后上提", use_target_poses,
        ):
            return False
    else:
        if not _move_to(ik_proxy, arm_pub, LIFT_POS, hand, 4.0, "向上提起", use_target_poses):
            return False
        if not _move_to(ik_proxy, arm_pub, RETREAT, hand, 2.0, "后撤", use_target_poses):
            return False
        if not skip_gripper:
            _claw_cmd(claw_hand, 0)
            rospy.sleep(0.5)

    _finish_release_and_home(claw_hand, arm_pub, use_target_poses, skip_gripper, open_claw=False)

    _log(f"[完成] 抓取流程结束（IK={hand}，夹爪={claw_hand}）")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="固定坐标抓取（单文件，参数在脚本顶部用户参数区）"
    )
    parser.add_argument("--hand", choices=("left", "right"), default="right")
    parser.add_argument("--grasp-width", type=int, default=GRASP_WIDTH)
    parser.add_argument("--grasp-effort", type=float, default=GRASP_EFFORT)
    parser.add_argument("--skip-gripper", action="store_true")
    parser.add_argument("--skip-arm-mode", action="store_true")
    parser.add_argument(
        "--grasp-json",
        default=str(DEFAULT_GRASP_JSON),
        help="含 camera_coord_m 的 JSON，默认同目录 grasp_target.json",
    )
    parser.add_argument(
        "--camera-coord", nargs=3, type=float, metavar=("X", "Y", "Z"),
        help="覆盖 JSON/默认，直接指定相机 optical 坐标 (m)",
    )
    parser.add_argument("--dry-coords", action="store_true",
                        help="只打印坐标，不控制机械臂")
    args = parser.parse_args()

    if args.camera_coord:
        camera_point = tuple(args.camera_coord)
    else:
        jpath = Path(args.grasp_json)
        if jpath.is_file():
            camera_point = _load_camera_point_from_json(jpath)
        else:
            camera_point = CAMERA_POINT_M
            _log(f"[坐标] 未找到 {jpath}，使用脚本内 CAMERA_POINT_M")

    if args.dry_coords:
        _apply_grasp_coordinates(camera_point, args.hand)
        if args.hand == "left":
            _log("[策略] 实机 --hand left：左手 IK 运动 + left_claw 抓取")
        return 0

    _check_ros_packages()
    try:
        ok = run_grasp(
            hand=args.hand,
            grasp_width=args.grasp_width,
            grasp_effort=args.grasp_effort,
            skip_gripper=args.skip_gripper,
            skip_arm_mode=args.skip_arm_mode,
            camera_point=camera_point,
        )
        return 0 if ok else 1
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
