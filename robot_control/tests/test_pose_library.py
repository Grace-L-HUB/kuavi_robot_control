"""姿态库单元测试"""
import pytest
from src.control.pose_library import PoseLibrary


class TestPoseLibrary:
    """测试姿态库功能"""
    
    def test_initialization(self):
        """测试姿态库初始化"""
        pl = PoseLibrary()
        poses = pl.list_poses()
        
        # 验证默认姿态存在
        assert "home" in poses
        assert "ready" in poses
        assert "pre_grasp_front" in poses
        assert "grasp_low" in poses
        assert "transport" in poses
        assert "deliver_front" in poses
        assert "present" in poses
    
    def test_get_pose(self):
        """测试获取姿态"""
        pl = PoseLibrary()
        
        # 获取home姿态（全0）
        home_pose = pl.get("home")
        assert len(home_pose) == 14
        assert all(v == 0.0 for v in home_pose)
        
        # 获取ready姿态
        ready_pose = pl.get("ready")
        assert len(ready_pose) == 14
        assert ready_pose != [0.0] * 14  # 非全0
    
    def test_get_for_hand(self):
        """测试获取单臂姿态"""
        pl = PoseLibrary()
        
        # 获取左臂姿态
        left_pose = pl.get_for_hand("ready", "left")
        assert len(left_pose) == 7
        
        # 获取右臂姿态
        right_pose = pl.get_for_hand("ready", "right")
        assert len(right_pose) == 7
        
        # 测试无效参数
        assert pl.get_for_hand("ready", "invalid") is None
    
    def test_interpolate(self):
        """测试姿态插值"""
        pl = PoseLibrary()
        
        # 测试home到ready的插值
        trajectory = pl.interpolate("home", "ready", steps=5)
        assert len(trajectory) == 5
        
        # 检查每个插值点
        for waypoint in trajectory:
            assert len(waypoint) == 14
        
        # 最后一个点应该接近ready姿态
        last_point = trajectory[-1]
        ready_pose = pl.get("ready")
        for i in range(14):
            assert abs(last_point[i] - ready_pose[i]) < 1.0
    
    def test_add_pose(self):
        """测试添加自定义姿态"""
        pl = PoseLibrary()
        custom_pose = [10.0] * 14
        
        # 添加新姿态
        result = pl.add_pose("custom_test", custom_pose)
        assert result is True
        assert "custom_test" in pl.list_poses()
        
        # 验证姿态内容
        retrieved = pl.get("custom_test")
        assert retrieved == custom_pose
    
    def test_add_invalid_pose(self):
        """测试添加无效姿态"""
        pl = PoseLibrary()
        
        # 无效长度
        assert not pl.add_pose("invalid1", [1.0] * 10)
        
        # 无效数据类型
        assert not pl.add_pose("invalid2", ["a"] * 14)
    
    def test_has_pose(self):
        """测试检查姿态是否存在"""
        pl = PoseLibrary()
        assert pl.has_pose("home") is True
        assert pl.has_pose("nonexistent") is False
    
    def test_config_override(self):
        """测试通过配置覆盖默认姿态"""
        config = {
            "poses": {
                "home": [1.0] * 14,
                "custom_config": [2.0] * 14
            }
        }
        pl = PoseLibrary(config)
        
        # 验证覆盖生效
        home_pose = pl.get("home")
        assert all(v == 1.0 for v in home_pose)
        
        # 验证自定义姿态加载
        assert "custom_config" in pl.list_poses()
