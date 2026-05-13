#!/usr/bin/env python3
"""
测试完整抓取递送流程（使用状态机驱动的动作模型）

流程：
1. 初始化机器人控制器
2. 查询机器人状态
3. 执行抓取（状态机自动完成 19 步）
4. 移动到递送位置
5. 执行放置
6. 查询最终状态
"""
import sys
import os
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from control.robot_controller import RobotController
from utils.config_manager import ConfigManager


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_pickup_place():
    """测试抓取和放置流程"""
    logger = logging.getLogger('test_pickup')
    logger.info("Testing pickup and place flow (state machine driven)...")

    try:
        # 加载配置
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'robot_config.yaml')
        config = ConfigManager(config_path)

        # 初始化机器人控制器
        robot = RobotController(config.config)
        if not robot.initialize():
            logger.error("Failed to initialize robot controller")
            return False

        # 获取机器人状态
        logger.info("Getting robot status...")
        status = robot.get_status()
        if status:
            logger.info(f"Robot status: {status}")

        # 定义抓取和放置位置（根据实际环境设置）
        pickup_pos = (1.0, 1.0, 0.1)
        delivery_pos = (2.0, 1.0, 0.1)

        # 执行完整的抓取-递送流程
        logger.info(f"Executing pickup-and-deliver: {pickup_pos} -> {delivery_pos}")
        result = robot.pickup_and_deliver(
            pickup_pos=pickup_pos,
            delivery_pos=delivery_pos,
            hand="left",
            grasp_width=90,
            grasp_effort=1.5
        )

        if result:
            logger.info("Pickup and deliver completed successfully!")
        else:
            logger.error("Pickup and deliver failed!")

        # 获取最终状态
        final_status = robot.get_status()
        if final_status:
            logger.info(f"Final status: {final_status}")

        return result
    except Exception as e:
        logger.error(f"Error in pickup and place test: {e}")
        return False


def main():
    """主函数"""
    setup_logging()
    logger = logging.getLogger('test_pickup')

    try:
        logger.info("Starting pickup and place tests...")
        result = test_pickup_place()

        if result:
            logger.info("All tests completed successfully!")
        else:
            logger.error("Tests failed!")

        return 0 if result else 1
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
