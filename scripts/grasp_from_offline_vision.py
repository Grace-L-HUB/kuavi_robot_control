#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
固定坐标抓取（单文件，对齐 Kuavo 开源 SDK / interface.md 调用方式）。

可单独拷到下位机任意目录运行，仅需 ROS 环境 + kuavo_sdk + motion_capture_ik。

用法:
  source /opt/ros/noetic/setup.bash
  source ~/kuavo-ros-control/devel/setup.bash
  python3 grasp_from_offline_vision.py --hand right

  # 若夹爪服务未启用
  python3 grasp_from_offline_vision.py --hand right --skip-gripper
"""

from __future__ import annotations

import argparse
import math
import sys
import traceback

# ---------- 已计算目标坐标（米，基座系；与 grasp_target.json 一致）----------
TARGET_X = -0.044330238372661326
TARGET_Y = 0.08261372036424994
TARGET_Z = 0.64

PRE_GRASP = (TARGET_X, TARGET_Y, 0.79)
GRASP_POS = (TARGET_X, TARGET_Y, 0.69)
RETREAT = (TARGET_X, TARGET_Y, 0.79)

# 掌心朝下（interface.md 示例四元数 [qx,qy,qz,qw]）
GRASP_QUAT = [0.0, -0.70682518, 0.0, 0.70738827]

IK_SERVICE_CANDIDATES = (
    "/ik/two_arm_hand_pose_cmd_srv",
    "two_arm_hand_pose_cmd_srv",
)


def _log(msg: str) -> None:
    print(msg, flush=True)


def _rad_to_deg_14(q_rad) -> list:
    return [math.degrees(float(x)) for x in q_rad[:14]]


def _wait_for_connections(pub, timeout: float = 5.0) -> bool:
    import rospy

    t0 = rospy.Time.now().to_sec()
    while pub.get_num_connections() == 0:
        if rospy.Time.now().to_sec() - t0 > timeout:
            return False
        rospy.sleep(0.05)
    return True


def _resolve_ik_proxy():
    """与官方示例一致，兼容带/不带 /ik 前缀的服务名。"""
    import rospy
    from motion_capture_ik.srv import twoArmHandPoseCmdSrv

    last_err = None
    for name in IK_SERVICE_CANDIDATES:
        try:
            _log(f"[IK] 等待服务: {name}")
            rospy.wait_for_service(name, timeout=5.0)
            proxy = rospy.ServiceProxy(name, twoArmHandPoseCmdSrv)
            _log(f"[IK] 已连接: {name}")
            return proxy
        except Exception as e:
            last_err = e
            _log(f"[IK] 不可用 {name}: {e}")
    raise RuntimeError(f"未找到 IK 服务: {last_err}")


def _solve_ik(ik_proxy, pos, quat, hand: str):
    import numpy as np
    from motion_capture_ik.msg import twoArmHandPoseCmd

    req = twoArmHandPoseCmd()
    req.use_custom_ik_param = False
    req.joint_angles_as_q0 = False

    zero3 = np.zeros(3)
    if hand == "left":
        req.hand_poses.left_pose.pos_xyz = np.array(pos, dtype=float)
        req.hand_poses.left_pose.quat_xyzw = quat
        req.hand_poses.left_pose.elbow_pos_xyz = zero3
    else:
        req.hand_poses.right_pose.pos_xyz = np.array(pos, dtype=float)
        req.hand_poses.right_pose.quat_xyzw = quat
        req.hand_poses.right_pose.elbow_pos_xyz = zero3

    resp = ik_proxy(req)
    if not resp.success:
        _log(f"[IK] 求解失败 pos={pos}")
        return None
    q = list(resp.q_arm)
    _log(f"[IK] 成功 joints={len(q)} time_cost={getattr(resp, 'time_cost', '?')}ms")
    return q


def _set_arm_mode_external() -> None:
    import rospy
    from kuavo_sdk.srv import changeArmCtrlMode, changeArmCtrlModeRequest

    rospy.wait_for_service("/arm_traj_change_mode", timeout=5.0)
    cli = rospy.ServiceProxy("/arm_traj_change_mode", changeArmCtrlMode)
    req = changeArmCtrlModeRequest()
    req.control_mode = 2
    res = cli(req)
    if not res.result:
        raise RuntimeError(f"arm_traj_change_mode 失败: {res.message}")
    _log("[手臂] 外部控制模式 mode=2 已设置")


def _publish_arm_timed(pub, q_rad, duration: float) -> None:
    import rospy
    from kuavo_sdk.msg import armTargetPoses

    msg = armTargetPoses()
    msg.times = [float(duration)]
    msg.values = _rad_to_deg_14(q_rad)
    pub.publish(msg)
    _log(f"[手臂] 已发布 kuavo_arm_target_poses duration={duration}s values(deg)前3={msg.values[:3]}...")
    rospy.sleep(duration + 0.5)


def _publish_arm_traj_fallback(q_rad) -> None:
    """armTargetPoses 不可用时，用 /kuavo_arm_traj（度）。"""
    import rospy
    from sensor_msgs.msg import JointState

    pub = rospy.Publisher("/kuavo_arm_traj", JointState, queue_size=10, latch=True)
    _wait_for_connections(pub, timeout=3.0)
    msg = JointState()
    msg.name = [f"arm_joint_{i}" for i in range(1, 15)]
    msg.header.stamp = rospy.Time.now()
    msg.position = _rad_to_deg_14(q_rad)
    pub.publish(msg)
    _log("[手臂] 已发布 /kuavo_arm_traj (fallback)")
    rospy.sleep(2.5)


def _move_to(ik_proxy, arm_pub, pos, hand: str, duration: float, label: str,
             use_target_poses: bool) -> bool:
    import rospy

    _log(f"[运动] {label} -> ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")
    q = _solve_ik(ik_proxy, pos, GRASP_QUAT, hand)
    if q is None:
        return False
    if use_target_poses and arm_pub is not None:
        _publish_arm_timed(arm_pub, q, duration)
    else:
        _publish_arm_traj_fallback(q)
    return True


def _claw_cmd(hand: str, position: int, velocity: int = 50, effort: float = 1.5) -> bool:
    import rospy
    from kuavo_sdk.srv import controlLejuClaw, controlLejuClawRequest

    rospy.wait_for_service("/control_robot_leju_claw", timeout=5.0)
    cli = rospy.ServiceProxy("/control_robot_leju_claw", controlLejuClaw)
    req = controlLejuClawRequest()
    claw = f"{hand}_claw"
    req.data.name = [claw]
    req.data.position = [float(position)]
    req.data.velocity = [float(velocity)]
    req.data.effort = [float(effort)]
    res = cli(req)
    if not res.success:
        _log(f"[夹爪] 失败: {getattr(res, 'message', res)}")
        return False
    _log(f"[夹爪] {claw} position={position}")
    return True


def run_grasp(hand: str, grasp_width: int, grasp_effort: float, skip_gripper: bool) -> bool:
    import rospy
    from kuavo_sdk.msg import armTargetPoses

    rospy.init_node("grasp_from_offline_vision", anonymous=True)
    _log("[0] ROS 节点已启动")

    _set_arm_mode_external()
    rospy.sleep(0.3)

    use_target_poses = True
    arm_pub = None
    try:
        arm_pub = rospy.Publisher(
            "/kuavo_arm_target_poses", armTargetPoses, queue_size=10, latch=True
        )
        if not _wait_for_connections(arm_pub, timeout=5.0):
            _log("[警告] /kuavo_arm_target_poses 无订阅者，将尝试 /kuavo_arm_traj")
            use_target_poses = False
            arm_pub = None
        else:
            _log("[手臂] /kuavo_arm_target_poses 已有订阅者")
    except Exception as e:
        _log(f"[警告] armTargetPoses 不可用: {e}")
        use_target_poses = False
        arm_pub = None

    ik_proxy = _resolve_ik_proxy()

    if not skip_gripper:
        try:
            _claw_cmd(hand, 0)
            rospy.sleep(0.8)
        except Exception as e:
            _log(f"[夹爪] 张开跳过: {e}")
    else:
        _log("[夹爪] 已跳过 (--skip-gripper)")

    if not _move_to(ik_proxy, arm_pub, PRE_GRASP, hand, 2.0, "预抓取", use_target_poses):
        return False
    if not _move_to(ik_proxy, arm_pub, GRASP_POS, hand, 3.0, "下降抓取", use_target_poses):
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
    parser = argparse.ArgumentParser(description="固定坐标抓取（单文件 ROS 直调）")
    parser.add_argument("--hand", choices=("left", "right"), default="right")
    parser.add_argument("--grasp-width", type=int, default=90)
    parser.add_argument("--grasp-effort", type=float, default=1.5)
    parser.add_argument("--skip-gripper", action="store_true")
    args = parser.parse_args()

    _log(
        f"目标: pre={PRE_GRASP} grasp={GRASP_POS} hand={args.hand} "
        f"skip_gripper={args.skip_gripper}"
    )

    try:
        ok = run_grasp(
            hand=args.hand,
            grasp_width=args.grasp_width,
            grasp_effort=args.grasp_effort,
            skip_gripper=args.skip_gripper,
        )
        return 0 if ok else 1
    except Exception:
        _log("[错误] 执行异常:")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
