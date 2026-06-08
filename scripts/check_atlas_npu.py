#!/usr/bin/env python3
"""检查 Atlas NPU 环境与模型文件是否就绪。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    from vision_lim.ascend import can_use_yolo_npu, default_om_path, is_ascend_available

    print("=== NPU 环境检查 ===")
    print("acl 可用:", is_ascend_available())
    yolo_om = default_om_path("yolov8n.om")
    whisper_om = default_om_path("whisper_encoder.om")
    print("yolov8n.om:", yolo_om, "存在" if yolo_om.is_file() else "缺失")
    print("whisper_encoder.om:", whisper_om, "存在" if whisper_om.is_file() else "缺失")
    print("YOLO NPU 就绪:", can_use_yolo_npu(str(yolo_om)))

    if not is_ascend_available():
        print("\n提示: source /usr/local/Ascend/ascend-toolkit/set_env.sh")
    if not yolo_om.is_file():
        print("提示: bash scripts/convert_yolo_to_om.sh")
    if not whisper_om.is_file():
        print("提示: PC 运行 export_whisper_encoder_onnx.py，板端 convert_whisper_encoder_to_om.sh")

    ok = is_ascend_available() and yolo_om.is_file()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
