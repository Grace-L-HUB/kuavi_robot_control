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

  # --hand left：左手 IK 双臂就位，到位后由 left_claw 抓取
  python3 grasp_from_offline_vision.py --hand left

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
# +X 前伸；-Y 向中心收；-Z 压低（水平已准，主要调 Z）
LEFT_GRASP_X_BIAS = -0.015
LEFT_GRASP_Y_BIAS = -0.01
LEFT_GRASP_Z_BIAS = -0.485

# 预抓取 / 后撤（沿 base X：预抓取在抓取点后方 -X）
PRE_GRASP_BACK_M = 0.10
PRE_GRASP_LIFT_Z = 0.03
RETREAT_BACK_M = 0.08
RETREAT_LIFT_Z = 0.05

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
GRASP_POS: Tuple[float, float, float] = (0.0, 0.0, 0.0)
RETREAT: Tuple[float, float, float] = (0.0, 0.0, 0.0)
ACTIVE_GRASP_QUAT = list(GRASP_QUAT_RIGHT)


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

    pre = (grasp[0] - pre_back, grasp[1], grasp[2] + pre_lift)
    retreat = (grasp[0] - ret_back, grasp[1], grasp[2] + ret_lift)

    return {
        "camera_coord_m": list(point_cam),
        "base_target_m": list(base),
        "arm_coord_m": list(grasp),
        "pre_grasp": list(pre),
        "grasp": list(grasp),
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


def _solve_ik(ik_proxy, pos, hand: str):
    import numpy as np
    from motion_capture_ik.msg import twoArmHandPoseCmd

    req = twoArmHandPoseCmd()
    req.use_custom_ik_param = False
    req.joint_angles_as_q0 = False
    zero3 = np.zeros(3)

    grasp_q = np.array(ACTIVE_GRASP_QUAT, dtype=float)
    down_q = np.array(PALM_DOWN_QUAT, dtype=float)

    left_pos = list(INACTIVE_LEFT_POS)
    right_pos = list(INACTIVE_RIGHT_POS)
    if hand == "left":
        left_pos = list(pos)
        left_q = grasp_q
        right_q = down_q
    else:
        right_pos = list(pos)
        right_q = grasp_q
        left_q = down_q

    req.hand_poses.left_pose.pos_xyz = np.array(left_pos, dtype=float)
    req.hand_poses.left_pose.quat_xyzw = left_q
    req.hand_poses.left_pose.elbow_pos_xyz = zero3
    req.hand_poses.right_pose.pos_xyz = np.array(right_pos, dtype=float)
    req.hand_poses.right_pose.quat_xyzw = right_q
    req.hand_poses.right_pose.elbow_pos_xyz = zero3

    try:
        resp = _call_with_retry(lambda: ik_proxy(req), "IK", retries=2, pause=1.5)
    except Exception as e:
        _log(f"[IK] 服务通信失败 pos={pos}: {e}")
        return None

    if not resp.success:
        _log(f"[IK] 求解失败 pos={pos}")
        return None
    _log(f"[IK] 成功 time_cost={getattr(resp, 'time_cost', '?')}ms")
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
    pub.publish(msg)
    rospy.sleep(duration + 0.5)


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


def _move_to(ik_proxy, arm_pub, pos, hand: str, duration: float, label: str,
             use_target_poses: bool) -> bool:
    _log(f"[运动] {label} -> ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")
    q = _solve_ik(ik_proxy, pos, hand)
    if q is None:
        return False
    if use_target_poses and arm_pub is not None:
        _publish_arm_timed(arm_pub, q, duration)
    else:
        _publish_arm_traj(q, duration)
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
    global PRE_GRASP, GRASP_POS, RETREAT
    global ACTIVE_GRASP_QUAT, INACTIVE_LEFT_POS, INACTIVE_RIGHT_POS

    poses = resolve_grasp_poses_arm_base(camera_point, hand=hand)
    PRE_GRASP = tuple(poses["pre_grasp"])
    GRASP_POS = tuple(poses["grasp"])
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
    _log(f"[坐标] 预抓取 (m): {PRE_GRASP}")
    _log(f"[坐标] 后撤 (m): {RETREAT}")
    _log(f"[姿态] quat_xyzw: {ACTIVE_GRASP_QUAT}")
    _log("[提示] 调参请编辑本文件顶部「用户参数区」")


def run_grasp(hand: str, grasp_width: int, grasp_effort: float,
              skip_gripper: bool, skip_arm_mode: bool,
              camera_point: tuple) -> bool:
    import rospy

    claw_hand = _grasp_claw_hand(hand)
    rospy.init_node("grasp_from_offline_vision", anonymous=True)
    _apply_grasp_coordinates(camera_point, hand)

    if hand == "left":
        _log("[策略] --hand left：左手 IK 双臂运动，抓取由 left_claw 开合")

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

    if not _move_to(ik_proxy, arm_pub, PRE_GRASP, hand, 2.0, "后方就位", use_target_poses):
        return False
    if not _move_to(ik_proxy, arm_pub, GRASP_POS, hand, 3.0, "前伸抓取", use_target_poses):
        return False

    if not skip_gripper:
        _claw_cmd(claw_hand, grasp_width, effort=grasp_effort)
        rospy.sleep(1.5)

    if not _move_to(ik_proxy, arm_pub, RETREAT, hand, 2.0, "后撤", use_target_poses):
        return False

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
