#!/usr/bin/env python3
"""
测试底盘移动功能
- 前进/后退
- 左转/右转
- 导航到指定点
"""
import sys
import os
import time
import logging

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from communication.robot_api import WooshApi
from utils.config_manager import ConfigManager

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_move_forward_backward(client):
    """测试前进和后退"""
    logger = logging.getLogger('test_move')
    logger.info("Testing forward and backward movement...")
    
    try:
        # 前进
        logger.info("Moving forward...")
        if client.robot_twist(0.1, 0):
            time.sleep(2)
            # 停止
            client.robot_stop()
            time.sleep(1)
        else:
            logger.error("Failed to move forward")
            return False
        
        # 后退
        logger.info("Moving backward...")
        if client.robot_twist(-0.1, 0):
            time.sleep(2)
            # 停止
            client.robot_stop()
            time.sleep(1)
        else:
            logger.error("Failed to move backward")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error testing forward/backward movement: {e}")
        return False

def test_turn_left_right(client):
    """测试左转和右转"""
    logger = logging.getLogger('test_move')
    logger.info("Testing left and right turns...")
    
    try:
        # 左转
        logger.info("Turning left...")
        if client.robot_twist(0, 0.5):
            time.sleep(2)
            # 停止
            client.robot_stop()
            time.sleep(1)
        else:
            logger.error("Failed to turn left")
            return False
        
        # 右转
        logger.info("Turning right...")
        if client.robot_twist(0, -0.5):
            time.sleep(2)
            # 停止
            client.robot_stop()
            time.sleep(1)
        else:
            logger.error("Failed to turn right")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error testing left/right turns: {e}")
        return False

def test_go_to_position(client):
    """测试导航到指定位置"""
    logger = logging.getLogger('test_move')
    logger.info("Testing navigation to position...")
    
    try:
        # 导航到指定位置
        # 注意：这里需要根据实际地图设置合适的坐标
        target_x = 1.0
        target_y = 1.0
        target_theta = 0.0
        
        logger.info(f"Navigating to position ({target_x}, {target_y}, {target_theta})...")
        if client.robot_go_to(target_x, target_y, target_theta):
            logger.info("Navigation started successfully")
            # 等待导航完成
            time.sleep(5)
        else:
            logger.error("Failed to start navigation")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error testing navigation: {e}")
        return False

def test_step_control(client):
    """测试单步控制"""
    logger = logging.getLogger('test_move')
    logger.info("Testing step control...")
    
    try:
        # 测试前进一步
        logger.info("Stepping forward...")
        if client.robot_step_control("ahead", 0.5, 0.1):
            time.sleep(1)
        else:
            logger.error("Failed to step forward")
            return False
        
        # 测试后退一步
        logger.info("Stepping backward...")
        if client.robot_step_control("back", 0.5, 0.1):
            time.sleep(1)
        else:
            logger.error("Failed to step backward")
            return False
        
        # 测试左转
        logger.info("Stepping left...")
        if client.robot_step_control("left", 0.5, 0.1):
            time.sleep(1)
        else:
            logger.error("Failed to step left")
            return False
        
        # 测试右转
        logger.info("Stepping right...")
        if client.robot_step_control("right", 0.5, 0.1):
            time.sleep(1)
        else:
            logger.error("Failed to step right")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error testing step control: {e}")
        return False

def main():
    """主函数"""
    setup_logging()
    logger = logging.getLogger('test_move')
    
    try:
        # 加载配置
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'robot_config.yaml')
        config = ConfigManager(config_path)
        
        # 初始化WebSocket客户端
        websocket_config = config.get("robot.websocket", {})
        ip = websocket_config.get("ip", "192.168.1.100")
        port = websocket_config.get("port", 8080)
        url = f"ws://{ip}:{port}/"
        
        client = WooshApi(url)
        if not client.connect():
            logger.error("Failed to connect to robot")
            return 1
        
        logger.info("Starting movement tests...")
        
        # 测试前进后退
        test_move_forward_backward(client)
        
        # 测试左右转
        test_turn_left_right(client)
        
        # 测试单步控制
        test_step_control(client)
        
        # 测试导航到指定位置
        test_go_to_position(client)
        
        # 停止机器人
        client.robot_stop()
        
        # 关闭连接
        client.close()
        
        logger.info("All movement tests completed!")
        return 0
    except Exception as e:
        logger.error(f"Error in movement tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
