#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按已标定/计算好的目标坐标，直接控制机械臂与夹爪完成抓取（无视觉、无 YOLO）。

坐标来源：grasp_target.json（由上位机图像 + camera_info 离线算出）。

在机器人 ROS 环境运行（项目根目录）:
  python scripts/grasp_from_offline_vision.py
  python scripts/grasp_from_offline_vision.py --hand right
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import math
import sys
from pathlib import Path
from typing import List, Tuple

# 项目根目录（脚本须在 仓库/scripts/ 下）
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "robot_control" / "src"


def _load_module(relative_path: str, module_name: str):
    """按文件路径加载模块，避免 control 包 __init__ 的相对导入问题。"""
    path = SRC / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载模块: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("grasp_execute")

# ---------- 已计算好的目标坐标（米，机械臂基座系）----------
# 与 grasp_target.json 一致；若重新标定请改 JSON 或下方常量
TARGET_X = -0.044330238372661326
TARGET_Y = 0.08261372036424994
TARGET_Z = 0.64

PRE_GRASP = (TARGET_X, TARGET_Y, 0.79)   # 预抓取：目标上方
GRASP_POS = (TARGET_X, TARGET_Y, 0.69)   # 下降抓取
RETREAT = (TARGET_X, TARGET_Y, 0.79)     # 抓取后抬起

# 掌心朝下（与 robot_config / interface.md 默认一致）
GRASP_QUAT = [0.0, -0.70682518, 0.0, 0.70738827]

DEFAULT_JSON = ROOT / "grasp_target.json"


def _load_coords_from_json(path: Path) -> Tuple[Tuple[float, float, float], ...]:
    """从 grasp_target.json 读取 arm_coord 与 grasp_plan。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    arm = tuple(data["arm_coord_m"])
    plan = data["grasp_plan"]
    pre = tuple(plan["pre_grasp"])
    grasp = tuple(plan["grasp"])
    retreat = tuple(plan["retreat"])
    return arm, pre, grasp, retreat


def _rad_to_deg_14(q_rad: List[float]) -> List[float]:
    return [math.degrees(x) for x in q_rad[:14]]


def _move_hand_to(
    arm,
    gripper,
    rospy,
    pos: Tuple[float, float, float],
    hand: str,
    quat: List[float],
    duration: float,
    label: str,
) -> bool:
    logger.info("%s -> (%.3f, %.3f, %.3f)", label, pos[0], pos[1], pos[2])
    if hand == "left":
        q = arm.solve_ik(left_pos=list(pos), left_quat=quat)
    else:
        q = arm.solve_ik(right_pos=list(pos), right_quat=quat)
    if q is None:
        logger.error("%s IK 失败", label)
        return False
    arm.set_target_poses_timed(_rad_to_deg_14(q), duration=duration)
    rospy.sleep(duration + 0.5)
    return True


def run_grasp(
    hand: str,
    pre_grasp: Tuple[float, float, float],
    grasp_pos: Tuple[float, float, float],
    retreat: Tuple[float, float, float],
    grasp_width: int,
    grasp_effort: float,
    robot_config: Path,
) -> bool:
    import rospy

    ConfigManager = _load_module(
        "utils/config_manager.py", "kuavi_config_manager"
    ).ConfigManager
    ArmController = _load_module(
        "control/arm_controller.py", "kuavi_arm_controller"
    ).ArmController
    GripperController = _load_module(
        "control/gripper_controller.py", "kuavi_gripper_controller"
    ).GripperController

    if not rospy.core.is_initialized():
        rospy.init_node("grasp_from_offline_vision", anonymous=True)

    config = ConfigManager(str(robot_config)).config
    arm = ArmController(config)
    gripper = GripperController(config)

    logger.info(
        "目标抓取点 (m): x=%.3f y=%.3f z=%.3f  使用手: %s",
        grasp_pos[0],
        grasp_pos[1],
        grasp_pos[2],
        hand,
    )

    logger.info("设置手臂外部控制模式 /arm_traj_change_mode mode=2")
    arm.set_control_mode(2)
    rospy.sleep(0.5)

    logger.info("张开夹爪 /control_robot_leju_claw")
    if not gripper.open_hand(hand):
        logger.error("夹爪张开失败")
        return False
    rospy.sleep(0.8)

    if not _move_hand_to(arm, gripper, rospy, pre_grasp, hand, GRASP_QUAT, 2.0, "预抓取"):
        return False
    if not _move_hand_to(arm, gripper, rospy, grasp_pos, hand, GRASP_QUAT, 3.0, "下降抓取"):
        return False

    logger.info("闭合夹爪 position=%d effort=%.1f", grasp_width, grasp_effort)
    if not gripper.close_hand(hand, position=grasp_width, effort=grasp_effort):
        logger.error("夹爪闭合指令失败")
        return False

    if gripper.wait_for_grasp(hand=hand, timeout=3.0):
        logger.info("夹爪状态: 已抓取 (Grabbed)")
    else:
        logger.warning("未确认 Grabbed，仍执行抬起")

    if not _move_hand_to(arm, gripper, rospy, retreat, hand, GRASP_QUAT, 2.0, "抬起"):
        return False

    logger.info("抓取流程完成")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="使用固定坐标控制机械臂与夹爪抓取（无 YOLO）"
    )
    parser.add_argument("--hand", choices=("left", "right"), default="right")
    parser.add_argument("--grasp-width", type=int, default=90, help="夹爪闭合 0-100")
    parser.add_argument("--grasp-effort", type=float, default=1.5, help="夹爪电流 A")
    parser.add_argument(
        "--coords-json",
        default=str(DEFAULT_JSON),
        help="可选：从 JSON 覆盖内置坐标（默认 grasp_target.json）",
    )
    parser.add_argument(
        "--use-constants",
        action="store_true",
        help="强制使用脚本顶部常量，不读 JSON",
    )
    parser.add_argument(
        "--robot-config",
        default=str(ROOT / "robot_control" / "config" / "robot_config.yaml"),
    )
    args = parser.parse_args()

    pre_grasp, grasp_pos, retreat = PRE_GRASP, GRASP_POS, RETREAT

    json_path = Path(args.coords_json)
    if not args.use_constants and json_path.is_file():
        _, pre_grasp, grasp_pos, retreat = _load_coords_from_json(json_path)
        logger.info("坐标来自 %s", json_path)
    else:
        logger.info("坐标来自脚本内置常量")

    try:
        import rospy  # noqa: F401
    except ImportError:
        logger.error("需要 ROS 环境（rospy、kuavo_sdk、motion_capture_ik）")
        return 1

    ok = run_grasp(
        hand=args.hand,
        pre_grasp=pre_grasp,
        grasp_pos=grasp_pos,
        retreat=retreat,
        grasp_width=args.grasp_width,
        grasp_effort=args.grasp_effort,
        robot_config=Path(args.robot_config),
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
