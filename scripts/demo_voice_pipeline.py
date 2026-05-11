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
from vision_lim.voice_pipeline import record_then_parse, transcribe_then_parse  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="语音/文本 -> 任务 JSON（wav 走 speech_file_to_json）")
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
        "--record",
        action="store_true",
        help="从麦克风录制（默认 5s）后再识别；依赖 sounddevice",
    )
    p.add_argument(
        "--seconds",
        type=float,
        default=5.0,
        help="录制时长（秒），配合 --record",
    )
    p.add_argument(
        "-o",
        "--output",
        help="录制 wav 保存路径；省略则使用临时文件（不保留）",
    )
    p.add_argument(
        "--device",
        type=int,
        default=None,
        help="麦克风设备编号（默认系统默认）；可用 python -m sounddevice 列出",
    )
    p.add_argument(
        "--config",
        dest="config_path",
        help="覆盖默认 config/asr.yaml",
    )
    args = p.parse_args()

    if args.record:
        print(f"开始录制 {args.seconds} 秒，请对着麦克风说话…")
        transcript, result = record_then_parse(
            duration_sec=args.seconds,
            wav_path=args.output,
            config_path=args.config_path,
            device=args.device,
        )
        if args.output:
            print("已保存:", args.output)
        print("ASR:", transcript)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.text is not None:
        text = args.text.strip()
        result = parse_instruction(text)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.audio:
        transcript, result = transcribe_then_parse(args.audio, config_path=args.config_path)
        print("ASR:", transcript)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        p.print_help()
        print("\n示例: python scripts/demo_voice_pipeline.py --text \"递给我蓝色的球\"")
        print("       python scripts/demo_voice_pipeline.py samples/demo.wav")
        print("       python scripts/demo_voice_pipeline.py --record -o samples/last.wav")
        print("\n代码调用: from vision_lim import speech_file_to_json")
        print("           task = speech_file_to_json(\"samples/demo.wav\")")
        sys.exit(1)


if __name__ == "__main__":
    main()
