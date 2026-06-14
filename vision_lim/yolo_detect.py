"""统一 YOLO 检测入口：自动选择 NPU (.om) 或 CPU (ultralytics .pt)。"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from .ascend import can_use_yolo_npu, get_yolo_npu_detector
from .target_synonyms import matches_target_class
from .vision_config import load_vision_config, resolve_yolo_backend


def detect_target_yolo(
    color_bgr,
    target_class: str,
    *,
    model_path: Optional[str] = None,
    vision_config_path: Optional[str] = None,
    device: str = "auto",
    conf_threshold: Optional[float] = None,
    iou_threshold: Optional[float] = None,
) -> tuple[Optional[Dict], str]:
    """
    检测目标类别，返回 (detection_dict | None, backend_label)。
    backend_label 为 "npu" 或 "cpu"。
    """
    cfg = load_vision_config(vision_config_path)
    yolo_cfg = resolve_yolo_backend(cfg, device_override=device, model_override=model_path)
    conf = conf_threshold if conf_threshold is not None else yolo_cfg["conf_threshold"]
    iou = iou_threshold if iou_threshold is not None else yolo_cfg["iou_threshold"]
    backend = yolo_cfg["backend"]

    want_npu = backend in ("npu", "ascend_om", "ascend")
    if backend == "auto":
        want_npu = can_use_yolo_npu(yolo_cfg["model_path"])

    if want_npu and can_use_yolo_npu(yolo_cfg["model_path"]):
        detector = get_yolo_npu_detector(
            yolo_cfg["model_path"],
            device_id=yolo_cfg["device_id"],
            conf_threshold=conf,
            iou_threshold=iou,
        )
        det = detector.detect_target(color_bgr, target_class)
        return det, "npu"

    return _detect_ultralytics(
        color_bgr,
        target_class,
        Path(yolo_cfg["fallback_model_path"]),
        conf,
        iou,
    ), "cpu"


def _bbox_to_detection(
    class_name: str,
    confidence: float,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
) -> Dict:
    """将单框检测结果转为统一字典格式。"""
    u, v = int((x1 + x2) / 2), int((y1 + y2) / 2)
    return {
        "class_name": class_name,
        "confidence": confidence,
        "bbox": [x1, y1, x2, y2],
        "bbox_center": [u, v],
    }


def _detect_ultralytics(
    color_bgr,
    target_class: str,
    model_path: Path,
    conf_threshold: float,
    iou_threshold: float,
) -> Optional[Dict]:
    """CPU 回退：ultralytics YOLO，返回置信度最高的同义匹配框。"""
    try:
        from ultralytics import YOLO
    except ImportError as e:
        raise ImportError("请安装 ultralytics: pip install ultralytics") from e

    if not model_path.is_file():
        raise FileNotFoundError(
            f"未找到 YOLO 模型: {model_path}\n"
            "NPU 模式需 ascend_models/yolov8n.om；CPU 回退需 yolov8n.pt"
        )

    model = YOLO(str(model_path))
    results = model(color_bgr, conf=conf_threshold, iou=iou_threshold, verbose=False)
    if not results:
        return None

    result = results[0]
    names = result.names or {}
    best = None
    boxes = result.boxes
    if boxes is None:
        return None

    for box in boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        class_name = str(names.get(cls_id, f"class_{cls_id}")).lower()
        if not matches_target_class(class_name, target_class):
            continue
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        det = _bbox_to_detection(class_name, conf, x1, y1, x2, y2)
        if best is None or conf > best["confidence"]:
            best = det
    return best
