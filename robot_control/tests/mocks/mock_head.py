"""模拟头部控制器"""

class MockHeadController:
    """模拟头部控制接口"""
    
    def __init__(self, config=None):
        self._yaw = 0.0
        self._pitch = 0.0
    
    def set_gaze(self, yaw: float, pitch: float, wait: bool = True) -> bool:
        """设置头部姿态"""
        # 限制角度范围
        self._yaw = max(-30.0, min(30.0, yaw))
        self._pitch = max(-25.0, min(25.0, pitch))
        return True
    
    def look_forward(self) -> bool:
        """正视前方"""
        return self.set_gaze(0.0, 0.0)
    
    def look_down(self, pitch: float = -20.0) -> bool:
        """低头"""
        return self.set_gaze(0.0, pitch)
    
    def look_at_hand(self, hand: str = "left") -> bool:
        """注视手部"""
        if hand == "left":
            return self.set_gaze(15.0, -15.0)
        elif hand == "right":
            return self.set_gaze(-15.0, -15.0)
        return False
    
    def look_at_target(self, yaw: float, pitch: float) -> bool:
        """注视目标"""
        return self.set_gaze(yaw, pitch)
    
    def get_gaze(self) -> tuple:
        """获取当前姿态"""
        return (self._yaw, self._pitch)
