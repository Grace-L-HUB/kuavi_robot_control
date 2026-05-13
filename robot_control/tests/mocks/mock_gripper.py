"""模拟夹爪控制器"""

class MockGripperController:
    """模拟夹爪控制接口"""
    
    # 状态常量
    CLAW_STATE_ERROR = -1
    CLAW_STATE_UNKNOWN = 0
    CLAW_STATE_MOVING = 1
    CLAW_STATE_REACHED = 2
    CLAW_STATE_GRABBED = 3
    
    def __init__(self, config=None):
        self._state = {
            "left": {"state": self.CLAW_STATE_UNKNOWN, "position": 0, "velocity": 0, "effort": 0},
            "right": {"state": self.CLAW_STATE_UNKNOWN, "position": 0, "velocity": 0, "effort": 0},
        }
        self._default_position = 90
        self._default_velocity = 50
        self._default_effort = 1.5
    
    def close(self, position: int = None, velocity: int = None, effort: float = None) -> bool:
        """闭合双侧夹爪"""
        pos = position if position is not None else self._default_position
        self._state["left"]["position"] = pos
        self._state["right"]["position"] = pos
        self._state["left"]["state"] = self.CLAW_STATE_GRABBED
        self._state["right"]["state"] = self.CLAW_STATE_GRABBED
        return True
    
    def close_hand(self, hand: str = "left", position: int = None, 
                   velocity: int = None, effort: float = None) -> bool:
        """闭合指定侧夹爪"""
        if hand not in ("left", "right"):
            return False
        pos = position if position is not None else self._default_position
        self._state[hand]["position"] = pos
        self._state[hand]["state"] = self.CLAW_STATE_GRABBED
        return True
    
    def open(self) -> bool:
        """张开双侧夹爪"""
        self._state["left"]["position"] = 0
        self._state["right"]["position"] = 0
        self._state["left"]["state"] = self.CLAW_STATE_REACHED
        self._state["right"]["state"] = self.CLAW_STATE_REACHED
        return True
    
    def open_hand(self, hand: str = "left") -> bool:
        """张开指定侧夹爪"""
        if hand not in ("left", "right"):
            return False
        self._state[hand]["position"] = 0
        self._state[hand]["state"] = self.CLAW_STATE_REACHED
        return True
    
    def get_state(self) -> dict:
        """获取夹爪状态"""
        return {
            "left": dict(self._state["left"]),
            "right": dict(self._state["right"]),
        }
    
    def get_claw_state_code(self, hand: str = "left") -> int:
        """获取夹爪状态码"""
        return self._state.get(hand, {}).get("state", self.CLAW_STATE_UNKNOWN)
    
    def is_grasping(self, hand: str = "left") -> bool:
        """检查是否正在抓取"""
        return self.get_claw_state_code(hand) == self.CLAW_STATE_GRABBED
    
    def wait_for_grasp(self, hand: str = "left", timeout: float = 3.0) -> bool:
        """等待抓取确认"""
        return True  # 模拟抓取成功
    
    def wait_for_position(self, hand: str = "left", timeout: float = 3.0) -> bool:
        """等待到达目标位置"""
        return True
