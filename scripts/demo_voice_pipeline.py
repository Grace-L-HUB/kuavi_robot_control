#!/usr/bin/env python3
"""演示：音频文件 -> ASR 文本 -> NLU JSON。需在仓库根目录执行或设置 PYTHONPATH。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from vision_lim.semantic_parser import parse_instruction  # noqa: E402
from vision_lim.speech_recognition import transcribe_file  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="wav -> Whisper -> parse_instruction -> JSON")
    p.add_argument(
        "audio",
        nargs="?",
        help="音频文件路径；省略则仅用 --text 演示 NLU",
    )
    p.add_argument(
        "--text",
        help="跳过 ASR，直接对该字符串做语义解析（便于无 wav 时调试 NLU）",
    )
    p.add_argument(
        "--config",
        dest="config_path",
        help="覆盖默认 config/asr.yaml",
    )
    args = p.parse_args()

    if args.text is not None:
        text = args.text.strip()
    elif args.audio:
        text = transcribe_file(args.audio, config_path=args.config_path)
        print("ASR:", text)
    else:
        p.print_help()
        print("\n示例: python scripts/demo_voice_pipeline.py --text \"递给我蓝色的球\"")
        print("       python scripts/demo_voice_pipeline.py samples/demo.wav")
        sys.exit(1)

    result = parse_instruction(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
