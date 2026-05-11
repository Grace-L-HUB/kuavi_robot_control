# 测试音频

将课设演示用 wav 放在此目录（建议 16kHz 单声道，便于与板端统一）。

示例文件名：`demo_red_cup.wav`（内容可为「帮我拿红色的杯子」）。

运行：

```bash
# 在仓库根目录
python scripts/demo_voice_pipeline.py samples/demo_red_cup.wav
```

未准备音频时，可仅用 NLU 调试：

```bash
python scripts/demo_voice_pipeline.py --text "递给我蓝色的球"
```
