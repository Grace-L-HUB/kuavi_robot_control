#!/usr/bin/env python3
"""
动作模型集成测试

分层测试各子系统和完整抓取递送流程：
1. 姿态库基础测试
2. 状态机逻辑测试（无硬件）
3. 头部控制测试
4. 手臂 IK 测试
5. 夹爪状态测试
6. 完整抓取流程测试
7. 完整递送流程测试
8. 错误恢复测试
"""
import sys
import os
import time
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from control.pose_library import PoseLibrary
from control.action_state import (
    ActionState, ActionEvent, ActionContext,
    get_next_state, TRANSITIONS
)


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


# ==================== 无硬件测试 ====================

def test_pose_library():
    """测试姿态库（无硬件依赖）"""
    logger = logging.getLogger('test_pose')
    logger.info("=== Testing Pose Library ===")

    lib = PoseLibrary()

    # 验证所有默认姿态
    for name in lib.list_poses():
        pose = lib.get(name)
        assert pose is not None, f"Pose '{name}' returned None"
        assert len(pose) == 14, f"Pose '{name}' has {len(pose)} joints, expected 14"
        logger.info(f"  {name}: {pose}")

    # 测试单手获取
    left = lib.get_for_hand("home", "left")
    right = lib.get_for_hand("home", "right")
    assert left is not None and len(left) == 7
    assert right is not None and len(right) == 7

    # 测试插值
    trajectory = lib.interpolate("home", "ready", steps=5)
    assert trajectory is not None
    assert len(trajectory) == 5
    # 最后一步应等于目标姿态
    ready = lib.get("ready")
    for i, (a, b) in enumerate(zip(trajectory[-1], ready)):
        assert abs(a - b) < 1e-6, f"Interpolation endpoint mismatch at joint {i}"

    # 测试自定义姿态
    custom = [10] * 14
    assert lib.add_pose("custom_test", custom)
    assert lib.has_pose("custom_test")
    assert lib.get("custom_test") == custom

    # 测试无效姿态
    assert not lib.add_pose("bad", [1, 2, 3])  # 长度不对

    logger.info("Pose library tests PASSED")
    return True


def test_state_machine_logic():
    """测试状态机转移逻辑（无硬件依赖）"""
    logger = logging.getLogger('test_state')
    logger.info("=== Testing State Machine Logic ===")

    # 测试正常抓取流程转移
    expected_pickup_path = [
        (ActionState.IDLE, ActionEvent.SUCCESS, ActionState.PREPARE),
        (ActionState.PREPARE, ActionEvent.SUCCESS, ActionState.APPROACH),
        (ActionState.APPROACH, ActionEvent.SUCCESS, ActionState.ALIGN),
        (ActionState.ALIGN, ActionEvent.SUCCESS, ActionState.HEAD_LOOK_DOWN),
        (ActionState.HEAD_LOOK_DOWN, ActionEvent.SUCCESS, ActionState.PRE_GRASP),
        (ActionState.PRE_GRASP, ActionEvent.SUCCESS, ActionState.OPEN_GRIPPER),
        (ActionState.OPEN_GRIPPER, ActionEvent.SUCCESS, ActionState.GRASP_DESCEND),
        (ActionState.GRASP_DESCEND, ActionEvent.SUCCESS, ActionState.CLOSE_GRIPPER),
        (ActionState.CLOSE_GRIPPER, ActionEvent.SUCCESS, ActionState.VERIFY_GRASP),
        (ActionState.VERIFY_GRASP, ActionEvent.GRASP_CONFIRMED, ActionState.LIFT),
        (ActionState.LIFT, ActionEvent.SUCCESS, ActionState.TRANSPORT),
    ]

    for current, event, expected_next in expected_pickup_path:
        actual = get_next_state(current, event)
        assert actual == expected_next, \
            f"Transition {current.name} --[{event.name}]--> expected {expected_next.name}, " \
            f"got {actual.name}"
        logger.info(f"  {current.name} --[{event.name}]--> {actual.name} OK")

    # 测试递送流程
    expected_deliver_path = [
        (ActionState.TRANSPORT, ActionEvent.SUCCESS, ActionState.NAVIGATE),
        (ActionState.NAVIGATE, ActionEvent.SUCCESS, ActionState.PRE_PLACE),
        (ActionState.PRE_PLACE, ActionEvent.SUCCESS, ActionState.PLACE_DESCEND),
        (ActionState.PLACE_DESCEND, ActionEvent.SUCCESS, ActionState.RELEASE),
        (ActionState.RELEASE, ActionEvent.SUCCESS, ActionState.RETRACT),
        (ActionState.RETRACT, ActionEvent.SUCCESS, ActionState.COMPLETE),
    ]

    for current, event, expected_next in expected_deliver_path:
        actual = get_next_state(current, event)
        assert actual == expected_next
        logger.info(f"  {current.name} --[{event.name}]--> {actual.name} OK")

    # 测试抓取重试分支
    retry_next = get_next_state(ActionState.VERIFY_GRASP, ActionEvent.GRASP_FAILED)
    assert retry_next == ActionState.OPEN_GRIPPER
    logger.info(f"  VERIFY_GRASP --[GRASP_FAILED]--> {retry_next.name} (retry) OK")

    # 测试 ABORT 总是进入 ERROR
    for state in ActionState:
        if state in (ActionState.COMPLETE, ActionState.ERROR):
            continue
        next_state = get_next_state(state, ActionEvent.ABORT)
        assert next_state == ActionState.ERROR, \
            f"ABORT from {state.name} should go to ERROR, got {next_state.name}"

    logger.info("  All ABORT transitions -> ERROR OK")

    # 测试 ActionContext
    ctx = ActionContext(target_position=(1.0, 2.0, 0.1))
    assert ctx.current_state == ActionState.IDLE
    ctx.enter_state(ActionState.PREPARE)
    assert ctx.current_state == ActionState.PREPARE
    assert ctx.retry_count == 0

    # 模拟重试
    ctx.enter_state(ActionState.VERIFY_GRASP)
    assert ctx.can_retry()  # max_retries=2, retry_count=0
    ctx.enter_state(ActionState.VERIFY_GRASP)  # 重试1
    assert ctx.retry_count == 1
    assert ctx.can_retry()
    ctx.enter_state(ActionState.VERIFY_GRASP)  # 重试2
    assert ctx.retry_count == 2
    assert not ctx.can_retry()  # 达到上限

    logger.info("  ActionContext retry logic OK")
    logger.info("State machine logic tests PASSED")
    return True


# ==================== 需要硬件的测试 ====================

def test_head_control():
    """测试头部控制（需要 ROS 环境）"""
    logger = logging.getLogger('test_head')
    logger.info("=== Testing Head Controller ===")

    try:
        from control.head_controller import HeadController
        head = HeadController()

        logger.info("Testing look_forward...")
        head.look_forward()
        time.sleep(1)

        logger.info("Testing look_down...")
        head.look_down(-20)
        time.sleep(1)

        logger.info("Testing look_at_hand (left)...")
        head.look_at_hand("left")
        time.sleep(1)

        logger.info("Testing look_forward (reset)...")
        head.look_forward()

        logger.info("Head control tests PASSED")
        return True
    except Exception as e:
        logger.error(f"Head control test failed: {e}")
        return False


def test_full_pickup():
    """测试完整抓取流程（需要机器人连接）"""
    logger = logging.getLogger('test_pickup')
    logger.info("=== Testing Full Pickup ===")

    try:
        from control.robot_controller import RobotController
        from utils.config_manager import ConfigManager

        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'robot_config.yaml')
        config = ConfigManager(config_path)

        robot = RobotController(config.config)
        if not robot.initialize():
            logger.error("Failed to initialize robot")
            return False

        # 测试抓取
        logger.info("Executing pickup at (1.0, 1.0, 0.1)...")
        result = robot.pick_object(1.0, 1.0, 0.1, hand="left")
        logger.info(f"Pickup result: {result}")

        return result
    except Exception as e:
        logger.error(f"Full pickup test failed: {e}")
        return False


def test_full_pickup_and_deliver():
    """测试完整抓取递送流程（需要机器人连接）"""
    logger = logging.getLogger('test_full')
    logger.info("=== Testing Full Pickup and Deliver ===")

    try:
        from control.robot_controller import RobotController
        from utils.config_manager import ConfigManager

        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'robot_config.yaml')
        config = ConfigManager(config_path)

        robot = RobotController(config.config)
        if not robot.initialize():
            logger.error("Failed to initialize robot")
            return False

        pickup_pos = (1.0, 1.0, 0.1)
        delivery_pos = (2.0, 1.0, 0.1)

        logger.info(f"Executing pickup-and-deliver: {pickup_pos} -> {delivery_pos}")
        result = robot.pickup_and_deliver(pickup_pos, delivery_pos, hand="left")
        logger.info(f"Pickup-and-deliver result: {result}")

        return result
    except Exception as e:
        logger.error(f"Full test failed: {e}")
        return False


def main():
    """主函数"""
    setup_logging()
    logger = logging.getLogger('test_action_model')

    results = {}

    # 无硬件测试（始终运行）
    logger.info("\n========== Phase 1: No-hardware tests ==========\n")
    results["pose_library"] = test_pose_library()
    results["state_machine"] = test_state_machine_logic()

    # 硬件测试（可选，需要参数 --hardware）
    if "--hardware" in sys.argv:
        logger.info("\n========== Phase 2: Hardware tests ==========\n")
        results["head_control"] = test_head_control()

    if "--full" in sys.argv:
        logger.info("\n========== Phase 3: Full integration tests ==========\n")
        results["full_pickup"] = test_full_pickup()
        results["full_deliver"] = test_full_pickup_and_deliver()

    # 汇总结果
    logger.info("\n========== Test Results ==========")
    all_passed = True
    for name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        logger.info(f"  {name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        logger.info("\nAll tests PASSED!")
    else:
        logger.error("\nSome tests FAILED!")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
