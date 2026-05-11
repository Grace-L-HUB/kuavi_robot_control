# 测试音频

将课设演示用 wav 放在此目录（建议 16kHz 单声道，便于与板端统一）。

示例文件名：`demo_red_cup.wav`（内容可为「帮我拿红色的杯子」）。

运行：

```bash
# 在仓库根目录
python scripts/demo_voice_pipeline.py samples/demo_red_cup.wav
```

Python 中一键「语音 → 任务 JSON」：

```python
from vision_lim import speech_file_to_json

task = speech_file_to_json("samples/demo_red_cup.wav")
# task == {"action": "fetch", "target": "cup", "attribute": "red", "location": None}
```

未准备音频时，可仅用 NLU 调试：

```bash
python scripts/demo_voice_pipeline.py --text "递给我蓝色的球"
```

麦克风录制（需 `pip install sounddevice numpy`，Windows 一般可直接用）：

```bash
python scripts/demo_voice_pipeline.py --record
# 保存本次录音并识别：
python scripts/demo_voice_pipeline.py --record -o samples/last.wav --seconds 6
```

查看麦克风设备编号：`python -m sounddevice`
