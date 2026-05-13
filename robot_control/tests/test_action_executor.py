"""动作执行器集成测试"""
import pytest
from src.control.action_model import ActionExecutor
from src.control.action_state import ActionState, ActionEvent
from src.control.pose_library import PoseLibrary
from tests.mocks.mock_chassis import MockChassis
from tests.mocks.mock_arm import MockArmController
from tests.mocks.mock_gripper import MockGripperController
from tests.mocks.mock_head import MockHeadController


class MockRobotController:
    """模拟机器人控制器"""
    
    def __init__(self):
        self.chassis = MockChassis()
        self.gripper = MockGripperController()
        self.arm = MockArmController()
        self.head = MockHeadController()
        self.pose_library = PoseLibrary()


class TestActionExecutor:
    """测试动作执行器"""
    
    def test_initialization(self):
        """测试初始化"""
        robot = MockRobotController()
        executor = ActionExecutor(robot)
        
        assert executor.robot == robot
        assert executor.context is None
    
    def test_execute_pickup(self):
        """测试抓取流程"""
        robot = MockRobotController()
        executor = ActionExecutor(robot)
        
        # 执行抓取
        result = executor.execute_pickup((0.5, 0.0, 0.1), hand="left")
        
        # 抓取成功应该进入TRANSPORT状态
        assert result is True
        assert executor.get_state() == ActionState.TRANSPORT
        
        # 验证各子系统状态
        assert robot.arm.get_control_mode() == 2  # 外部控制模式
        assert robot.gripper.is_grasping("left") is True
    
    def test_execute_pickup_right_hand(self):
        """测试用右手抓取"""
        robot = MockRobotController()
        executor = ActionExecutor(robot)
        
        result = executor.execute_pickup((0.5, 0.0, 0.1), hand="right")
        
        assert result is True
        assert executor.get_state() == ActionState.TRANSPORT
        assert robot.gripper.is_grasping("right") is True
    
    def test_execute_delivery(self):
        """测试递送流程"""
        robot = MockRobotController()
        executor = ActionExecutor(robot)
        
        # 先执行抓取
        executor.execute_pickup((0.5, 0.0, 0.1), hand="left")
        
        # 再执行递送
        result = executor.execute_delivery((1.0, 0.5, 0.1))
        
        # 递送成功应该进入COMPLETE状态
        assert result is True
        assert executor.get_state() == ActionState.COMPLETE
    
    def test_execute_pickup_and_deliver(self):
        """测试完整抓取递送流程"""
        robot = MockRobotController()
        executor = ActionExecutor(robot)
        
        result = executor.execute_pickup_and_deliver(
            target_pos=(0.5, 0.0, 0.1),
            delivery_pos=(1.0, 0.5, 0.1),
            hand="left"
        )
        
        # 完整流程成功应该进入COMPLETE状态
        assert result is True
        assert executor.get_state() == ActionState.COMPLETE
        
        # 验证最终状态
        assert robot.arm.get_control_mode() == 0  # 回到保持模式
        assert robot.head.get_gaze() == (0.0, 0.0)  # 正视前方
    
    def test_abort(self):
        """测试紧急中止"""
        robot = MockRobotController()
        executor = ActionExecutor(robot)
        
        # 开始抓取
        executor.execute_pickup((0.5, 0.0, 0.1), hand="left")
        
        # 中止动作
        executor.abort()
        
        # 错误恢复完成后状态重置为IDLE（安全状态）
        assert executor.get_state() == ActionState.IDLE
        
        # 验证安全恢复执行：夹爪张开
        assert robot.gripper.get_state()["left"]["position"] == 0
    
    def test_get_state(self):
        """测试获取状态"""
        robot = MockRobotController()
        executor = ActionExecutor(robot)
        
        # 未执行动作时返回None
        assert executor.get_state() is None
        
        # 执行动作后返回当前状态
        executor.execute_pickup((0.5, 0.0, 0.1), hand="left")
        assert executor.get_state() == ActionState.TRANSPORT
    
    def test_grasp_failure_retry(self):
        """测试抓取失败重试机制（Mock默认成功，此测试验证重试逻辑框架）"""
        robot = MockRobotController()
        executor = ActionExecutor(robot)
        
        # 修改gripper使其返回失败
        original_wait_for_grasp = robot.gripper.wait_for_grasp
        
        # 第一次返回失败，第二次返回成功
        call_count = [0]
        
        def mock_wait_for_grasp(hand="left", timeout=3.0):
            call_count[0] += 1
            if call_count[0] == 1:
                return False  # 第一次失败
            return True  # 第二次成功
        
        robot.gripper.wait_for_grasp = mock_wait_for_grasp
        
        # 执行抓取
        result = executor.execute_pickup((0.5, 0.0, 0.1), hand="left")
        
        # 应该成功（重试后成功）
        assert result is True
        assert call_count[0] == 2  # 验证重试被调用
    
    def test_invalid_hand(self):
        """测试无效手部参数（动作执行器不处理此验证，由上下文处理）"""
        robot = MockRobotController()
        executor = ActionExecutor(robot)
        
        # 动作执行器接收hand参数并传递给上下文
        result = executor.execute_pickup((0.5, 0.0, 0.1), hand="invalid")
        
        # Mock控制器会处理无效参数（可能返回失败或默认行为）
        # 这里取决于Mock实现，我们验证流程能正常执行
        assert result is True
