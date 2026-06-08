"""读取 config/vision.yaml 并解析 YOLO 后端。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

_DEFAULT_VISION = "vision.yaml"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_vision_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    if config_path:
        path = Path(config_path).expanduser().resolve()
    else:
        path = _repo_root() / "config" / _DEFAULT_VISION
    if not path.is_file():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_yolo_backend(
    cfg: Dict[str, Any],
    *,
    device_override: Optional[str] = None,
    model_override: Optional[str] = None,
) -> Dict[str, Any]:
    """返回 {backend, model_path, fallback_model_path, device_id, conf, iou}。"""
    vision = cfg.get("vision") or {}
    yolo = vision.get("yolo") or {}
    backend = (device_override or vision.get("backend") or "auto").strip().lower()

    repo = _repo_root()
    model_path = model_override or yolo.get("model_path") or "ascend_models/yolov8n.om"
    fallback = yolo.get("fallback_model_path") or "ascend_models/yolov8n.pt"
    if not Path(model_path).is_absolute():
        model_path = str((repo / model_path).resolve())
    if not Path(fallback).is_absolute():
        fallback = str((repo / fallback).resolve())

    return {
        "backend": backend,
        "model_path": model_path,
        "fallback_model_path": fallback,
        "device_id": int(yolo.get("device_id") or 0),
        "conf_threshold": float(yolo.get("conf_threshold") or 0.35),
        "iou_threshold": float(yolo.get("iou_threshold") or 0.45),
    }
