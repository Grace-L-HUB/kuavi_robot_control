# ascend_models/README.md

本目录存放经过昇腾ATC工具转换后的 `.om` 格式模型文件，供NPU推理使用。

## 昇腾平台简介

Atlas 200I DK A2开发板搭载昇腾310 AI处理器，提供8 TOPS INT8算力，支持高效的神经网络推理。开发板已预装CANN软件包，可直接用于模型推理。

## 模型列表

| 文件名 | 原始模型 | 用途 | 输入尺寸 | 输出说明 |
|--------|----------|------|----------|----------|
| `yolov8n.om` | YOLOv8n | 目标检测 | 640×640 | 边界框、类别、置信度 |
| `whisper.om` | Whisper | 语音转文字 | 音频特征 | 文本序列 |
| `bert.om` | BERT/Qwen-1.8B | 语义解析 | 文本token | 结构化指令JSON |

## 模型转换指南

昇腾平台不能直接运行PyTorch/TensorFlow等开源框架的模型，需要使用ATC工具转换为 `.om` 格式。

### 环境准备

1. 确认CANN已正确安装：
```bash
source /usr/local/Ascend/ascend-toolkit/set_env.sh
```

2. 查看开发板的 `soc_version`：
```bash
npu-smi info
```
Atlas 200I DK A2 的 `soc_version` 为 **Ascend310B4**（或Ascend310B）。

### YOLOv8模型转换示例

**步骤1：PyTorch → ONNX**

```python
from ultralytics import YOLO

# 导出ONNX格式（不要包含NMS）
model = YOLO("yolov8n.pt")
model.export(format="onnx", imgsz=640, opset=12)
```

关键参数说明：
- 不要设置 `--end2end`（NMS后处理需独立）
- 不要设置 `--dynamic`（保持输入尺寸固定）

**步骤2：ONNX → OM（在开发板上执行）**

```bash
atc --model=yolov8n.onnx \
    --framework=5 \
    --output=yolov8n \
    --input_format=NCHW \
    --input_shape="images:1,3,640,640" \
    --soc_version=Ascend310B4 \
    --log=info
```

参数说明：
| 参数 | 说明 |
|------|------|
| `--model` | 输入的ONNX模型路径 |
| `--framework=5` | 表示输入为ONNX格式 |
| `--output` | 输出OM模型文件名 |
| `--soc_version` | 目标芯片型号（Ascend310B4） |
| `--input_shape` | 指定输入张量的形状 |

### 其他模型转换注意事项

- **Whisper语音模型**：输入为音频特征，需保持输入尺寸固定
- **BERT语义模型**：输入为token序列，可使用动态batch

## 推理调用示例

转换完成后，可在Python中使用mindx.sdk加载模型进行推理：

```python
import numpy as np
from mindx.sdk.base import Tensor, Model

# 加载模型
model = Model(modelPath="yolov8n.om", deviceId=0)

# 准备输入
input_tensor = Tensor(input_array)
input_tensor.to_device(0)
input_tensors = [input_tensor]

# 执行推理
outputs = model.infer(input_tensors)
```

## 常见问题

| 问题 | 解决方法 |
|------|----------|
| `soc_version` 不识别 | 使用 `npu-smi info` 查看实际值，通常为 `Ascend310B4` |
| 推理输出shape不对 | 检查ONNX导出时是否包含了NMS，应导出未处理的原始输出 |
| 模型转换后精度下降 | 尝试使用 `--precision_mode` 参数调整精度模式 |