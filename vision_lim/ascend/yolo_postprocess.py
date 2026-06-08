"""YOLOv8 预处理、NMS 后处理（OM / ONNX 通用）。"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from .coco_names import COCO80

INPUT_SIZE = (640, 640)


def preprocess_bgr(image: np.ndarray) -> Tuple[np.ndarray, Tuple[int, int]]:
    """BGR 图像 → NCHW float32 blob，返回 (1,3,640,640) 与原图 (h,w)。"""
    h_orig, w_orig = image.shape[:2]
    resized = cv2.resize(image, INPUT_SIZE)
    blob = resized.astype(np.float32) / 255.0
    blob = np.transpose(blob, (2, 0, 1))
    blob = np.expand_dims(blob, axis=0)
    return np.ascontiguousarray(blob), (h_orig, w_orig)


def _nms_xyxy(
    boxes: np.ndarray,
    scores: np.ndarray,
    iou_threshold: float,
) -> List[int]:
    if boxes.size == 0:
        return []
    x1, y1, x2, y2 = boxes.T
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    keep: List[int] = []
    while order.size > 0:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        order = order[1:][iou <= iou_threshold]
    return keep


def postprocess_yolov8(
    output: np.ndarray,
    orig_hw: Tuple[int, int],
    *,
    conf_threshold: float = 0.35,
    iou_threshold: float = 0.45,
    class_names: Optional[Tuple[str, ...]] = None,
) -> List[Dict]:
    """
    解析 YOLOv8 原始输出 (1,84,8400) 或 (1,8400,84)，返回检测 dict 列表。
    """
    h_orig, w_orig = orig_hw
    names = class_names or COCO80

    out = output
    if not isinstance(out, np.ndarray):
        raise TypeError(f"YOLO 输出必须是 numpy.ndarray，实际为 {type(out)!r}")
    if out.ndim == 3:
        if out.shape[1] == 84 or out.shape[1] == 4 + len(names):
            out = np.transpose(out, (0, 2, 1))
        preds = out[0]
    elif out.ndim == 2:
        preds = out
    else:
        return []

    boxes_raw: List[List[float]] = []
    scores_raw: List[float] = []
    cls_raw: List[int] = []

    for det in preds:
        cx, cy, w, h = det[:4]
        class_scores = det[4:]
        if class_scores.size == 0:
            continue
        score = float(np.max(class_scores))
        if score < conf_threshold:
            continue
        cls_id = int(np.argmax(class_scores))
        x1 = (cx - w / 2) * w_orig / INPUT_SIZE[0]
        y1 = (cy - h / 2) * h_orig / INPUT_SIZE[1]
        x2 = (cx + w / 2) * w_orig / INPUT_SIZE[0]
        y2 = (cy + h / 2) * h_orig / INPUT_SIZE[1]
        boxes_raw.append([x1, y1, x2, y2])
        scores_raw.append(score)
        cls_raw.append(cls_id)

    if not boxes_raw:
        return []

    boxes_np = np.array(boxes_raw, dtype=np.float32)
    scores_np = np.array(scores_raw, dtype=np.float32)
    keep = _nms_xyxy(boxes_np, scores_np, iou_threshold)

    results: List[Dict] = []
    for idx in keep:
        x1, y1, x2, y2 = boxes_np[idx]
        x1, y1 = max(0, int(x1)), max(0, int(y1))
        x2, y2 = min(w_orig, int(x2)), min(h_orig, int(y2))
        cls_id = cls_raw[idx]
        class_name = names[cls_id] if cls_id < len(names) else f"class_{cls_id}"
        u, v = int((x1 + x2) / 2), int((y1 + y2) / 2)
        results.append(
            {
                "class_name": class_name.lower(),
                "class_id": cls_id,
                "confidence": float(scores_np[idx]),
                "bbox": [x1, y1, x2, y2],
                "bbox_center": [u, v],
            }
        )
    return results


def best_detection_for_class(
    detections: List[Dict],
    target_class: str,
) -> Optional[Dict]:
    target = target_class.lower().strip()
    best = None
    for det in detections:
        if det["class_name"] != target:
            continue
        if best is None or det["confidence"] > best["confidence"]:
            best = det
    return best
