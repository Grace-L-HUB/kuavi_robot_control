# Kuavi 语音视觉抓取系统

基于华为 Atlas 200I DK A2 的轮式机器人语音交互与抓取方案。当前已验证的闭环为 **上位机采图 → Atlas 语音/视觉推理 → 下位机 ROS 抓取**：Atlas 侧不依赖 ROS，产出 `grasp_target.json`；下位机读取其中的 `camera_coord_m` 完成机械臂 IK 与夹爪控制。

## 系统角色

| 节点 | 硬件/环境 | 职责 |
|------|-----------|------|
| **上位机** | 轮臂机器人工控机 / 开发 PC | 采集 RGB-D 图像、相机内参；录制语音；将数据包拷贝到 Atlas |
| **Atlas 200I DK A2** | 昇腾 NPU 开发板 | Whisper ASR + 语义解析 + YOLO 检测 + 深度反投影 → `grasp_target.json` |
| **下位机** | Kuavo ROS 机器人 | 载入控制脚本，读取 JSON，执行三段位姿抓取与安全放开 |

## 总体数据流

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 上位机（机器人/PC）                                                       │
│  • color_image.png / depth_image.png                                    │
│  • camera_info.txt / camera_info1.txt（color/depth 内参）               │
│  • record*.m4a（语音「拿瓶子」等）                                         │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ U 盘 / scp 拷贝到 instance/
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Atlas 200I（~/kuavi_robot_control）                                     │
│  atlas_voice_grasp_pipeline.py                                          │
│    ① 语音 → Whisper(NPU encoder + CPU decode) → 语义 → target 类别      │
│    ② YOLOv8n(NPU .om) → bbox → 抓取像素点                               │
│    ③ 深度采样 + 内参反投影 → camera_coord_m（相机 optical 系，米）       │
│    ④ 写入 instance/grasp_target.json + scripts/grasp_target.json        │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ 拷贝 grasp_target.json + 控制脚本
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 下位机（kuavo-ros-opensource/scripts/）                                  │
│  grasp_from_offline_vision.py --hand left                               │
│    • 读取 camera_coord_m → base 系抓取位姿                               │
│    • 三段位姿：左上方 → 平移至正上方 → 垂直下降                           │
│    • 夹紧 → 上提展示 → 下放 → 水平后撤松爪 → 回零                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 功能模块

| 模块 | 功能 | 技术方案 |
|------|------|----------|
| 语音交互 | 离线语音识别 | Whisper encoder NPU + CPU decode |
| 语义理解 | 意图与目标类别解析 | 规则 NLU + 同音纠错（`semantic_parser.py`） |
| 目标检测 | 物体识别与定位 | YOLOv8n NPU（`.om`）+ RGB 图 |
| 坐标转换 | 像素 → 3D 坐标 | 相机内参 + 深度图反投影（camera optical 系） |
| 机械臂控制 | 抓取姿态与轨迹 | IK + `/kuavo_arm_traj` |
| 夹爪控制 | 抓取与释放 | `/control_robot_leju_claw` |

## 项目结构

PC 开发与 Atlas 部署共用本仓库；部署到 Atlas 时通常同步为 `~/kuavi_robot_control`。

```
Kuavi_bot_control/
├── instance/                          # 上位机采集数据（输入/输出）
│   ├── color_image.png
│   ├── depth_image.png
│   ├── camera_info.txt                # color camera_info
│   ├── camera_info1.txt               # depth camera_info
│   ├── record5.m4a                    # 语音指令
│   └── grasp_target.json              # Atlas 输出（给下位机）
│
├── config/
│   ├── asr_atlas_npu.yaml             # Atlas NPU ASR（Whisper encoder.om）
│   ├── asr.yaml                       # PC 侧 ASR 配置
│   └── vision.yaml                    # YOLO NPU/CPU 自动选择
│
├── ascend_models/
│   ├── whisper_encoder.om
│   └── yolov8n.om
│
├── vision_lim/                        # 语音 / 视觉 / 坐标模块
│   ├── voice_pipeline.py              # ASR + NLU
│   ├── semantic_parser.py             # 意图解析与同音纠错
│   ├── yolo_detect.py                 # NPU/CPU YOLO 统一入口
│   ├── camera_info_parser.py          # 解析 camera_info.txt
│   └── asr_backends/ascend_om.py      # Whisper NPU 后端
│
├── robot_control/                     # 下位机控制参考与接口说明
│   └── interface.md
│
└── scripts/
    ├── activate_kuavi_atlas.sh        # Atlas 每次运行前 source
    ├── atlas_voice_grasp_pipeline.py  # Atlas 端到端流水线（核心）
    └── grasp_from_offline_vision.py   # 下位机抓取脚本（可单独拷贝）
```

## 环境要求

| 节点 | 硬件 | 软件 |
|------|------|------|
| Atlas 200I DK A2 | 昇腾 310B4 NPU | Ubuntu 20.04 aarch64、CANN 6.0+、Python 3.9 venv（`~/kuavi`） |
| 上位机 / 下位机 | 轮臂机器人 + RGB-D 相机 | ROS Noetic（下位机）、与 Atlas 可通过 U 盘/scp 交换数据 |

模型转换（ONNX → `.om`）见 [ascend_models/readme.md](ascend_models/readme.md)。

---

## 第一步：上位机采集

在机器人或联调 PC 上，与目标场景**同一时刻**保存以下文件（放入 `instance/`）：

| 文件 | 说明 |
|------|------|
| `color_image.png` | RGB 彩色图 |
| `depth_image.png` | 对齐的深度图（16 bit 单通道） |
| `camera_info.txt` | `/camera/color/camera_info` 导出（含 fx, fy, cx, cy） |
| `camera_info1.txt` | `/camera/depth/camera_info` 导出 |
| `record*.m4a` | 麦克风录音，如「拿瓶子」 |

图像、深度、内参、语音应来自**同一次观测**，否则坐标与语义会不匹配。

将整个 `instance/` 目录拷贝到 Atlas：`~/kuavi_robot_control/instance/`。

---

## 第二步：Atlas 200I 语音 + 视觉 + 坐标

### 环境准备（每次新开终端）

```bash
cd ~/kuavi_robot_control
source scripts/activate_kuavi_atlas.sh
```

`activate_kuavi_atlas.sh` 会依次：激活 `~/kuavi` venv → source CANN → 配置 `acl` 的 `PYTHONPATH`。

### 运行端到端流水线

```bash
python3 scripts/atlas_voice_grasp_pipeline.py \
  --asr-config config/asr_atlas_npu.yaml \
  --vision-config config/vision.yaml \
  --device npu \
  --audio instance/record5.m4a
```

### 流水线内部步骤

1. **语音识别（ASR）** — 输入 `record*.m4a`，模型 `ascend_models/whisper_encoder.om`（NPU）+ CPU decode，输出如「拿瓶子」。
2. **语义理解（NLU）** — `vision_lim/semantic_parser.py`，输出 `{"action":"fetch","target":"bottle",...}`，支持同音纠错（如「屏子」→ 瓶子）。
3. **目标检测（YOLO）** — `ascend_models/yolov8n.om`（NPU，`soc_version=Ascend310B4`），在彩色图中检测 COCO 类别；抓取像素为 bbox 水平中心 + 垂直 65% 偏下。
4. **坐标转换** — color 像素映射到 depth 像素，深度邻域中值采样，反投影到 **camera optical 坐标系（米）**，写入 `camera_coord_m`。

### 输出文件

- `instance/grasp_target.json`
- `scripts/grasp_target.json`（副本，便于 scp）

```json
{
  "voice_transcript": "拿瓶子",
  "voice_task": { "action": "fetch", "target": "bottle" },
  "yolo_backend": "npu",
  "camera_coord_m": [-0.213, 0.074, 0.582],
  "pixel_color": [178, 298],
  "pixel_depth": [181, 286],
  "depth_m": 0.582
}
```

下位机抓取脚本**仅依赖** `camera_coord_m`；其余字段供调试与记录。

### 常用调试参数

```bash
# 跳过 ASR，直接指定中文测视觉+坐标
python3 scripts/atlas_voice_grasp_pipeline.py \
  --text "拿瓶子" --device npu

# 指定输出路径
python3 scripts/atlas_voice_grasp_pipeline.py \
  --output instance/grasp_target.json \
  --audio instance/record5.m4a
```

---

## 第三步：下位机载入控制脚本并抓取

### 拷贝文件

```text
kuavo-ros-opensource/scripts/
├── grasp_from_offline_vision.py   # 自 Kuavi_bot_control/scripts/
└── grasp_target.json              # 自 Atlas 输出
```

### 环境

```bash
source /opt/ros/noetic/setup.bash
source /home/lab/kuavo-ros-opensource/devel/setup.bash
cd /home/lab/kuavo-ros-opensource/scripts
```

### 预览坐标（不动作）

```bash
python3 grasp_from_offline_vision.py \
  --hand left \
  --dry-coords \
  --grasp-json grasp_target.json
```

### 实机抓取

```bash
python3 grasp_from_offline_vision.py \
  --hand left \
  --grasp-json grasp_target.json
```

### 下位机控制逻辑

| 阶段 | 行为 |
|------|------|
| 接近 | 左上方 → 平移至物品正上方 → 垂直下降（抓取姿态 IK） |
| 抓取 | 闭合 `left_claw` |
| 展示 | 分两段垂直上提至正上方，短暂停留 |
| 安全放开 | 下放回抓取高度 → **水平后撤** → 松爪 → 上提 → 双臂回零 |

位姿偏置、三段位姿距离、上提高度等均在 `scripts/grasp_from_offline_vision.py` 顶部 **用户参数区** 调整；修改后先 `--dry-coords` 再实机。

---

## 坐标转换说明

1. YOLO 输出 bbox，取抓取像素 `(u, v)`（color 图）。
2. 按 color/depth 内参 cx、cy 偏移，映射到 depth 图对应像素。
3. 在 depth 邻域取中值深度 `Z`（米）。
4. 利用内参反投影到 camera optical 系：
   ```
   X = (u - cx) * Z / fx
   Y = (v - cy) * Z / fy
   Z = depth_value
   ```
5. 下位机脚本将 camera 坐标变换到机械臂 base 系后做 IK（见 `grasp_from_offline_vision.py`）。

---

## 三机协作检查清单

- [ ] 上位机：`color/depth` 图与 `camera_info` 成对、时间一致
- [ ] Atlas：`source scripts/activate_kuavi_atlas.sh` 后 `import acl` 正常
- [ ] Atlas：流水线日志出现 `yolo_backend: NPU` 与合理 `camera_coord_m`
- [ ] 下位机：`grasp_target.json` 与脚本在同一 `scripts/` 目录
- [ ] 下位机：`--dry-coords` 坐标合理后再 `--hand left` 实机

## 常见问题

| 现象 | 处理 |
|------|------|
| Atlas `import acl` 失败 | 重新 `source scripts/activate_kuavi_atlas.sh`；确认 CANN 与 Python 3.9 venv |
| YOLO 无检测 | 确认 `yolov8n.om` 存在；画面中有目标物体；可降低 `config/vision.yaml` 中 `conf_threshold` |
| 模型推理失败 | 确认 `soc_version` 为 `Ascend310B4`；详见 [ascend_models/readme.md](ascend_models/readme.md) |
| 正上方 IK 失败 | 脚本已拆「高位平移 + 下降」；可调 `APPROACH_ABOVE_CLEARANCE_M` |
| 抓取偏位 | 上位机重新采图；或调 `grasp_from_offline_vision.py` 中 `LEFT_GRASP_*_BIAS` |
| 深度值为 0 | 物体反光或超出量程；检查 depth 图对应像素，或调整采样邻域 |
| 松爪带倒物体 | 使用内置「水平后撤后再松爪」流程，勿在抓取点原位直接张开 |

## 相关文档

| 文档 | 内容 |
|------|------|
| [vision_lim/readme.md](vision_lim/readme.md) | 视觉 / 语音模块细节 |
| [ascend_models/readme.md](ascend_models/readme.md) | ONNX → OM 转换 |
| [robot_control/interface.md](robot_control/interface.md) | Kuavo ROS 接口（IK、夹爪、arm_traj） |
| [scripts/grasp_from_offline_vision.py](scripts/grasp_from_offline_vision.py) | 下位机抓取实现与参数 |

## 版本说明

当前文档对应已验证闭环：

- **Atlas**：Whisper encoder NPU + YOLOv8n NPU，`atlas_voice_grasp_pipeline.py` 输出 `grasp_target.json`
- **下位机**：`grasp_from_offline_vision.py` 左手三段位姿抓取 + 安全放开 + 回零

后续若改为 ROS 话题实时传图，可在上位机与 Atlas 之间增加同步节点，**JSON 接口与下位机脚本保持不变**。
