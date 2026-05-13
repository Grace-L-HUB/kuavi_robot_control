#!/usr/bin/env python3
"""
测试机械臂控制
- 关节角度控制
- 位置控制
- 夹爪开合
"""
import sys
import os
import time
import logging

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from control.gripper_controller import GripperController
from control.arm_controller import ArmController

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_gripper_operations():
    """测试夹爪操作"""
    logger = logging.getLogger('test_arm')
    logger.info("Testing gripper operations...")
    
    try:
        gripper = GripperController()
        
        # 测试张开夹爪
        logger.info("Opening gripper...")
        if gripper.open():
            logger.info("Gripper opened successfully")
        else:
            logger.error("Failed to open gripper")
        
        time.sleep(2)
        
        # 测试闭合夹爪
        logger.info("Closing gripper...")
        if gripper.close():
            logger.info("Gripper closed successfully")
        else:
            logger.error("Failed to close gripper")
        
        time.sleep(2)
        
        # 测试获取夹爪状态
        logger.info("Getting gripper state...")
        state = gripper.get_state()
        if state:
            logger.info(f"Gripper state: {state}")
        else:
            logger.error("Failed to get gripper state")
        
        return True
    except Exception as e:
        logger.error(f"Error testing gripper operations: {e}")
        return False

def test_arm_joint_control():
    """测试机械臂关节控制"""
    logger = logging.getLogger('test_arm')
    logger.info("Testing arm joint control...")
    
    try:
        arm = ArmController()
        
        # 测试设置关节角度
        logger.info("Setting joint angles...")
        # 测试角度，实际使用时需要根据机械臂型号调整
        joint_angles = [-30, 60, 0, -30, 0, -30, 30, 0, 0, 0, 0, 0, 0, 0]
        if arm.set_joint_angles(joint_angles):
            logger.info("Joint angles set successfully")
        else:
            logger.error("Failed to set joint angles")
        
        time.sleep(3)
        
        # 测试回到初始位置
        logger.info("Going home...")
        if arm.home():
            logger.info("Arm returned to home position")
        else:
            logger.error("Failed to go home")
        
        time.sleep(3)
        
        return True
    except Exception as e:
        logger.error(f"Error testing arm joint control: {e}")
        return False

def test_arm_position_control():
    """测试机械臂位置控制"""
    logger = logging.getLogger('test_arm')
    logger.info("Testing arm position control...")
    
    try:
        arm = ArmController()
        
        # 测试移动到指定位置
        logger.info("Moving to position...")
        # 测试位置，实际使用时需要根据机械臂工作空间调整
        x, y, z = 0.5, 0.0, 0.5
        if arm.go_to_position(x, y, z):
            logger.info(f"Arm moved to position ({x}, {y}, {z})")
        else:
            logger.error("Failed to move to position")
        
        time.sleep(3)
        
        # 测试回到初始位置
        logger.info("Going home...")
        if arm.home():
            logger.info("Arm returned to home position")
        else:
            logger.error("Failed to go home")
        
        time.sleep(3)
        
        return True
    except Exception as e:
        logger.error(f"Error testing arm position control: {e}")
        return False

def test_arm_control_mode():
    """测试机械臂控制模式"""
    logger = logging.getLogger('test_arm')
    logger.info("Testing arm control mode...")
    
    try:
        arm = ArmController()
        
        # 测试设置控制模式
        logger.info("Setting control mode to 0 (hold position)...")
        if arm.set_control_mode(0):
            logger.info("Control mode set successfully")
        else:
            logger.error("Failed to set control mode")
        
        time.sleep(2)
        
        return True
    except Exception as e:
        logger.error(f"Error testing arm control mode: {e}")
        return False

def main():
    """主函数"""
    setup_logging()
    logger = logging.getLogger('test_arm')
    
    try:
        logger.info("Starting arm tests...")
        
        # 测试夹爪操作
        test_gripper_operations()
        
        # 测试机械臂关节控制
        test_arm_joint_control()
        
        # 测试机械臂位置控制
        test_arm_position_control()
        
        # 测试机械臂控制模式
        test_arm_control_mode()
        
        logger.info("All arm tests completed!")
        return 0
    except Exception as e:
        logger.error(f"Error in arm tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
