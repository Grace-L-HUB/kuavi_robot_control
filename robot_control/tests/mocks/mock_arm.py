"""模拟机械臂控制器"""

from typing import List, Optional

class MockArmController:
    """模拟机械臂控制接口"""
    
    def __init__(self, config=None):
        self._joint_angles = [0.0] * 14
        self._control_mode = 0  # 0=保持姿势, 1=自动摆手, 2=外部控制
    
    def set_joint_angles(self, angles: List[float]) -> bool:
        """设置关节角度"""
        if len(angles) != 14:
            return False
        self._joint_angles = list(angles)
        return True
    
    def set_target_poses_timed(self, angles: List[float], duration: float = None) -> bool:
        """设置带时间的目标姿态"""
        return self.set_joint_angles(angles)
    
    def home(self) -> bool:
        """回到初始位置"""
        self._joint_angles = [0.0] * 14
        return True
    
    def set_control_mode(self, mode: int) -> bool:
        """设置控制模式"""
        self._control_mode = mode
        return True
    
    def go_to_cartesian(self, x: float, y: float, z: float, 
                        quat: List[float] = None, 
                        hand: str = "left", 
                        duration: float = None) -> bool:
        """模拟笛卡尔空间控制（总是成功）"""
        # 简化处理：直接设置关节角度为一个预设值
        if hand == "left":
            self._joint_angles[:7] = [-45.0, 15.0, 0.0, -60.0, 0.0, -30.0, 0.0]
        else:
            self._joint_angles[7:] = [-45.0, -15.0, 0.0, -60.0, 0.0, -30.0, 0.0]
        return True
    
    def get_control_mode(self) -> int:
        """获取当前控制模式"""
        return self._control_mode
    
    def get_joint_angles(self) -> List[float]:
        """获取当前关节角度"""
        return list(self._joint_angles)
