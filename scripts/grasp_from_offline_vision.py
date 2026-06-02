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
import math
import os
import sys
import traceback

# ---------- 已计算目标坐标（米，基座系）----------
TARGET_X = -0.044330238372661326
TARGET_Y = 0.08261372036424994
TARGET_Z = 0.64

PRE_GRASP = (TARGET_X, TARGET_Y, 0.79)
GRASP_POS = (TARGET_X, TARGET_Y, 0.69)
RETREAT = (TARGET_X, TARGET_Y, 0.79)

GRASP_QUAT = [0.0, -0.70682518, 0.0, 0.70738827]

# IK 必须同时给双手有效位姿（interface.md 示例）；未设置的一侧四元数为 0 会报错
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


def _solve_ik(ik_proxy, pos, quat, hand: str):
    """
    双臂 IK：必须同时填写 left_pose 与 right_pose 的有效四元数。
    仅设置一只手时另一侧默认为 [0,0,0,0] 会导致 IK 节点报错。
    """
    import numpy as np
    from motion_capture_ik.msg import twoArmHandPoseCmd

    req = twoArmHandPoseCmd()
    req.use_custom_ik_param = False
    req.joint_angles_as_q0 = False
    zero3 = np.zeros(3)

    left_pos = list(INACTIVE_LEFT_POS)
    right_pos = list(INACTIVE_RIGHT_POS)
    if hand == "left":
        left_pos = list(pos)
    else:
        right_pos = list(pos)

    req.hand_poses.left_pose.pos_xyz = np.array(left_pos, dtype=float)
    req.hand_poses.left_pose.quat_xyzw = quat
    req.hand_poses.left_pose.elbow_pos_xyz = zero3

    req.hand_poses.right_pose.pos_xyz = np.array(right_pos, dtype=float)
    req.hand_poses.right_pose.quat_xyzw = quat
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
    q = _solve_ik(ik_proxy, pos, GRASP_QUAT, hand)
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


def run_grasp(hand: str, grasp_width: int, grasp_effort: float,
              skip_gripper: bool, skip_arm_mode: bool) -> bool:
    import rospy

    rospy.init_node("grasp_from_offline_vision", anonymous=True)
    _log("[0] ROS 节点已启动")

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

    if not _move_to(ik_proxy, arm_pub, PRE_GRASP, hand, 2.0, "预抓取", use_target_poses):
        return False
    if not _move_to(ik_proxy, arm_pub, GRASP_POS, hand, 3.0, "下降", use_target_poses):
        return False

    if not skip_gripper:
        try:
            _claw_cmd(hand, grasp_width, effort=grasp_effort)
            rospy.sleep(1.5)
        except Exception as e:
            _log(f"[夹爪] 闭合失败: {e}")
            return False

    if not _move_to(ik_proxy, arm_pub, RETREAT, hand, 2.0, "抬起", use_target_poses):
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
    args = parser.parse_args()

    _log(f"目标 pre={PRE_GRASP} grasp={GRASP_POS} hand={args.hand}")

    _check_ros_packages()

    try:
        ok = run_grasp(
            hand=args.hand,
            grasp_width=args.grasp_width,
            grasp_effort=args.grasp_effort,
            skip_gripper=args.skip_gripper,
            skip_arm_mode=args.skip_arm_mode,
        )
        return 0 if ok else 1
    except Exception:
        _log("[错误] 执行异常:")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
