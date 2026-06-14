#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Atlas 200I 离线流水线（无 ROS）：
  语音 m4a/wav → Whisper + NLU → 目标类别
  → YOLO 检测 color_image → 深度采样 → camera_coord_m
  → 写入 grasp_target.json（供 grasp_from_offline_vision.py 使用）

【Atlas NPU 运行示例】
  cd ~/kuavi_robot_control
  source scripts/activate_kuavi_atlas.sh   # 必须：kuavi + CANN + acl

  python3 scripts/atlas_voice_grasp_pipeline.py \\
    --asr-config config/asr_atlas_npu.yaml \\
    --vision-config config/vision.yaml \\
    --device npu \\
    --audio instance/record5.m4a

【下位机抓取】（将 grasp_target.json 拷到机器人 scripts/ 后）
  python3 grasp_from_offline_vision.py --hand left --grasp-json grasp_target.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vision_lim.camera_info_parser import load_intrinsics_from_camera_info_files
from vision_lim.voice_pipeline import transcribe_then_parse
from vision_lim.yolo_detect import detect_target_yolo


def _log(msg: str) -> None:
    """打印带 flush 的流水线日志。"""
    print(msg, flush=True)


def _ensure_wav(audio_path: Path) -> Path:
    """m4a/mp3 等先转 16k 单声道 wav（需系统 ffmpeg）。"""
    if audio_path.suffix.lower() == ".wav":
        return audio_path

    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            f"音频为 {audio_path.suffix}，需要 ffmpeg 转 wav：sudo apt install ffmpeg"
        )

    out = audio_path.with_suffix(".wav")
    cmd = [
        "ffmpeg", "-y", "-i", str(audio_path),
        "-ar", "16000", "-ac", "1", "-sample_fmt", "s16",
        str(out),
    ]
    _log(f"[音频] 转换: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def depth_at(depth: np.ndarray, u: int, v: int, r: int = 4) -> float:
    """在 (u,v) 周围 r 像素邻域取有效深度中位数（与深度图单位一致）。"""
    vals: List[float] = []
    for du in range(-r, r + 1):
        for dv in range(-r, r + 1):
            uu, vv = u + du, v + dv
            if 0 <= vv < depth.shape[0] and 0 <= uu < depth.shape[1]:
                d = depth[vv, uu]
                if hasattr(d, "item"):
                    d = d.item()
                if float(d) > 0:
                    vals.append(float(d))
    return float(np.median(vals)) if vals else 0.0


def color_pixel_to_depth_pixel(
    u_c: int, v_c: int, color_ci: Dict, depth_di: Dict
) -> Tuple[int, int]:
    """彩色像素映射到深度图像素（按两相机主点 cx/cy 差值对齐）。"""
    u_d = int(round(u_c + (depth_di["cx"] - color_ci["cx"])))
    v_d = int(round(v_c + (depth_di["cy"] - color_ci["cy"])))
    return u_d, v_d


def sample_depth_mm(
    depth: np.ndarray,
    u_d0: int,
    v_d0: int,
    search_radius: int = 35,
) -> Tuple[float, int, int]:
    """在深度图邻域搜索有效深度（mm）。"""
    for dv in range(0, search_radius + 1, 2):
        for du in (-6, -3, 0, 3, 6):
            cand_u, cand_v = u_d0 + du, v_d0 + dv
            val = depth_at(depth, cand_u, cand_v, r=3)
            if val > 0:
                return val, cand_u, cand_v
    return 0.0, u_d0, v_d0


def camera_coord_from_pixels(
    u_d: int, v_d: int, depth_mm: float, depth_di: Dict
) -> Tuple[float, float, float]:
    """深度相机像素 + 深度(mm) → optical 系坐标 (m)。"""
    z = depth_mm / 1000.0
    x = (u_d - depth_di["cx"]) * z / depth_di["fx"]
    y = (v_d - depth_di["cy"]) * z / depth_di["fy"]
    return (x, y, z)


def grasp_pixel_from_bbox(
    x1: int, y1: int, x2: int, y2: int,
    vertical_ratio: float = 0.65,
) -> Tuple[int, int]:
    """边界框水平中心 + 垂直偏下（默认 65% 处）。"""
    u_c = int((x1 + x2) / 2)
    v_c = int(y1 + vertical_ratio * (y2 - y1))
    return u_c, v_c


def run_pipeline(
    audio_path: Path,
    color_path: Path,
    depth_path: Path,
    color_info_path: Path,
    depth_info_path: Path,
    output_path: Path,
    model_path: Path,
    asr_config: Optional[str],
    vision_config: Optional[str],
    device: str,
    vertical_ratio: float,
    text_override: Optional[str],
) -> Dict:
    """端到端离线流水线：语音解析 → YOLO 检测 → 深度采样 → 写出 grasp_target.json。"""
    # --- 1. 语音 → 任务 JSON ---
    if text_override:
        from vision_lim.semantic_parser import parse_instruction
        transcript = text_override.strip()
        task = parse_instruction(transcript)
        _log(f"[语音] 使用 --text 跳过 ASR: {transcript!r}")
    else:
        wav_path = _ensure_wav(audio_path)
        transcript, task = transcribe_then_parse(str(wav_path), config_path=asr_config)
        _log(f"[语音] ASR: {transcript}")
        if asr_config and "atlas_npu" in asr_config:
            _log("[语音] ASR 后端: 昇腾 NPU (encoder.om + CPU decode)")
    _log(f"[语音] 任务 JSON: {json.dumps(task, ensure_ascii=False)}")

    if task.get("action") == "stop":
        raise RuntimeError("语音指令为停止，不执行定位")
    target_class = task.get("target")
    if not target_class:
        raise RuntimeError(
            f"未能从语音解析目标物体，ASR={transcript!r}。"
            "请说「拿水瓶/拿瓶子」等，或改用 --text \"把瓶子拿起来\""
        )
    _log(f"[语音] 目标类别: {target_class}")

    # --- 2. 读图 ---
    color = cv2.imread(str(color_path))
    depth = cv2.imread(str(depth_path), cv2.IMREAD_UNCHANGED)
    if color is None:
        raise FileNotFoundError(f"无法读取彩色图: {color_path}")
    if depth is None:
        raise FileNotFoundError(f"无法读取深度图: {depth_path}")

    color_ci, depth_di = load_intrinsics_from_camera_info_files(
        str(color_info_path), str(depth_info_path)
    )

    # --- 3. YOLO 检测 ---
    detection, yolo_backend = detect_target_yolo(
        color,
        target_class,
        model_path=None if str(model_path) == "." else str(model_path),
        vision_config_path=vision_config,
        device=device,
    )
    _log(f"[YOLO] 推理设备: {yolo_backend.upper()}")
    if detection is None:
        raise RuntimeError(
            f"YOLO 未检测到 '{target_class}'。"
            "请确认模型为 COCO yolov8n，且画面中有该物体。"
        )
    _log(
        f"[YOLO] {detection['class_name']} conf={detection['confidence']:.3f} "
        f"bbox={detection['bbox']}"
    )

    x1, y1, x2, y2 = detection["bbox"]

    # --- 4. 深度采样 → camera_coord_m → JSON ---
    u_c, v_c = grasp_pixel_from_bbox(x1, y1, x2, y2, vertical_ratio=vertical_ratio)
    u_d0, v_d0 = color_pixel_to_depth_pixel(u_c, v_c, color_ci, depth_di)
    depth_mm, u_d, v_d = sample_depth_mm(depth, u_d0, v_d0)
    if depth_mm <= 0:
        raise RuntimeError(
            f"深度无效，color=({u_c},{v_c}) depth=({u_d0},{v_d0}) 邻域无有效值"
        )

    cam = camera_coord_from_pixels(u_d, v_d, depth_mm, depth_di)
    z_m = depth_mm / 1000.0

    grasp_json = {
        "voice_transcript": transcript,
        "voice_task": task,
        "yolo_backend": yolo_backend,
        "detection_confidence": round(detection["confidence"], 4),
        "bbox_color": detection["bbox"],
        "pixel_color": [u_c, v_c],
        "pixel_depth": [u_d, v_d],
        "depth_m": round(z_m, 4),
        "camera_coord_m": [round(cam[0], 4), round(cam[1], 4), round(cam[2], 4)],
        "color_intrinsics": color_ci,
        "depth_intrinsics": depth_di,
        "note": (
            f"Atlas pipeline (ASR+NPU/CPU, YOLO={yolo_backend}): "
            f"{target_class} → camera_coord_m; vertical_ratio={vertical_ratio}"
        ),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(grasp_json, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    scripts_copy = ROOT / "scripts" / "grasp_target.json"
    if output_path.resolve() != scripts_copy.resolve():
        scripts_copy.write_text(output_path.read_text(encoding="utf-8"), encoding="utf-8")

    _log(f"[坐标] pixel_color=({u_c}, {v_c}) pixel_depth=({u_d}, {v_d})")
    _log(f"[坐标] camera_coord_m=({cam[0]:.4f}, {cam[1]:.4f}, {cam[2]:.4f})")
    _log(f"[输出] {output_path}")
    _log(f"[输出] {scripts_copy}")
    _log("[完成] 可将 grasp_target.json 拷到下位机，运行:")
    _log("       python3 grasp_from_offline_vision.py --hand left --grasp-json grasp_target.json")
    return grasp_json


def main() -> int:
    instance = ROOT / "instance"
    parser = argparse.ArgumentParser(
        description="Atlas: 语音 + YOLO + 深度 → grasp_target.json"
    )
    parser.add_argument("--audio", default=str(instance / "record1.m4a"))
    parser.add_argument("--color", default=str(instance / "color_image.png"))
    parser.add_argument("--depth", default=str(instance / "depth_image.png"))
    parser.add_argument("--camera-info-color", default=str(instance / "camera_info.txt"))
    parser.add_argument("--camera-info-depth", default=str(instance / "camera_info1.txt"))
    parser.add_argument(
        "--model", default=None,
        help="YOLO 模型路径（.om 或 .pt；默认读 config/vision.yaml）",
    )
    parser.add_argument(
        "--output", default=str(instance / "grasp_target.json"),
        help="输出 grasp_target.json",
    )
    parser.add_argument("--asr-config", default=None, help="ASR 配置，NPU 用 config/asr_atlas_npu.yaml")
    parser.add_argument(
        "--vision-config", default=None, help="视觉配置，默认 config/vision.yaml",
    )
    parser.add_argument(
        "--device", default="auto", choices=["auto", "npu", "cpu"],
        help="推理设备：auto=有 .om 且 acl 可用则用 NPU，否则 CPU",
    )
    parser.add_argument(
        "--vertical-ratio", type=float, default=0.65,
        help="抓取点在检测框内的垂直比例（0=顶，1=底，默认0.65偏下）",
    )
    parser.add_argument(
        "--text", default=None,
        help="跳过 Whisper，直接用该中文指令测 NLU+视觉",
    )
    args = parser.parse_args()

    use_npu = args.device in ("npu", "auto") or (
        args.asr_config and "atlas_npu" in str(args.asr_config)
    )
    if use_npu:
        from vision_lim.ascend import is_ascend_available

        if not is_ascend_available():
            _log(
                "[错误] NPU 模式需要 acl 模块。请先执行:\n"
                "       source scripts/activate_kuavi_atlas.sh"
            )
            return 1

    try:
        run_pipeline(
            audio_path=Path(args.audio),
            color_path=Path(args.color),
            depth_path=Path(args.depth),
            color_info_path=Path(args.camera_info_color),
            depth_info_path=Path(args.camera_info_depth),
            output_path=Path(args.output),
            model_path=Path(args.model) if args.model else Path("."),
            asr_config=args.asr_config,
            vision_config=args.vision_config,
            device=args.device,
            vertical_ratio=args.vertical_ratio,
            text_override=args.text,
        )
        return 0
    except Exception as e:
        import traceback
        traceback.print_exc()
        _log(f"[错误] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
