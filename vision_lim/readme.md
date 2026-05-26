# vision_llm/README.md

本目录包含视觉与语言模型推理的核心代码，负责从传感器数据（图像、音频）中提取结构化信息，供机器人控制模块使用。

## 模块参考结构

```
vision_lim/
├── detection.py           # YOLO目标检测（像素坐标+类别）
├── speech_recognition.py  # Whisper语音识别（音频→文本）
├── semantic_parser.py     # 语义解析（文本→结构化指令）
├── coordinate_transform.py # 像素坐标→3D空间坐标（含手眼标定）
├── depth_processor.py     # 深度图预处理与滤波
├── vision_pipeline.py     # 视觉感知流水线（整合所有模块）
├── config/
│   └── camera_intrinsics.yaml  # 相机内参配置
└── utils.py               # 公共工具函数
```

## 模块说明

| 文件 | 输入 | 输出 | 依赖模型 |
|------|------|------|----------|
| `detection.py` | RGB图像 | `(class, bbox_center_u, bbox_center_v, confidence)` | `yolov8n.om` |
| `speech_recognition.py` | 音频数据（麦克风） | 文本字符串 | `whisper.om` |
| `semantic_parser.py` | 文本指令 | `{"action": "fetch", "target": "cup", "attribute": "red"}` | 无 |
| `coordinate_transform.py` | 像素坐标 `(u, v)` + 深度值 `Z` | 机械臂基座坐标系 `(X, Y, Z)` | 相机内参、手眼标定矩阵 |
| `depth_processor.py` | 原始深度图 | 滤波后的深度值 | 无 |
| `vision_pipeline.py` | 语音指令/音频 | 目标3D坐标 | 所有上游模块 |

## 数据流向

```
麦克风 ──▶ speech_recognition.py ──▶ 文本指令
                                          │
                                          ▼
                    semantic_parser.py ──▶ 结构化JSON
                                          │
相机彩色图 ──▶ detection.py ──▶ (u, v) ──┤
                                          │
相机深度图 ──▶ depth_processor.py ──▶ Z ─┼──▶ coordinate_transform.py
                                          │
相机内参 ──▶ (fx, fy, cx, cy) ────────────┤
                                          │
手眼标定 ──▶ T_cam_to_arm ────────────────┘
                                          │
                                          ▼
                                   机械臂抓取坐标 (X, Y, Z)
```

## 快速使用

### 方式一：使用便捷函数（推荐）

```python
from vision_lim import locate_object_from_voice, locate_object_from_audio

# 从语音文本定位目标
result = locate_object_from_voice("把红色的杯子拿给我")
if result:
    arm_coord = result["target"]["arm_coord"]
    print(f"目标坐标: {arm_coord}")

# 从音频文件定位目标
result = locate_object_from_audio("path/to/audio.wav")
```

### 方式二：使用流水线类

```python
from vision_lim import VisionPipeline

# 创建流水线
pipeline = VisionPipeline(
    config_path="vision_lim/config/camera_intrinsics.yaml",
    model_path="ascend_models/yolov8n.pt",
)

# 从语音指令定位
result = pipeline.locate_target_from_voice("把红色的杯子拿给我")
if result:
    print(f"目标类别: {result.target.class_name}")
    print(f"像素坐标: {result.target.pixel_coord}")
    print(f"机械臂坐标: {result.target.arm_coord}")
```

### 方式三：分步使用

```python
from vision_lim import (
    YOLODetector,
    DepthProcessor,
    CoordinateTransformer,
    get_reliable_depth,
    compute_target_position,
    parse_instruction,
)

# 1. 语义解析
command = parse_instruction("把红色的杯子拿给我")
print(f"目标: {command.target}, 属性: {command.attribute}")

# 2. 初始化组件
detector = YOLODetector(classes=["cup", "bottle", "ball"])
detector.initialize()

depth_proc = DepthProcessor()
transformer = CoordinateTransformer()

# 3. 获取同步的彩色图和深度图
# (需要ROS环境，这里假设已获取)
color_img, depth_img = get_synchronized_frames()

# 4. 目标检测
detections = detector.detect_once(color_img)
target_detection = detections[0]  # 假设第一个就是目标

# 5. 获取深度
u, v = target_detection.bbox_center
depth_m = get_reliable_depth(depth_img, u, v)

# 6. 计算3D坐标
target_pos = compute_target_position(
    detection=target_detection,
    depth_m=depth_m,
    transformer=transformer,
)

print(f"机械臂基座坐标: {target_pos.arm_coord}")
```

## 关键函数参考说明

### detection.py

```python
def detect_objects(image: np.ndarray) -> List[Detection]:
    """
    对输入图像进行目标检测

    参数:
        image: BGR格式的彩色图像 (H, W, 3)

    返回:
        Detection对象列表，每个包含:
        - class_name: str，物体类别（如"cup", "bottle"）
        - confidence: float，置信度(0-1)
        - bbox_center: (u, v)，边界框中心像素坐标
        - bbox: (x1, y1, x2, y2)，边界框四个角点
    """
```

### coordinate_transform.py

```python
def pixel_to_camera_coord(u: int, v: int, depth_m: float,
                          intrinsics: dict) -> tuple:
    """
    像素坐标转相机坐标系3D坐标

    公式:
        X = (u - cx) * Z / fx
        Y = (v - cy) * Z / fy
        Z = depth_m

    参数:
        u, v: 像素坐标
        depth_m: 深度值（单位：米）
        intrinsics: {'fx', 'fy', 'cx', 'cy'}

    返回:
        (X, Y, Z) 相机坐标系下的坐标（单位：米）
    """

def camera_to_arm_base(point_cam: tuple, T_cam_to_arm: np.ndarray) -> tuple:
    """
    相机坐标系 → 机械臂基座坐标系

    公式:
        P_arm = R * P_cam + t

    参数:
        point_cam: (X, Y, Z) 相机坐标系坐标
        T_cam_to_arm: 4x4齐次变换矩阵 [R t; 0 1]

    返回:
        (X_arm, Y_arm, Z_arm) 机械臂基座坐标系坐标
    """
```

### depth_processor.py

```python
def get_reliable_depth(depth_image: np.ndarray, u: int, v: int,
                       window_size: int = 5) -> float:
    """
    获取可靠的深度值（处理无效点）

    策略:
        1. 若(u,v)处深度有效，直接返回
        2. 否则取周围窗口内有效深度的中位数

    参数:
        depth_image: 16UC1格式深度图（单位：毫米）
        u, v: 像素坐标
        window_size: 搜索窗口大小（奇数）

    返回:
        深度值（单位：米），若无有效深度返回None
    """
```

### semantic_parser.py

```python
def parse_instruction(text: str) -> dict:
    """
    解析自然语言指令为结构化数据

    输入示例:
        "把红色的杯子拿给我"

    输出示例:
        {
            "action": "fetch",
            "target": "cup",
            "attribute": "red",
            "location": None
        }
    """
```

### vision_pipeline.py

```python
class VisionPipeline:
    """视觉感知流水线"""

    def locate_target_from_voice(self, text: str, timeout: float = 10.0) -> Optional[TargetResult]:
        """
        从语音指令定位目标物体

        参数:
            text: 语音识别文本
            timeout: 超时时间（秒）

        返回:
            TargetResult对象，包含:
            - target.arm_coord: 机械臂基座坐标系下的3D坐标
            - command.target: 目标物体类别
            - command.attribute: 目标属性（颜色等）
        """

class GraspPlanner:
    """抓取规划器"""

    def plan_grasp_pose(self, target_pos: tuple, hand: str = "right") -> dict:
        """
        规划抓取姿态

        返回:
            包含 pre_grasp、grasp、retreat 位置的字典
        """
```

## 配置文件格式

### camera_intrinsics.yaml

```yaml
# 相机内参（需根据实际标定结果填写）
color_camera:
  topic: "/camera_1/color/image_raw"
  width: 320
  height: 240
  fx: 361.1151123046875
  fy: 361.1151123046875
  cx: 321.2451477050781
  cy: 180.9050750732422

depth_camera:
  topic: "/camera_1/depth/image_rect_raw"
  width: 320
  height: 240
  fx: 192.194091796875
  fy: 192.194091796875
  cx: 154.92611694335938
  cy: 119.32855224609375

hand_eye_calibration:
  enabled: false
  T_cam_to_arm:
    - [1.0, 0.0, 0.0, 0.0]
    - [0.0, 1.0, 0.0, 0.0]
    - [0.0, 0.0, 1.0, 0.0]
    - [0.0, 0.0, 0.0, 1.0]
```

### T_cam_to_arm.npy

手眼标定矩阵，4x4 NumPy数组格式，通过手眼标定流程获得：

```python
T_cam_to_arm = np.array([
    [R00, R01, R02, tx],
    [R10, R11, R12, ty],
    [R20, R21, R22, tz],
    [0,   0,   0,   1 ]
])
```

## ROS话题映射

根据官方文档和rostopic信息，相机话题映射如下：

| 功能 | ROS话题 | 消息类型 |
|------|---------|----------|
| 彩色图像 | `/camera_1/color/image_raw` | `sensor_msgs/Image` |
| 深度图像 | `/camera_1/depth/image_rect_raw` | `sensor_msgs/Image` |
| 彩色相机内参 | `/camera_1/color/camera_info` | `sensor_msgs/CameraInfo` |
| 深度相机内参 | `/camera_1/depth/camera_info` | `sensor_msgs/CameraInfo` |

**注意**: 代码中默认使用 `/camera_1/` 前缀，如实际环境使用不同前缀，请修改配置文件或构造函数参数。

## 依赖项

```bash
pip install -r requirements-asr.txt
```

基础依赖:
```bash
pip install numpy opencv-python pillow pyyaml
```

视觉感知依赖:
```bash
pip install ultralytics onnxruntime
```

昇腾推理依赖（需正确设置环境变量）:
```bash
source /usr/local/Ascend/ascend-toolkit/set_env.sh
```

ROS依赖（仅在机器人上运行时需要）:
```bash
pip install rospkg sensor_msgs cv_bridge
```

## 使用示例

### PC开发环境（无需ROS）

```bash
# 测试视觉流水线
python scripts/test_vision_pipeline.py
```

### 机器人运行环境

```bash
# 启动ROS master
roscore

# 启动相机节点（根据实际环境）

# 运行视觉感知
python scripts/test_vision_pipeline.py
```

## 抓取流程说明

完整抓取流程涉及两个模块：

1. **vision_lim** (本模块): 目标定位
   - 语音识别 → 语义解析 → 目标检测 → 深度获取 → 坐标变换
   - 输出: 机械臂基座坐标系下的3D坐标

2. **robot_control** (robot_control模块): 运动控制
   - 接收目标坐标 → 逆运动学求解 → 轨迹规划 → 执行抓取
   - 使用 `ArmController.go_to_cartesian()` 移动机械臂
   - 使用 `GripperController` 控制夹爪开合

### 完整抓取示例

```python
from vision_lim import VisionPipeline, GraspPlanner
from robot_control import ArmController, GripperController

# 1. 视觉定位
pipeline = VisionPipeline()
result = pipeline.locate_target_from_voice("把杯子拿给我")

if result:
    target_pos = result.target.arm_coord

    # 2. 抓取规划
    planner = GraspPlanner()
    grasp_plan = planner.plan_grasp_pose(target_pos, hand="right")

    # 3. 机械臂控制
    arm = ArmController()
    arm.go_to_cartesian(*grasp_plan["pre_grasp"]["position"], hand="right")

    # 4. 移动到抓取位置
    arm.go_to_cartesian(*grasp_plan["grasp"]["position"], hand="right")

    # 5. 夹爪闭合
    gripper = GripperController()
    gripper.close()

    # 6. 抬升并移动
    arm.go_to_cartesian(*grasp_plan["retreat"]["position"], hand="right")
```

## 注意事项

1. **手眼标定**: 首次部署时需要进行手眼标定，将 `T_cam_to_arm.npy` 文件放置在 `vision_lim/` 目录下。

2. **相机话题**: 根据实际ROS环境修改配置文件中的话题名称。

3. **YOLO模型**: 开发环境使用 `.pt` 格式，昇腾端使用 `.om` 格式。

4. **深度图单位**: 相机深度图可能使用不同单位（毫米或米），代码会自动处理转换。

5. **坐标系**: 输出坐标使用机械臂基座坐标系，单位为米。