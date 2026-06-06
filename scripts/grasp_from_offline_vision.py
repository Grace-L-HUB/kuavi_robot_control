#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
固定坐标抓取（单文件，对齐 Kuavo 开源 SDK / interface.md）。

【重要】必须先 source Kuavo 工作空间，否则 No module named 'kuavo_sdk'：
  source /opt/ros/noetic/setup.bash
  source /home/lab/kuavo-ros-control/devel/setup.bash   # 按实际路径修改
  python3 scripts/grasp_from_offline_vision.py --hand right

脚本放在 opensource/scripts 时:
  cd /path/to/opensource/scripts
  bash run_grasp.sh --hand right

或一键（在 Kuavi_bot_control 仓库内）:
  bash scripts/run_grasp.sh --hand right
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

# 允许从 Kuavi_bot_control 或 opensource 旁路导入 vision_lim
_SCRIPT_DIR = Path(__file__).resolve().parent
for _repo in (_SCRIPT_DIR.parent, _SCRIPT_DIR.parent.parent):
    _vl = _repo / "vision_lim"
    if _vl.is_dir() and str(_repo) not in sys.path:
        sys.path.insert(0, str(_repo))

try:
    from vision_lim.wheeled_camera_transform import (
        DEFAULT_CAMERA_POINT,
        get_grasp_quat,
        get_inactive_arm_pose,
        load_wheeled_camera_config,
        resolve_grasp_poses_arm_base,
    )
except ImportError:
    DEFAULT_CAMERA_POINT = (-0.013972711859484142, 0.0325017152875609, 0.772)

    def load_wheeled_camera_config(path=None):
        return {
            "camera_frame": "camera_depth_optical_frame",
            "ik_target_frames": ["base_link", "torso", "pelvis"],
            "static_transform": {
                "pitch_deg": 51.0,
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
                "left_z_fine": 0.0,
                "grasp_depth_z": 0.0,
                "pre_grasp_back_m": 0.10,
                "pre_grasp_lift_z": 0.03,
                "retreat_back_m": 0.08,
                "retreat_lift_z": 0.05,
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

    def get_grasp_quat(hand, config=None):
        eo = (config or load_wheeled_camera_config()).get("end_effector_orientation", {})
        key = "left" if hand == "left" else "right"
        block = eo.get(key, {})
        if isinstance(block, dict) and block.get("quat_xyzw"):
            return list(block["quat_xyzw"])
        return list(eo.get("palm_down", [0.0, -0.70682518, 0.0, 0.70738827]))

    def get_inactive_arm_pose(hand, config=None):
        p = (config or load_wheeled_camera_config()).get("inactive_arm_pose", {})
        return list(p.get("left", [0.45, 0.25, 0.12])) if hand == "right" else list(
            p.get("right", [0.45, -0.25, 0.12])
        )

    def resolve_grasp_poses_arm_base(point_cam, config=None, use_tf=False, hand="right"):
        cfg = config or load_wheeled_camera_config()
        st = cfg["static_transform"]
        off = cfg.get("grasp_offsets", {})
        p = math.radians(float(st["pitch_deg"]))
        c, s = math.cos(p), math.sin(p)
        x_c, y_c, z_c = point_cam
        cx, cy, cz = st["camera_position_in_base"]
        lat = float(st.get("lateral_sign", -1.0))
        x_b = cx + z_c * c + y_c * s + float(off.get("forward_extra_m", 0.02))
        y_b = cy + lat * x_c + float(off.get("center_y_bias", 0.02))
        z_b = cz - z_c * s + y_c * c * 0.15 + float(off.get("grasp_z_bias", 0.0))
        grasp_ref = (x_b, y_b, z_b)
        if hand == "left" and off.get("symmetric_mirror_y", True):
            inactive = cfg.get("inactive_arm_pose", {})
            ref_z = float(inactive.get("right", [0.45, -0.25, 0.11988012])[2])
            grasp = (
                grasp_ref[0],
                -grasp_ref[1] + float(off.get("left_y_fine", 0.0)),
                (ref_z if off.get("left_grasp_z_from_inactive", True) else grasp_ref[2])
                + float(off.get("left_z_fine", 0.0)),
            )
        else:
            grasp = grasp_ref
        pre_lift = float(off.get("pre_grasp_lift_z", 0.03))
        ret_lift = float(off.get("retreat_lift_z", 0.05))
        pre = (
            grasp[0] - float(off.get("pre_grasp_back_m", 0.14)),
            grasp[1],
            grasp[2] + pre_lift,
        )
        retreat = (
            grasp[0] - float(off.get("retreat_back_m", 0.12)),
            grasp[1],
            grasp[2] + ret_lift,
        )
        return {
            "camera_coord_m": list(point_cam),
            "arm_coord_m": list(grasp),
            "pre_grasp": list(pre),
            "grasp": list(grasp),
            "retreat": list(retreat),
            "transform_method": "static_pitch_embedded",
            "grasp_quat_xyzw": get_grasp_quat(hand),
            "inactive_arm_pose": get_inactive_arm_pose(hand),
        }

# 运行时由相机系坐标换算
PRE_GRASP: tuple = (0.0, 0.0, 0.0)
GRASP_POS: tuple = (0.0, 0.0, 0.0)
RETREAT: tuple = (0.0, 0.0, 0.0)
ACTIVE_GRASP_QUAT = [-0.5002, -0.4998, -0.4998, 0.5002]
PALM_DOWN_QUAT = [0.0, -0.70682518, 0.0, 0.70738827]
INACTIVE_LEFT_POS = [0.45, 0.25, 0.11988012]
INACTIVE_RIGHT_POS = [0.45, -0.25, 0.11988012]

IK_SERVICE_CANDIDATES = (
    "/ik/two_arm_hand_pose_cmd_srv",
    "two_arm_hand_pose_cmd_srv",
)
IK_WAIT_TIMEOUT = 15.0


def _log(msg: str) -> None:
    print(msg, flush=True)


def _bootstrap_kuavo_python_path() -> None:
    """把 catkin devel 下的 dist-packages 加入 sys.path（未 source 时的补救）。"""
    candidates = []

    if os.environ.get("PYTHONPATH"):
        candidates.extend(p for p in os.environ["PYTHONPATH"].split(":") if p)

    home = os.path.expanduser("~")
    for base in ("/home/lab", home, "/opt"):
        if not os.path.isdir(base):
            continue
        pattern = os.path.join(base, "*", "devel", "lib", "python3", "dist-packages")
        candidates.extend(glob.glob(pattern))

    for fixed in (
        "/home/lab/kuavo-ros-control/devel/lib/python3/dist-packages",
        os.path.join(home, "kuavo-ros-control/devel/lib/python3/dist-packages"),
    ):
        candidates.append(fixed)

    seen = set()
    added = []
    for p in candidates:
        if not p or p in seen or not os.path.isdir(p):
            continue
        seen.add(p)
        if p not in sys.path:
            sys.path.insert(0, p)
            added.append(p)

    if added:
        _log("[环境] 已添加 Python 路径:")
        for p in added:
            _log(f"       {p}")


def _check_ros_packages() -> None:
    """确认 kuavo_sdk / motion_capture_ik 可导入。"""
    _bootstrap_kuavo_python_path()
    missing = []
    for mod in ("kuavo_sdk", "motion_capture_ik"):
        try:
            __import__(mod)
            _log(f"[环境] {mod} OK")
        except ImportError:
            missing.append(mod)

    if not missing:
        return

    _log("")
    _log("[错误] 缺少 Python 包: " + ", ".join(missing))
    _log("请先 source Kuavo catkin 工作空间，再运行本脚本。示例：")
    _log("  source /opt/ros/noetic/setup.bash")
    _log("  source /home/lab/kuavo-ros-control/devel/setup.bash")
    _log("  python3 scripts/grasp_from_offline_vision.py --hand right")
    _log("")
    _log("或（推荐）:")
    _log("  bash scripts/run_grasp.sh --hand right")
    _log("")
    _log("若工作空间不在默认路径，可指定：")
    _log("  export KUAVO_WS_SETUP=/你的路径/kuavo-ros-control/devel/setup.bash")
    _log("  bash scripts/run_grasp.sh --hand right")
    raise SystemExit(1)


def _rad_to_deg_14(q_rad) -> list:
    return [math.degrees(float(x)) for x in q_rad[:14]]


def _call_with_retry(fn, label: str, retries: int = 3, pause: float = 1.0):
    """ROS 服务偶发 TransportTerminated 时重试。"""
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
    """
    双臂 IK：抓取侧仅改 pos_xyz + 水平 quat；非抓取侧用待机 pos + 掌心朝下。
    关节整体角度由位置目标决定，水平夹爪四元数不参与待机侧。
    """
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

    def _do_ik():
        return ik_proxy(req)

    try:
        resp = _call_with_retry(_do_ik, "IK", retries=2, pause=1.5)
    except Exception as e:
        _log(f"[IK] 服务通信失败 pos={pos}: {e}")
        _log("[IK] 请查看 IK 节点日志: rosnode list | grep ik")
        return None

    if not resp.success:
        _log(f"[IK] 求解失败 pos={pos}（目标可能超出工作空间）")
        return None
    q = list(resp.q_arm)
    _log(f"[IK] 成功 joints={len(q)} time_cost={getattr(resp, 'time_cost', '?')}ms")
    return q


def _set_arm_mode_external() -> bool:
    """切换外部控制；失败不抛异常，由调用方决定是否继续。"""
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
            _log(f"[手臂] mode 服务返回失败: {res.message}")
            return False
        _log("[手臂] 外部控制 mode=2 OK")
        return True
    except Exception as e:
        _log(f"[手臂] Python 服务调用失败: {e}")
        _log("[手臂] 尝试 rosservice call 备用 ...")
        try:
            subprocess.run(
                ["rosservice", "call", "/arm_traj_change_mode", "control_mode: 2"],
                check=True,
                timeout=15,
                capture_output=True,
                text=True,
            )
            _log("[手臂] rosservice 切换 mode=2 OK")
            return True
        except Exception as e2:
            _log(f"[手臂] rosservice 也失败: {e2}")
            return False


def _publish_arm_timed(pub, q_rad, duration: float) -> None:
    import rospy
    from kuavo_sdk.msg import armTargetPoses

    msg = armTargetPoses()
    msg.times = [float(duration)]
    msg.values = _rad_to_deg_14(q_rad)
    pub.publish(msg)
    _log(f"[手臂] kuavo_arm_target_poses {duration}s, deg[:3]={msg.values[:3]}")
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
    _log(f"[手臂] /kuavo_arm_traj 已发布, 等待 {duration}s")
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


def _claw_cmd(hand: str, position: int, velocity: int = 50, effort: float = 1.5) -> bool:
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
        _log(f"[夹爪] 通信失败: {e}")
        return False

    if not res.success:
        _log(f"[夹爪] 失败: {getattr(res, 'message', res)}")
        return False
    _log(f"[夹爪] {claw} pos={position}")
    return True


def _load_camera_point_from_json(path: Path) -> tuple:
    data = json.loads(path.read_text(encoding="utf-8"))
    cc = data.get("camera_coord_m")
    if cc and len(cc) >= 3:
        return (float(cc[0]), float(cc[1]), float(cc[2]))
    raise ValueError(f"{path} 缺少 camera_coord_m")


def _apply_grasp_coordinates(
    camera_point: tuple,
    config_path: str,
    use_tf: bool,
    hand: str,
) -> None:
    global PRE_GRASP, GRASP_POS, RETREAT
    global ACTIVE_GRASP_QUAT, INACTIVE_LEFT_POS, INACTIVE_RIGHT_POS

    cfg = load_wheeled_camera_config(config_path if config_path else None)
    poses = resolve_grasp_poses_arm_base(
        camera_point, cfg, use_tf=use_tf, hand=hand
    )

    PRE_GRASP = tuple(poses["pre_grasp"])
    GRASP_POS = tuple(poses["grasp"])
    RETREAT = tuple(poses["retreat"])
    ACTIVE_GRASP_QUAT = list(poses["grasp_quat_xyzw"])

    inact = poses["inactive_arm_pose"]
    if hand == "right":
        INACTIVE_LEFT_POS = list(inact)
    else:
        INACTIVE_RIGHT_POS = list(inact)

    _log(f"[坐标] 相机 optical (m): {camera_point}")
    _log(f"[坐标] 变换: {poses['transform_method']}")
    _log(f"[坐标] 水平抓取点 (m): {GRASP_POS}")
    _log(f"[坐标] 预抓取(后方就位, -X): {PRE_GRASP}")
    _log(f"[坐标] 后撤 (m): {RETREAT}")
    _log(f"[姿态] 抓取侧水平 quat_xyzw: {ACTIVE_GRASP_QUAT}")
    _log("[坐标] 微调: vision_lim/config/wheeled_head_camera.yaml "
         "(forward_extra_m / right_y_bias / quat)")


def run_grasp(hand: str, grasp_width: int, grasp_effort: float,
              skip_gripper: bool, skip_arm_mode: bool,
              camera_point: tuple, config_path: str, use_tf: bool) -> bool:
    import rospy

    rospy.init_node("grasp_from_offline_vision", anonymous=True)
    _log("[0] ROS 节点已启动")

    _apply_grasp_coordinates(camera_point, config_path, use_tf, hand)

    if not skip_arm_mode:
        if not _set_arm_mode_external():
            _log(
                "[手臂] 未能切换外部控制，继续执行。"
                "若手臂不动请改用: --skip-arm-mode 或先手动切到外部控制"
            )
        rospy.sleep(0.5)
    else:
        _log("[手臂] 跳过 mode 设置 (--skip-arm-mode)")

    use_target_poses = False
    arm_pub = None
    try:
        from kuavo_sdk.msg import armTargetPoses

        arm_pub = rospy.Publisher(
            "/kuavo_arm_target_poses", armTargetPoses, queue_size=10, latch=True
        )
        if _wait_for_connections(arm_pub, timeout=3.0):
            use_target_poses = True
            _log("[手臂] 使用 /kuavo_arm_target_poses")
        else:
            arm_pub = None
            _log("[手臂] 无订阅者，改用 /kuavo_arm_traj")
    except Exception as e:
        _log(f"[手臂] armTargetPoses 不可用 ({e})，改用 /kuavo_arm_traj")

    _log("[2] 连接 IK 服务 ...")
    ik_proxy = _resolve_ik_proxy()

    if not skip_gripper:
        try:
            _claw_cmd(hand, 0)
            rospy.sleep(0.8)
        except Exception as e:
            _log(f"[夹爪] 张开跳过: {e}")
    else:
        _log("[夹爪] --skip-gripper")

    if not _move_to(ik_proxy, arm_pub, PRE_GRASP, hand, 2.0, "后方就位", use_target_poses):
        return False
    if not _move_to(ik_proxy, arm_pub, GRASP_POS, hand, 3.0, "前伸水平抓取", use_target_poses):
        return False

    if not skip_gripper:
        try:
            _claw_cmd(hand, grasp_width, effort=grasp_effort)
            rospy.sleep(1.5)
        except Exception as e:
            _log(f"[夹爪] 闭合失败: {e}")
            return False

    if not _move_to(ik_proxy, arm_pub, RETREAT, hand, 2.0, "后撤抬起", use_target_poses):
        return False

    _log("[完成] 抓取流程结束")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="固定坐标抓取")
    parser.add_argument("--hand", choices=("left", "right"), default="right")
    parser.add_argument("--grasp-width", type=int, default=90)
    parser.add_argument("--grasp-effort", type=float, default=1.5)
    parser.add_argument("--skip-gripper", action="store_true")
    parser.add_argument("--skip-arm-mode", action="store_true",
                        help="不调用 arm_traj_change_mode（已在外部模式时用）")
    parser.add_argument(
        "--grasp-json",
        default=str(_SCRIPT_DIR.parent / "instance" / "grasp_target.json"),
        help="含 camera_coord_m 的 JSON（默认仓库根目录 grasp_target.json）",
    )
    parser.add_argument(
        "--camera-coord",
        nargs=3,
        type=float,
        metavar=("X", "Y", "Z"),
        help="覆盖 JSON，直接指定相机 optical 坐标 (m)",
    )
    parser.add_argument(
        "--camera-config",
        default="",
        help="wheeled_head_camera.yaml 路径，默认 vision_lim/config/...",
    )
    parser.add_argument(
        "--use-tf",
        action="store_true",
        help="用 /tf 将相机点变换到 base_link（需 ros_interface 发布 tf）",
    )
    parser.add_argument(
        "--dry-coords",
        action="store_true",
        help="只打印坐标变换结果，不控制机械臂",
    )
    args = parser.parse_args()

    if args.camera_coord:
        camera_point = tuple(args.camera_coord)
    else:
        jpath = Path(args.grasp_json)
        if not jpath.is_file():
            camera_point = DEFAULT_CAMERA_POINT
            _log(f"[坐标] 未找到 {jpath}，使用默认相机点")
        else:
            camera_point = _load_camera_point_from_json(jpath)

    if args.dry_coords:
        cfg_path = args.camera_config or None
        if args.use_tf:
            _check_ros_packages()
            import rospy
            rospy.init_node("grasp_coord_preview", anonymous=True)
        _apply_grasp_coordinates(
            camera_point, cfg_path or "", args.use_tf, args.hand
        )
        return 0

    _check_ros_packages()
    _log(f"hand={args.hand} 相机点={camera_point} use_tf={args.use_tf}")

    try:
        ok = run_grasp(
            hand=args.hand,
            grasp_width=args.grasp_width,
            grasp_effort=args.grasp_effort,
            skip_gripper=args.skip_gripper,
            skip_arm_mode=args.skip_arm_mode,
            camera_point=camera_point,
            config_path=args.camera_config,
            use_tf=args.use_tf,
        )
        return 0 if ok else 1
    except Exception:
        _log("[错误] 执行异常:")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
