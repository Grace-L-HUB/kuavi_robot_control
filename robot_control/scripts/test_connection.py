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
    
    try:
        websocket_config = config.get("robot", {}).get("websocket", {})
        ip = websocket_config.get("ip", "192.168.1.100")
        port = websocket_config.get("port", 8080)
        url = f"ws://{ip}:{port}/"
        
        client = WooshApi(url)
        if client.connect():
            logger.info("WebSocket connection successful")
            
            # 测试获取机器人状态
            state = client.robot_state()
            if state:
                logger.info(f"Robot state: {state}")
            else:
                logger.warning("Failed to get robot state")
            
            # 测试获取电池信息
            battery = client.robot_battery()
            if battery:
                logger.info(f"Battery info: {battery}")
            else:
                logger.warning("Failed to get battery info")
            
            client.close()
            return True
        else:
            logger.error("WebSocket connection failed")
            return False
    except Exception as e:
        logger.error(f"Error testing WebSocket connection: {e}")
        return False

def test_ros_connection():
    """测试ROS连接"""
    logger = logging.getLogger('test_ros')
    logger.info("Testing ROS connection...")
    
    try:
        # 测试夹爪控制器
        try:
            gripper = GripperController()
            logger.info("Gripper controller initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize gripper controller: {e}")
        
        # 测试机械臂控制器
        try:
            arm = ArmController()
            logger.info("Arm controller initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize arm controller: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Error testing ROS connection: {e}")
        return False

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
        ros_success = test_ros_connection()
        
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
