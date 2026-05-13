"""动作状态机单元测试"""
import pytest
from src.control.action_state import (
    ActionState, ActionEvent, ActionContext, get_next_state, STATE_TIMEOUTS
)


class TestActionState:
    """测试动作状态枚举"""
    
    def test_state_enum(self):
        """验证状态枚举值"""
        assert ActionState.IDLE.value > 0
        assert ActionState.COMPLETE.value > 0
        assert ActionState.ERROR.value > 0
    
    def test_event_enum(self):
        """验证事件枚举值"""
        assert ActionEvent.SUCCESS.value > 0
        assert ActionEvent.FAILURE.value > 0
        assert ActionEvent.TIMEOUT.value > 0


class TestStateTransitions:
    """测试状态转移"""
    
    def test_normal_flow(self):
        """测试正常状态流转"""
        # IDLE -> PREPARE
        assert get_next_state(ActionState.IDLE, ActionEvent.SUCCESS) == ActionState.PREPARE
        
        # PREPARE -> APPROACH
        assert get_next_state(ActionState.PREPARE, ActionEvent.SUCCESS) == ActionState.APPROACH
        
        # APPROACH -> ALIGN
        assert get_next_state(ActionState.APPROACH, ActionEvent.SUCCESS) == ActionState.ALIGN
        
        # ALIGN -> HEAD_LOOK_DOWN
        assert get_next_state(ActionState.ALIGN, ActionEvent.SUCCESS) == ActionState.HEAD_LOOK_DOWN
        
        # HEAD_LOOK_DOWN -> PRE_GRASP
        assert get_next_state(ActionState.HEAD_LOOK_DOWN, ActionEvent.SUCCESS) == ActionState.PRE_GRASP
        
        # PRE_GRASP -> OPEN_GRIPPER
        assert get_next_state(ActionState.PRE_GRASP, ActionEvent.SUCCESS) == ActionState.OPEN_GRIPPER
        
        # OPEN_GRIPPER -> GRASP_DESCEND
        assert get_next_state(ActionState.OPEN_GRIPPER, ActionEvent.SUCCESS) == ActionState.GRASP_DESCEND
        
        # GRASP_DESCEND -> CLOSE_GRIPPER
        assert get_next_state(ActionState.GRASP_DESCEND, ActionEvent.SUCCESS) == ActionState.CLOSE_GRIPPER
        
        # CLOSE_GRIPPER -> VERIFY_GRASP
        assert get_next_state(ActionState.CLOSE_GRIPPER, ActionEvent.SUCCESS) == ActionState.VERIFY_GRASP
    
    def test_grasp_verify_branch(self):
        """测试抓取验证分支"""
        # 抓取成功
        assert get_next_state(ActionState.VERIFY_GRASP, ActionEvent.GRASP_CONFIRMED) == ActionState.LIFT
        
        # 抓取失败（重试）
        assert get_next_state(ActionState.VERIFY_GRASP, ActionEvent.GRASP_FAILED) == ActionState.OPEN_GRIPPER
    
    def test_timeout_and_abort(self):
        """测试超时和中止"""
        # APPROACH超时
        assert get_next_state(ActionState.APPROACH, ActionEvent.TIMEOUT) == ActionState.ERROR
        
        # NAVIGATE超时
        assert get_next_state(ActionState.NAVIGATE, ActionEvent.TIMEOUT) == ActionState.ERROR
        
        # 任意状态中止
        assert get_next_state(ActionState.PREPARE, ActionEvent.ABORT) == ActionState.ERROR
        assert get_next_state(ActionState.GRASP_DESCEND, ActionEvent.ABORT) == ActionState.ERROR
    
    def test_failure_transition(self):
        """测试失败转移"""
        # 未定义的失败转移进入ERROR
        assert get_next_state(ActionState.PRE_GRASP, ActionEvent.FAILURE) == ActionState.ERROR


class TestActionContext:
    """测试动作上下文"""
    
    def test_initialization(self):
        """测试上下文初始化"""
        ctx = ActionContext(
            target_position=(1.0, 2.0, 0.1),
            grasp_hand="right",
            grasp_width=80,
            grasp_effort=1.8
        )
        
        assert ctx.target_position == (1.0, 2.0, 0.1)
        assert ctx.grasp_hand == "right"
        assert ctx.grasp_width == 80
        assert ctx.grasp_effort == 1.8
        assert ctx.current_state == ActionState.IDLE
    
    def test_enter_state(self):
        """测试进入状态"""
        ctx = ActionContext()
        
        # 首次进入状态
        ctx.enter_state(ActionState.PREPARE)
        assert ctx.current_state == ActionState.PREPARE
        assert ctx.retry_count == 0
        
        # 重试同一状态
        ctx.enter_state(ActionState.PREPARE)
        assert ctx.retry_count == 1
        assert ctx.total_retries == 1
        
        # 进入新状态
        ctx.enter_state(ActionState.APPROACH)
        assert ctx.retry_count == 0
    
    def test_can_retry(self):
        """测试重试检查"""
        ctx = ActionContext()
        ctx.current_state = ActionState.VERIFY_GRASP
        
        # 默认可以重试
        assert ctx.can_retry() is True
        
        # 模拟多次重试
        ctx.retry_count = 2
        assert ctx.can_retry() is False  # MAX_RETRIES = 2
    
    def test_timeout_check(self):
        """测试超时检查"""
        import time
        ctx = ActionContext()
        ctx.current_state = ActionState.PREPARE
        
        # 刚进入状态，未超时
        assert ctx.state_timed_out() is False
        
        # 模拟超时（通过修改state_entry_time）
        ctx.state_entry_time = time.time() - 10.0
        assert ctx.state_timed_out() is True  # PREPARE超时5秒
