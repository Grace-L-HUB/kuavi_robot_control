# 基于华为昇腾平台的轮式机器人语音交互与抓取递送系统

## 项目简介

本项目基于华为 Atlas 200I DK A2 开发板，实现了一套可通过自然语言控制的轮式机器人语音交互与抓取递送系统。系统集成离线语音识别、语义理解、视觉目标检测与三维定位、机械臂抓取及自主导航等模块，打通从“语音指令输入”到“物品抓取递送”的全流程。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      用户语音指令                                │
│                    "把红色的杯子拿给我"                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    华为 Atlas 200I DK A2                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ Whisper模型   │ ──▶│ 语义解析     │ ──▶│ 任务调度     │       │
│  │ (语音转文字)  │    │ (意图提取)   │    │              │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                                       │                │
│         ▼                                       ▼                │
│  ┌──────────────┐                      ┌──────────────┐        │
│  │ YOLOv8模型   │                      │ 坐标变换与IK  │        │
│  │ (目标检测)   │                      │ (手眼标定)   │        │
│  └──────────────┘                      └──────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        机器人执行层                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ WebSocket    │    │ ROS Topic    │    │ ROS Service  │       │
│  │ (底盘控制)   │    │ (手臂控制)   │    │ (夹爪控制)   │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

## 功能模块

| 模块 | 功能 | 技术方案 |
|------|------|----------|
| 语音交互 | 离线语音识别与唤醒 | Whisper 轻量化模型 |
| 语义理解 | 自然语言意图解析 | BERT/Qwen-1.8B |
| 目标检测 | 物体识别与定位 | YOLOv8n + RGB-D相机 |
| 坐标变换 | 像素→3D坐标转换 | 相机内参 + 深度图 + 手眼标定 |
| 机械臂控制 | 抓取姿态计算与执行 | IK逆解 + /kuavo_arm_traj |
| 夹爪控制 | 物品抓取与释放 | /control_robot_leju_claw |
| 底盘导航 | 自主移动与定位 | WebSocket + SLAM |

## 项目结构

```
/home/HwHiAiUser/
├── robot_control/                 # 机器人硬件控制代码
│   ├── WooshWebSocketClient.py   # 底盘WebSocket控制
│   ├── arm_controller.py          # 机械臂ROS控制
│   ├── gripper_controller.py      # 夹爪ROS控制
│   └── config/
│       └── robot_config.yaml      # 机器人IP、端口等配置
│
├── vision_lim/                    # AI模型推理代码（语音/视觉/坐标）
│   ├── asr_backends/              # ASR 可替换后端（Whisper 本地 / 昇腾占位）
│   ├── detection.py               # YOLO目标检测（待补充）
│   ├── speech_recognition.py      # 语音识别入口（读 config 选择后端）
│   ├── semantic_parser.py         # 语义解析（当前为规则版）
│   ├── coordinate_transform.py    # 坐标变换（像素→3D）（待补充）
│   └── utils.py                   # 图像预处理工具（待补充）
│
├── config/
│   └── asr.yaml                   # ASR 后端与 Whisper 参数（上板后改 backend）
├── scripts/
│   └── demo_voice_pipeline.py     # 音频→文本→JSON 演示脚本
├── samples/                       # 放置测试用 wav（可与 PC/板子共用）
│
├── ascend_models/                 # 昇腾.om格式模型文件
│   ├── yolov8n.om                 # YOLO目标检测模型
│   ├── whisper.om                 # Whisper语音模型
│   └── bert.om                    # 语义理解模型
│
├── calibration/                   # 标定文件
│   ├── camera_intrinsics.yaml     # 相机内参
│   └── hand_eye_calibration.yaml  # 手眼标定矩阵
│
├── launch/                        # ROS启动文件
│   └── grasp_system.launch        # 系统主启动文件
│
└── README.md                      # 本文件
```

## 环境要求

### 硬件
- **开发板**：华为 Atlas 200I DK A2（Ubuntu 20.04）
- **机器人**：轮臂系列机器人（配备RGB-D相机、7轴机械臂、二指夹爪）
- **网络**：开发板与机器人位于同一局域网

### 软件
- **操作系统**：Ubuntu 20.04 aarch64
- **ROS版本**：ROS Noetic
- **AI框架**：Ascend CANN 6.0+
- **Python**：3.8+

## 安装步骤

### 1. 开发板环境配置

```bash
# 更新软件源
sudo apt update && sudo apt upgrade -y

# 安装ROS Noetic
sudo sh -c 'echo "deb http://packages.ros.org/ros/ubuntu focal main" > /etc/apt/sources.list.d/ros-latest.list'
sudo apt-key adv --keyserver 'hkp://keyserver.ubuntu.com:80' --recv-key C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654
sudo apt install ros-noetic-desktop-full

# 设置ROS环境
echo "source /opt/ros/noetic/setup.bash" >> ~/.bashrc
source ~/.bashrc

# 安装Python依赖
pip3 install numpy opencv-python ultralytics websocket-client
```

### 2. 确认昇腾CANN环境

```bash
# 检查NPU状态
npu-smi info

# 设置CANN环境变量
source /usr/local/Ascend/ascend-toolkit/set_env.sh
```

### 3. 模型转换（YOLOv8示例）

```bash
# 在PC上导出ONNX
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt').export(format='onnx')"

# 在开发板上使用ATC工具转换
atc --model=yolov8n.onnx \
    --framework=5 \
    --output=yolov8n \
    --input_format=NCHW \
    --soc_version=Ascend310B
```

将生成的 `yolov8n.om` 放入 `ascend_models/` 目录。

### 4. 相机内参获取

```bash
# 订阅camera_info话题获取内参
rostopic echo /camera/color/camera_info
```

### 5. 手眼标定

参考 `calibration/` 目录下的标定指南，完成相机到机械臂基座的坐标变换矩阵标定。

## 使用方法

### 启动机器人底盘与机械臂

确保机器人已上电，网络连接正常。

### 运行主程序

```bash
# 进入工作目录
cd /home/HwHiAiUser

# 启动系统（示例）
python3 robot_control/main.py
```

### 语音指令示例

| 指令 | 预期行为 |
|------|----------|
| "小助小助，把红色的杯子拿给我" | 识别红色杯子，移动到目标位置，抓取并递送 |
| "小助小助，拿那个手机" | 检测手机，抓取并递送 |
| "小助小助，停止" | 停止当前任务，手臂归位 |

## 核心算法说明

### 图像到3D坐标转换

1. **目标检测**：YOLOv8n 输出物体中心像素坐标 `(u, v)`
2. **深度获取**：从深度图对应位置读取深度值 `Z`（单位：米）
3. **相机坐标**：利用内参 `(fx, fy, cx, cy)` 转换为相机坐标系：
   ```
   X = (u - cx) * Z / fx
   Y = (v - cy) * Z / fy
   Z = depth_value
   ```
4. **机械臂坐标**：通过手眼标定矩阵变换到机械臂基座坐标系

### 机械臂控制流程

1. 切换手臂到外部控制模式：`/arm_traj_change_mode`（mode=2）
2. 预抓取：移动到物体正上方5cm
3. 下降：垂直下降到抓取高度
4. 闭合夹爪：`/control_robot_leju_claw`（position=90）
5. 上升：提起物品
6. 移动底盘到递送点
7. 释放夹爪：`/control_robot_leju_claw`（position=0）

## 故障排查

| 问题 | 可能原因 | 解决方法 |
|------|----------|----------|
| SSH连接失败 | IP配置错误 | 确认开发板与电脑在同一网段 |
| 无法上网 | DNS问题 | 配置 `/etc/resolv.conf` 添加 `nameserver 114.114.114.114` |
| 模型推理失败 | `.om` 模型转换错误 | 确认 `soc_version` 为 `Ascend310B` |
| 机器人连接失败 | WebSocket IP错误 | 检查 `config/robot_config.yaml` 中的机器人IP |
| 深度值为0 | 物体材质反光 | 调整物体位置或使用周围有效深度中位数 |
| 抓取位置偏差 | 手眼标定不准 | 重新进行手眼标定 |

## 参考资料

## 待完成功能

- [ ] 完整的多物体抓取测试
- [ ] 性能优化与延迟降低
- [ ] 更多物体类型的模型训练

## 联系方式

- 项目负责人：郭隶楷、何柳岩、李思远、张竹和