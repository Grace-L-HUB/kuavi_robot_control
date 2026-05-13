"""模拟底盘控制器"""

class MockChassis:
    """模拟底盘控制接口"""
    
    def __init__(self):
        self._position = (0.0, 0.0, 0.0)  # (x, y, theta)
        self._state = "idle"
    
    def robot_go_to(self, x: float, y: float, theta: float = 0) -> bool:
        """模拟导航到指定位置"""
        self._position = (x, y, theta)
        self._state = "moving"
        # 模拟导航成功
        self._state = "arrived"
        return True
    
    def robot_step_control(self, direction: str, distance: float, speed: float) -> bool:
        """模拟步进控制"""
        if direction == "ahead":
            self._position = (self._position[0] + distance, self._position[1], self._position[2])
        return True
    
    def robot_stop(self):
        """模拟停止底盘"""
        self._state = "stopped"
    
    def robot_state(self) -> str:
        """获取底盘状态"""
        return self._state
    
    def robot_pose_speed(self) -> dict:
        """获取位置和速度"""
        return {
            "x": self._position[0],
            "y": self._position[1],
            "theta": self._position[2],
            "speed": 0.0
        }
    
    def robot_battery(self) -> dict:
        """获取电池状态"""
        return {"level": 100, "voltage": 24.0}
