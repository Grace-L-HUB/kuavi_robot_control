"""控制器集成测试"""
import pytest
from tests.mocks.mock_chassis import MockChassis
from tests.mocks.mock_arm import MockArmController
from tests.mocks.mock_gripper import MockGripperController
from tests.mocks.mock_head import MockHeadController


class TestMockChassis:
    """测试模拟底盘"""
    
    def test_robot_go_to(self):
        """测试导航"""
        chassis = MockChassis()
        result = chassis.robot_go_to(1.0, 2.0, 0.5)
        
        assert result is True
        pose = chassis.robot_pose_speed()
        assert pose["x"] == 1.0
        assert pose["y"] == 2.0
        assert pose["theta"] == 0.5
    
    def test_step_control(self):
        """测试步进控制"""
        chassis = MockChassis()
        chassis.robot_go_to(0.0, 0.0, 0.0)
        
        result = chassis.robot_step_control("ahead", 0.3, 0.05)
        assert result is True
        
        pose = chassis.robot_pose_speed()
        assert pose["x"] == 0.3
    
    def test_stop(self):
        """测试停止"""
        chassis = MockChassis()
        chassis.robot_stop()
        
        assert chassis.robot_state() == "stopped"


class TestMockArmController:
    """测试模拟机械臂"""
    
    def test_set_joint_angles(self):
        """测试设置关节角度"""
        arm = MockArmController()
        angles = [1.0] * 14
        
        result = arm.set_joint_angles(angles)
        assert result is True
        assert arm.get_joint_angles() == angles
    
    def test_set_joint_angles_invalid(self):
        """测试无效关节角度"""
        arm = MockArmController()
        
        # 长度错误
        result = arm.set_joint_angles([1.0] * 10)
        assert result is False
    
    def test_home(self):
        """测试回到初始位置"""
        arm = MockArmController()
        arm.set_joint_angles([10.0] * 14)
        
        result = arm.home()
        assert result is True
        assert arm.get_joint_angles() == [0.0] * 14
    
    def test_control_mode(self):
        """测试控制模式切换"""
        arm = MockArmController()
        
        assert arm.get_control_mode() == 0
        
        result = arm.set_control_mode(2)
        assert result is True
        assert arm.get_control_mode() == 2
    
    def test_go_to_cartesian(self):
        """测试笛卡尔空间控制"""
        arm = MockArmController()
        
        result = arm.go_to_cartesian(0.5, 0.0, 0.1, hand="left")
        assert result is True
        
        # 检查关节角度是否被设置
        angles = arm.get_joint_angles()
        assert angles != [0.0] * 14


class TestMockGripperController:
    """测试模拟夹爪"""
    
    def test_open_close(self):
        """测试开合控制"""
        gripper = MockGripperController()
        
        # 张开
        result = gripper.open()
        assert result is True
        assert gripper.get_state()["left"]["position"] == 0
        
        # 闭合
        result = gripper.close(position=90)
        assert result is True
        assert gripper.get_state()["left"]["position"] == 90
    
    def test_close_hand(self):
        """测试单臂闭合"""
        gripper = MockGripperController()
        
        result = gripper.close_hand("left", position=80)
        assert result is True
        assert gripper.get_state()["left"]["position"] == 80
        assert gripper.get_state()["right"]["position"] == 0  # 右侧不变
    
    def test_is_grasping(self):
        """测试抓取状态检测"""
        gripper = MockGripperController()
        
        # 未抓取
        assert gripper.is_grasping("left") is False
        
        # 闭合后应该是抓取状态
        gripper.close()
        assert gripper.is_grasping("left") is True
    
    def test_wait_for_grasp(self):
        """测试等待抓取确认"""
        gripper = MockGripperController()
        
        result = gripper.wait_for_grasp("left")
        assert result is True


class TestMockHeadController:
    """测试模拟头部"""
    
    def test_look_forward(self):
        """测试正视前方"""
        head = MockHeadController()
        
        result = head.look_forward()
        assert result is True
        assert head.get_gaze() == (0.0, 0.0)
    
    def test_look_down(self):
        """测试低头"""
        head = MockHeadController()
        
        result = head.look_down(-20.0)
        assert result is True
        yaw, pitch = head.get_gaze()
        assert yaw == 0.0
        assert pitch == -20.0
    
    def test_look_at_hand(self):
        """测试注视手部"""
        head = MockHeadController()
        
        result = head.look_at_hand("left")
        assert result is True
        yaw, pitch = head.get_gaze()
        assert yaw == 15.0
        assert pitch == -15.0
        
        result = head.look_at_hand("right")
        assert result is True
        yaw, pitch = head.get_gaze()
        assert yaw == -15.0
        assert pitch == -15.0
    
    def test_angle_limits(self):
        """测试角度限制"""
        head = MockHeadController()
        
        # 超出范围的角度应该被限制
        result = head.set_gaze(50.0, 30.0)
        assert result is True
        yaw, pitch = head.get_gaze()
        assert yaw == 30.0  # 最大偏航角
        assert pitch == 25.0  # 最大俯仰角
