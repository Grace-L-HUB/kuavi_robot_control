
# 华为昇腾机器人基础操作模块开发指南

## 📋 项目概述

本项目是为生成式 AI 准备的开发任务说明。请根据本文档的要求，为华为 Atlas 200I DK A2 开发板编写机器人基础操作控制代码。

### 项目背景
- **目标平台**: 华为 Atlas 200I DK A2 (Ubuntu 22.04)
- **机器人型号**: 轮臂机器人（支持 WebSocket + ROS 控制）
- **核心任务**: 实现底盘移动、机械臂控制、夹爪操作等基础功能

### 你需要完成的工作
请根据以下各模块的要求，生成完整的、可直接运行的 Python 代码。

---

## 🎯 模块一：WebSocket 通信客户端

### 任务描述
实现一个 WebSocket 客户端，用于与机器人底盘通信。

### 已知信息
- 通信协议: WebSocket
- 消息格式: JSON
- 已有基础代码: `WooshWebSocketClient.py`（见下方）

### 需要实现的功能

#### 1.1 WebSocket 连接管理
```python
class WooshWebSocketClient:
    def __init__(self, url: str, debug: bool = False):
        """初始化 WebSocket 客户端
        
        Args:
            url: WebSocket 服务器地址，如 "ws://192.168.1.100:8080/"
            debug: 是否开启调试模式
        """
        pass
    
    def connect(self):
        """建立 WebSocket 连接"""
        pass
    
    def close(self):
        """关闭连接"""
        pass
    
    def reconnect_test(self) -> bool:
        """测试连接是否正常
        
        Returns:
            bool: 连接正常返回 True
        """
        pass
```

#### 1.2 请求-响应机制
```python
def request(self, message_type: str, body: dict = None, timeout: int = 8) -> dict:
    """发送请求并等待响应
    
    Args:
        message_type: 消息类型，如 "woosh.robot.RobotState"
        body: 请求参数
        timeout: 超时时间（秒）
    
    Returns:
        dict: 响应数据，失败返回 None
    
    Note:
        - 每个请求需要生成唯一的 sn 序列号
        - 使用 threading.Event 实现超时机制
        - 响应通过 sn 号匹配对应的请求
    """
    pass
```

#### 1.3 订阅机制
```python
def add_topic_callback(self, topic: str, callback: callable):
    """添加话题订阅回调
    
    Args:
        topic: 话题名称
        callback: 回调函数，接收消息数据作为参数
    """
    pass

def submit_subscriptions(self):
    """发送订阅请求，开始接收订阅数据"""
    pass
```

### 提供的参考代码
```python
# WooshWebSocketClient.py - 基础框架
import websocket
import json
import threading
import time
import socket
import re

class WooshWebSocketClient:
    def __init__(self, url, debug=False):
        self.url = url
        self.debug = debug
        self.ws_request = None
        self.ws_subscribe = None
        self.subscriptions = {}
        self.subscription_events = {}
        self.subscription_data = {}
        
    def on_message(self, ws, message):
        """处理接收到的消息"""
        # 需要实现：根据是否有 sn 字段分发到请求响应或订阅回调
        pass
```

### 输出要求
- 文件路径: `src/communication/websocket_client.py`
- 必须包含完整的 `WooshWebSocketClient` 类
- 必须实现所有上述方法
- 需要包含异常处理和日志输出

---

## 🎯 模块二：机器人底盘控制 API

### 任务描述
基于 WebSocket 客户端，实现机器人底盘的各种控制功能。

### 需要实现的功能

#### 2.1 状态查询接口
```python
class WooshApi(WooshWebSocketClient):
    def robot_state(self) -> dict:
        """获取机器人状态
        
        Returns:
            dict: 包含机器人状态信息
        """
        pass
    
    def robot_pose_speed(self) -> dict:
        """获取机器人位置和速度
        
        Returns:
            dict: 包含 x, y, theta 和线速度、角速度
        """
        pass
    
    def robot_battery(self) -> dict:
        """获取电池信息
        
        Returns:
            dict: 包含电量百分比、电压、电流等
        """
        pass
```

#### 2.2 移动控制接口
```python
def robot_go_to(self, x: float, y: float, theta: float = 0) -> bool:
    """导航到指定位置（需要先建图）
    
    Args:
        x: 目标 X 坐标（米）
        y: 目标 Y 坐标（米）
        theta: 目标朝向角度（弧度）
    
    Returns:
        bool: 成功返回 True
    """
    pass

def robot_twist(self, linear: float, angular: float) -> bool:
    """速度控制
    
    Args:
        linear: 线速度（米/秒），正数为前进
        angular: 角速度（弧度/秒），正数为左转
    """
    pass

def robot_step_control(self, direction: str, distance: float, speed: float = 0.15) -> bool:
    """单步移动控制
    
    Args:
        direction: 方向，可选 "ahead", "back", "left", "right", "rotate"
        distance: 移动距离（米）或旋转角度（弧度）
        speed: 移动速度（米/秒），最大 0.2
    
    Returns:
        bool: 成功返回 True
    """
    pass
```

#### 2.3 任务执行接口
```python
def robot_exec_task(self, target: dict, poses: list) -> bool:
    """执行导航任务
    
    Args:
        target: 目标点 {"x": 0, "y": 0, "theta": 0}
        poses: 路径点列表 [{"x": 0, "y": 0, "theta": 0}, ...]
    
    Returns:
        bool: 成功返回 True
    """
    pass

def robot_action_order(self, order: int) -> bool:
    """控制任务执行状态
    
    Args:
        order: 1=开始, 2=暂停, 3=继续, 4=取消
    """
    pass
```

#### 2.4 辅助功能
```python
def robot_speak(self, text: str) -> bool:
    """语音播报
    
    Args:
        text: 要播报的文字内容
    """
    pass

def robot_stop(self) -> bool:
    """立即停止机器人移动"""
    pass
```

### 消息类型参考
```python
# 请求消息格式
{
    "type": "woosh.robot.RobotState",
    "sn": 1234567890
}

# 响应消息格式
{
    "type": "woosh.robot.RobotState",
    "sn": 1234567890,
    "ok": true,
    "body": {
        "state": "moving",
        "mode": "auto"
    }
}
```

### 输出要求
- 文件路径: `src/communication/robot_api.py`
- 类名: `WooshApi`
- 继承自 `WooshWebSocketClient`
- 实现上述所有接口方法

---

## 🎯 模块三：ROS 机械臂控制

### 任务描述
实现通过 ROS 话题和服务控制机械臂和夹爪。

### 已知信息
- ROS 版本: ROS1 Noetic 或 ROS2 Humble
- 机械臂关节数: 14 个（双臂）
- 夹爪: 二指平行夹爪

### 需要实现的功能

#### 3.1 夹爪控制器
```python
class GripperController:
    """机器人夹爪控制器"""
    
    def __init__(self):
        """初始化 ROS 节点和服务代理"""
        pass
    
    def close(self, position: int = 90) -> bool:
        """闭合夹爪
        
        Args:
            position: 闭合程度 0-100，90 表示闭合 90%
        
        Returns:
            bool: 成功返回 True
        """
        pass
    
    def open(self) -> bool:
        """完全张开夹爪"""
        pass
    
    def get_state(self) -> dict:
        """获取夹爪状态
        
        Returns:
            dict: 包含位置、速度、是否抓取到物体等信息
        """
        pass
```

**服务接口说明**:
- 服务名: `/control_robot_leju_claw`
- 请求类型: `controlLejuClawRequest`
- 消息格式:
```python
req = controlLejuClawRequest()
req.data.name = ['left_claw', 'right_claw']
req.data.position = [90, 90]   # 0=张开, 100=闭合
req.data.velocity = [50, 50]   # 速度 0-100
req.data.effort = [1.0, 1.0]   # 力矩 1-2A
```

#### 3.2 机械臂控制器
```python
class ArmController:
    """机械臂控制器"""
    
    def __init__(self):
        """初始化 ROS 发布者"""
        pass
    
    def set_joint_angles(self, angles: list) -> bool:
        """设置机械臂关节角度
        
        Args:
            angles: 14 个关节的角度值列表（单位：度）
        
        Returns:
            bool: 成功返回 True
        """
        pass
    
    def go_to_position(self, x: float, y: float, z: float) -> bool:
        """移动到指定空间位置（使用逆运动学）
        
        Args:
            x, y, z: 目标位置坐标（米）
        
        Returns:
            bool: 成功返回 True
        """
        pass
    
    def home(self) -> bool:
        """回到初始位置"""
        pass
    
    def set_control_mode(self, mode: int) -> bool:
        """设置控制模式
        
        Args:
            mode: 0=保持姿势, 1=自动摆手, 2=外部控制
        """
        pass
```

**话题接口说明**:
- 话题名: `/kuavo_arm_traj`
- 消息类型: `JointState`
- 消息格式:
```python
msg = JointState()
msg.name = [f"arm_joint_{i}" for i in range(1, 15)]
msg.header.stamp = rospy.Time.now()
msg.position = [-30, 60, 0, -30, 0, -30, 30, 0, 0, 0, 0, 0, 0, 0]
```

### 输出要求
- 文件路径: `src/control/gripper_controller.py`
- 文件路径: `src/control/arm_controller.py`
- 需要处理 ROS 节点初始化
- 需要包含异常处理和重试机制

---

## 🎯 模块四：机器人统一控制接口

### 任务描述
整合底盘和机械臂控制，提供统一的机器人操作接口。

### 需要实现的功能
```python
class RobotController:
    """机器人统一控制器"""
    
    def __init__(self, config: dict):
        """初始化控制器
        
        Args:
            config: 配置字典，包含 IP、端口等
        """
        self.chassis = None   # WooshApi 实例
        self.gripper = None   # GripperController 实例
        self.arm = None       # ArmController 实例
        pass
    
    def initialize(self) -> bool:
        """初始化所有连接
        
        Returns:
            bool: 全部连接成功返回 True
        """
        pass
    
    def move_to(self, x: float, y: float) -> bool:
        """移动底盘到指定位置"""
        pass
    
    def pick_object(self, x: float, y: float, z: float) -> bool:
        """在指定位置抓取物体
        
        Args:
            x, y, z: 物体在机器人坐标系下的位置
        
        Returns:
            bool: 抓取成功返回 True
        """
        pass
    
    def place_object(self, x: float, y: float, z: float) -> bool:
        """将物体放置到指定位置"""
        pass
    
    def get_status(self) -> dict:
        """获取机器人完整状态
        
        Returns:
            dict: 包含位置、电池、夹爪状态等
        """
        pass
```

### 抓取流程示例
```python
def pick_object(self, x, y, z):
    # 1. 移动到物体附近
    self.move_to(x, y)
    
    # 2. 张开夹爪准备抓取
    self.gripper.open()
    
    # 3. 机械臂移动到抓取点
    self.arm.go_to_position(x, y, z)
    
    # 4. 闭合夹爪
    self.gripper.close()
    
    # 5. 抬起机械臂
    self.arm.go_to_position(x, y, z + 0.2)
    
    return True
```

### 输出要求
- 文件路径: `src/control/robot_controller.py`
- 整合所有底层控制接口
- 实现完整的抓取和放置流程

---

## 🎯 模块五：配置文件管理

### 任务描述
实现 YAML 配置文件的加载和管理。

### 配置文件示例
```yaml
# config/robot_config.yaml
robot:
  name: "wheeled_robot"
  
  # WebSocket 配置
  websocket:
    ip: "192.168.1.100"
    port: 8080
    timeout: 8
    reconnect_interval: 5
  
  # ROS 配置
  ros:
    master_uri: "http://192.168.1.100:11311"
    arm_topic: "/kuavo_arm_traj"
    gripper_service: "/control_robot_leju_claw"
    control_mode_service: "/arm_traj_change_mode"

# 运动参数
motion:
  max_linear_speed: 0.5      # 最大线速度 (m/s)
  max_angular_speed: 1.0     # 最大角速度 (rad/s)
  default_speed: 0.15        # 默认移动速度
  approach_distance: 0.3     # 接近物体的距离 (m)

# 抓取参数
grasp:
  gripper_close_position: 90   # 闭合位置
  gripper_open_position: 0     # 张开位置
  pre_grasp_height: 0.15       # 预抓取高度 (m)
  lift_height: 0.2             # 抓取后抬起高度 (m)
  
# 调试选项
debug:
  enable_log: true
  log_level: "INFO"
  save_images: false
```

### 需要实现的功能
```python
class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str):
        """加载配置文件
        
        Args:
            config_path: 配置文件路径
        """
        pass
    
    def get(self, key: str, default=None):
        """获取配置值
        
        Args:
            key: 支持点号分隔，如 "robot.websocket.ip"
            default: 默认值
        """
        pass
    
    def set(self, key: str, value):
        """修改配置值"""
        pass
    
    def save(self):
        """保存配置到文件"""
        pass
```

### 输出要求
- 文件路径: `src/utils/config_manager.py`
- 支持 YAML 格式
- 支持嵌套键值访问

---

## 🎯 模块六：测试脚本

### 任务描述
编写完整的测试脚本，验证所有功能。

### 测试脚本要求

#### 6.1 连接测试
```python
# scripts/test_connection.py
"""
测试机器人连接
验证 WebSocket 和 ROS 连接是否正常
"""
```

#### 6.2 底盘移动测试
```python
# scripts/test_move.py
"""
测试底盘移动功能
- 前进/后退
- 左转/右转
- 导航到指定点
"""
```

#### 6.3 机械臂测试
```python
# scripts/test_arm.py
"""
测试机械臂控制
- 关节角度控制
- 位置控制
- 夹爪开合
"""
```

#### 6.4 完整抓取测试
```python
# scripts/test_pickup.py
"""
测试完整抓取流程
1. 移动到目标位置
2. 识别并抓取物体
3. 移动到放置位置
4. 释放物体
"""
```

### 输出要求
- 所有测试脚本放在 `scripts/` 目录
- 每个测试脚本可独立运行
- 包含详细的输出信息和错误处理

---

## 📦 依赖管理

### requirements.txt 内容
```txt
# WebSocket 通信
websocket-client>=1.3.0
rel>=0.4.0

# 数据处理
numpy>=1.21.0
PyYAML>=5.4.0

# ROS 相关（根据实际版本选择）
# ROS1:
rospy>=1.15.0
# 或 ROS2:
# rclpy>=3.0.0

# 工具
colorlog>=6.6.0
```

---

## 🚀 开发规范

### 代码风格要求
1. 使用 Python 3.8+ 语法
2. 遵循 PEP 8 代码规范
3. 添加完整的类型注解
4. 每个函数都需要 docstring
5. 使用 logging 而不是 print

### 错误处理要求
```python
# 示例：正确的错误处理
try:
    result = self.request("woosh.robot.RobotState")
    if result is None:
        logger.error("Failed to get robot state")
        return None
    return result
except websocket.WebSocketTimeoutException as e:
    logger.error(f"WebSocket timeout: {e}")
    return None
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return None
```

### 日志输出要求
```python
import logging

logger = logging.getLogger(__name__)

# 使用级别
logger.debug("详细调试信息")
logger.info("正常操作信息")
logger.warning("警告信息")
logger.error("错误信息")
```

---

## ✅ 验收标准

### 功能完整性
- [ ] WebSocket 连接成功建立
- [ ] 能获取机器人状态信息
- [ ] 能控制底盘移动
- [ ] 能控制机械臂运动
- [ ] 能控制夹爪开合
- [ ] 能执行完整抓取流程

### 代码质量
- [ ] 所有函数有类型注解
- [ ] 所有函数有 docstring
- [ ] 异常处理完善
- [ ] 日志输出规范
- [ ] 无硬编码配置

### 测试通过
- [ ] 连接测试通过
- [ ] 移动测试通过
- [ ] 机械臂测试通过
- [ ] 抓取测试通过

---

## 📝 注意事项

1. **IP 地址和端口需要配置化**，不能硬编码
2. **超时处理**：所有网络操作都需要设置超时
3. **重连机制**：WebSocket 断开后需要自动重连
4. **线程安全**：多线程环境下需要保证数据安全
5. **资源释放**：确保程序退出时正确关闭所有连接

---

## 🎯 输出文件清单

请生成以下文件的完整代码：

```
src/
├── communication/
│   ├── __init__.py
│   ├── websocket_client.py    # WebSocket 基础客户端
│   └── robot_api.py           # 底盘控制 API
├── control/
│   ├── __init__.py
│   ├── gripper_controller.py  # 夹爪控制器
│   ├── arm_controller.py      # 机械臂控制器
│   └── robot_controller.py    # 统一控制器
├── utils/
│   ├── __init__.py
│   └── config_manager.py      # 配置管理
config/
└── robot_config.yaml          # 配置文件模板

scripts/
├── test_connection.py          # 连接测试
├── test_move.py               # 移动测试
├── test_arm.py                # 机械臂测试
└── test_pickup.py             # 抓取测试

requirements.txt                # 依赖列表
```

---

## 💡 提示

1. 在生成代码时，请确保所有类和方法都有完整的实现
2. 对于不确定的接口参数，请添加 TODO 注释说明
3. 尽量使用标准库，减少第三方依赖
4. 代码要能够在 Ubuntu 22.04 + Python 3.10 环境下运行

现在，请根据以上要求，生成所有需要的代码文件。每个文件应该是完整的、可直接运行的。
```

---

这个 README.md 文件包含了：

1. **清晰的任务分解**：6 个核心模块，每个都有明确的功能定义
2. **接口规范**：每个函数都有参数、返回值、异常说明
3. **代码示例**：提供了关键接口的使用示例
4. **验收标准**：明确的功能和质量要求
5. **输出清单**：需要生成的所有文件列表

你可以直接把这个文件提供给生成式 AI，它就能按照要求生成完整的代码。需要我调整或补充任何部分吗？