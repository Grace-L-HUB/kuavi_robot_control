# vision_llm/README.md

本目录包含视觉与语言模型推理的核心代码，负责从传感器数据（图像、音频）中提取结构化信息，供机器人控制模块使用。

## 模块参考结构

```
vision_llm/
├── detection.py           # YOLO目标检测（像素坐标+类别）
├── speech_recognition.py  # Whisper语音识别（音频→文本）
├── semantic_parser.py     # BERT语义解析（文本→结构化指令）
├── coordinate_transform.py # 像素坐标→3D空间坐标（含手眼标定）
├── depth_processor.py     # 深度图预处理与滤波
├── camera_intrinsics.yaml # 相机内参配置文件
└── utils.py               # 公共工具函数
```

## 模块说明

| 文件 | 输入 | 输出 | 依赖模型 |
|------|------|------|----------|
| `detection.py` | RGB图像 | `(class, bbox_center_u, bbox_center_v, confidence)` | `yolov8n.om` |
| `speech_recognition.py` | 音频数据（麦克风） | 文本字符串 | `whisper.om` |
| `semantic_parser.py` | 文本指令 | `{"action": "fetch", "target": "cup", "attribute": "red"}` | `bert.om` |
| `coordinate_transform.py` | 像素坐标 `(u, v)` + 深度值 `Z` | 机械臂基座坐标系 `(X, Y, Z)` | 相机内参、手眼标定矩阵 |
| `depth_processor.py` | 原始深度图 | 滤波后的深度值 | 无 |

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

## 配置文件格式

### camera_intrinsics.yaml
```yaml
# 相机内参（需根据实际标定结果填写）
image_width: 640
image_height: 480
fx: 616.0   # 焦距x（像素）
fy: 616.0   # 焦距y（像素）
cx: 320.0   # 光心x
cy: 240.0   # 光心y
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

## 依赖项

```bash
pip install numpy opencv-python pillow pyyaml
```

昇腾推理依赖（需正确设置环境变量）：
```bash
source /usr/local/Ascend/ascend-toolkit/set_env.sh
```

## 使用示例

```python
from vision_llm import detection, depth_processor, coordinate_transform

# 1. 目标检测
rgb_image = cv2.imread("scene.jpg")
detections = detection.detect_objects(rgb_image)

for det in detections:
    print(f"检测到: {det.class_name}, 中心: {det.bbox_center}")
    
    # 2. 获取深度
    depth_m = depth_processor.get_reliable_depth(depth_image, *det.bbox_center)
    
    # 3. 坐标转换
    point_cam = coordinate_transform.pixel_to_camera_coord(
        det.bbox_center[0], det.bbox_center[1], depth_m, intrinsics
    )
    point_arm = coordinate_transform.camera_to_arm_base(point_cam, T_cam_to_arm)
    
    print(f"抓取坐标: {point_arm}")
```