"""昇腾 NPU 推理模块。"""

from .om_infer import OmModel, default_om_path, is_ascend_available
from .yolo_npu import YoloNpuDetector, can_use_yolo_npu, get_yolo_npu_detector
from .yolo_postprocess import best_detection_for_class, postprocess_yolov8, preprocess_bgr

__all__ = [
    "OmModel",
    "YoloNpuDetector",
    "best_detection_for_class",
    "can_use_yolo_npu",
    "default_om_path",
    "get_yolo_npu_detector",
    "is_ascend_available",
    "postprocess_yolov8",
    "preprocess_bgr",
]
