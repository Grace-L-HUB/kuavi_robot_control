#!/usr/bin/env python3
"""
测试机器人连接
验证 WebSocket 和 ROS 连接是否正常
"""
import sys
import os
import logging

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from communication.robot_api import WooshApi
from control.gripper_controller import GripperController
from control.arm_controller import ArmController
from utils.config_manager import ConfigManager

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_websocket_connection(config):
    """测试WebSocket连接"""
    logger = logging.getLogger('test_websocket')
    logger.info("Testing WebSocket connection...")
    
    client = None
    try:
        websocket_config = config.get("robot.websocket", {}) or {}
        ip = websocket_config.get("ip", "169.254.128.2")
        port = websocket_config.get("port", 8080)
        timeout = websocket_config.get("timeout", 8)
        url = f"ws://{ip}:{port}/"
        logger.info(f"WebSocket URL: {url}")
        
        client = WooshApi(url)
        if not client.connect():
            logger.error("WebSocket connection failed (check IP/port and robot power)")
            return False

        logger.info("WebSocket connection successful")

        raw = client.request("woosh.robot.RobotState", timeout=timeout)
        if raw and raw.get("ok"):
            state = raw.get("body", {})
            logger.info(f"Robot state: {state}")
        else:
            logger.error(f"RobotState RPC failed: {raw}")
            return False

        raw = client.request("woosh.robot.Battery", timeout=timeout)
        if raw and raw.get("ok"):
            logger.info(f"Battery info: {raw.get('body', {})}")
        else:
            logger.error(f"Battery RPC failed: {raw}")
            return False

        return True
    except Exception as e:
        logger.error(f"Error testing WebSocket connection: {e}")
        return False
    finally:
        if client:
            client.close()

def test_ros_connection(config):
    """测试ROS连接"""
    logger = logging.getLogger('test_ros')
    logger.info("Testing ROS connection...")

    if not config.apply_ros_environment():
        logger.error("ROS master_uri not configured")
        return False

    cfg = config.data
    ros_ok = False

    try:
        gripper = GripperController(cfg)
        if gripper._gripper_service is not None:
            logger.info("Gripper controller: service ready")
            ros_ok = True
        else:
            logger.error("Gripper controller: service not available (check ROS on robot)")
    except Exception as e:
        logger.error(f"Gripper controller failed: {e}")

    try:
        arm = ArmController(cfg)
        if arm._arm_publisher is not None:
            logger.info("Arm controller: publisher ready")
            ros_ok = True
        else:
            logger.error("Arm controller: publisher not available")
    except Exception as e:
        logger.error(f"Arm controller failed: {e}")

    if not ros_ok:
        logger.error(
            "ROS test failed. On the board run: "
            "source /opt/ros/noetic/setup.bash && "
            "rostopic list | head"
        )
    return ros_ok

def main():
    """主函数"""
    setup_logging()
    logger = logging.getLogger('test_connection')
    
    try:
        # 加载配置
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'robot_config.yaml')
        config = ConfigManager(config_path)
        
        logger.info("Starting connection tests...")
        
        # 测试WebSocket连接
        ws_success = test_websocket_connection(config)
        
        # 测试ROS连接
        ros_success = test_ros_connection(config)
        
        if ws_success and ros_success:
            logger.info("All connection tests passed!")
            return 0
        else:
            logger.warning("Some connection tests failed")
            return 1
    except Exception as e:
        logger.error(f"Error in connection tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
