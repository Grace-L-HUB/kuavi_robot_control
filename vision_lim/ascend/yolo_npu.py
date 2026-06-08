"""昇腾 NPU 上的 YOLOv8n 检测。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from .om_infer import OmModel, default_om_path, is_ascend_available
from .yolo_postprocess import (
    best_detection_for_class,
    postprocess_yolov8,
    preprocess_bgr,
)

logger = logging.getLogger(__name__)

_model_cache: Dict[str, "YoloNpuDetector"] = {}


class YoloNpuDetector:
    """YOLOv8 .om 在昇腾 NPU 上推理。"""

    def __init__(
        self,
        model_path: str,
        device_id: int = 0,
        conf_threshold: float = 0.35,
        iou_threshold: float = 0.45,
    ):
        self.model_path = str(Path(model_path).resolve())
        self.device_id = device_id
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self._om: Optional[OmModel] = None

    def _ensure_model(self) -> OmModel:
        if self._om is None:
            self._om = OmModel(self.model_path, device_id=self.device_id)
            self._om.load()
        return self._om

    def detect(self, color_bgr: np.ndarray) -> List[Dict]:
        blob, orig_hw = preprocess_bgr(color_bgr)
        outputs = self._ensure_model().infer([blob])
        return postprocess_yolov8(
            outputs[0],
            orig_hw,
            conf_threshold=self.conf_threshold,
            iou_threshold=self.iou_threshold,
        )

    def detect_target(
        self,
        color_bgr: np.ndarray,
        target_class: str,
    ) -> Optional[Dict]:
        dets = self.detect(color_bgr)
        return best_detection_for_class(dets, target_class)

    def release(self) -> None:
        if self._om is not None:
            self._om.release()
            self._om = None


def get_yolo_npu_detector(
    model_path: Optional[str] = None,
    device_id: int = 0,
    conf_threshold: float = 0.35,
    iou_threshold: float = 0.45,
) -> YoloNpuDetector:
    path = model_path or str(default_om_path("yolov8n.om"))
    key = f"{path}|{device_id}|{conf_threshold}|{iou_threshold}"
    if key not in _model_cache:
        _model_cache[key] = YoloNpuDetector(
            path, device_id, conf_threshold, iou_threshold
        )
    return _model_cache[key]


def can_use_yolo_npu(model_path: Optional[str] = None) -> bool:
    path = Path(model_path or default_om_path("yolov8n.om"))
    return is_ascend_available() and path.is_file()
