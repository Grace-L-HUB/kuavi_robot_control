#!/usr/bin/env python3
"""快速测试 .om 能否在 NPU 上推理（Whisper encoder / YOLO）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np


def main() -> int:
    from vision_lim.ascend.om_infer import OmModel, default_om_path, is_ascend_available

    if not is_ascend_available():
        print("acl 不可用，请先: source scripts/activate_kuavi_atlas.sh")
        return 1

    whisper = default_om_path("whisper_encoder.om")
    yolo = default_om_path("yolov8n.om")

    if whisper.is_file():
        print("==> Whisper encoder.om")
        m = OmModel(str(whisper))
        mel = np.random.randn(1, 80, 3000).astype(np.float32)
        out = m.infer([mel])
        print("    OK output shapes:", [o.shape for o in out])
        m.release()

    if yolo.is_file():
        print("==> YOLOv8n.om")
        m = OmModel(str(yolo))
        img = np.random.rand(1, 3, 640, 640).astype(np.float32)
        out = m.infer([img])
        print("    OK output shapes:", [o.shape for o in out])
        m.release()

    print("[完成] OM 推理测试通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
