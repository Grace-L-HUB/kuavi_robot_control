"""视觉与语言推理模块（语音、检测、坐标变换等）。"""

from .audio_record import record_wav_file
from .semantic_parser import parse_instruction
from .speech_recognition import transcribe_file
from .voice_pipeline import (
    normalize_asr_text,
    record_speech_to_json,
    record_then_parse,
    speech_file_to_json,
    transcribe_then_parse,
)

# 新的视觉感知模块
from .detection import (
    Detection,
    ObjectDetectionNode,
    YOLODetector,
    detect_objects,
)
from .depth_processor import (
    DepthProcessor,
    SynchronizedSensorNode,
    get_reliable_depth,
    depth_to_pointcloud,
)
from .coordinate_transform import (
    CoordinateTransformer,
    TargetPosition,
    compute_target_position,
    load_intrinsics_from_yaml,
    pixel_to_camera_coord,
    camera_to_arm_base,
)
from .vision_pipeline import (
    VisionPipeline,
    VoiceCommand,
    TargetResult,
    GraspPlanner,
    locate_object_from_voice,
    locate_object_from_audio,
)

__all__ = [
    # 原有的语音模块
    "normalize_asr_text",
    "parse_instruction",
    "record_speech_to_json",
    "record_then_parse",
    "record_wav_file",
    "speech_file_to_json",
    "transcribe_file",
    "transcribe_then_parse",
    # 新的检测模块
    "Detection",
    "ObjectDetectionNode",
    "YOLODetector",
    "detect_objects",
    # 新的深度处理模块
    "DepthProcessor",
    "SynchronizedSensorNode",
    "get_reliable_depth",
    "depth_to_pointcloud",
    # 新的坐标变换模块
    "CoordinateTransformer",
    "TargetPosition",
    "compute_target_position",
    "load_intrinsics_from_yaml",
    "pixel_to_camera_coord",
    "camera_to_arm_base",
    # 新的流水线模块
    "VisionPipeline",
    "VoiceCommand",
    "TargetResult",
    "GraspPlanner",
    "locate_object_from_voice",
    "locate_object_from_audio",
]
