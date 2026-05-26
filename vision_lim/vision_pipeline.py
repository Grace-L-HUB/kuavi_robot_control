"""
视觉感知流水线：整合语音识别 + YOLO目标检测 + 深度坐标计算

用户通过语音指定目标物体，系统通过摄像头定位目标并返回3D坐标，
供机器人进行移动和抓取的后续操作。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ROS相关导入（可选）
ROS_AVAILABLE = False
try:
    import rospy
    ROS_AVAILABLE = True
except ImportError:
    pass

# 导入视觉模块
try:
    from .detection import (
        Detection,
        ObjectDetectionNode,
        YOLODetector,
    )
    from .depth_processor import (
        DepthProcessor,
        SynchronizedSensorNode,
        get_reliable_depth,
    )
    from .coordinate_transform import (
        CoordinateTransformer,
        TargetPosition,
        compute_target_position,
        load_intrinsics_from_yaml,
    )
    from .semantic_parser import parse_instruction
    from .speech_recognition import transcribe_file
    VISION_MODULES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Some vision modules not available: {e}")
    VISION_MODULES_AVAILABLE = False


@dataclass
class VoiceCommand:
    """语音指令解析结果"""
    action: str           # 动作类型（fetch, stop, unknown）
    target: str           # 目标物体类别
    attribute: str        # 属性（颜色等）
    raw_text: str        # 原始语音文本

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "target": self.target,
            "attribute": self.attribute,
            "raw_text": self.raw_text,
        }


@dataclass
class TargetResult:
    """目标定位结果"""
    target: TargetPosition  # 目标位置信息
    command: VoiceCommand    # 对应的语音指令
    timestamp: float        # 时间戳

    def to_dict(self) -> dict:
        return {
            "target": self.target.to_dict(),
            "command": self.command.to_dict(),
            "timestamp": self.timestamp,
        }


class VisionPipeline:
    """
    视觉感知流水线

    整合语音识别、目标检测、深度处理和坐标变换，
    实现"语音指定目标 -> 视觉定位 -> 返回3D坐标"的功能。
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        model_path: str = "ascend_models/yolov8n.pt",
        color_topic: str = "/camera_1/color/image_raw",
        depth_topic: str = "/camera_1/depth/image_rect_raw",
        conf_threshold: float = 0.5,
        device: str = "auto",
        target_classes: Optional[List[str]] = None,
    ):
        """
        初始化视觉感知流水线

        Args:
            config_path: 配置文件路径（包含相机内参等）
            model_path: YOLO模型路径
            color_topic: 彩色图像ROS话题
            depth_topic: 深度图像ROS话题
            conf_threshold: 目标检测置信度阈值
            device: 推理设备
            target_classes: 目标类别列表
        """
        self.config_path = config_path
        self.model_path = model_path
        self.color_topic = color_topic
        self.depth_topic = depth_topic
        self.conf_threshold = conf_threshold
        self.device = device
        self.target_classes = target_classes or ["cup", "bottle", "ball", "phone", "box"]

        # 初始化组件
        self._detector: Optional[ObjectDetectionNode] = None
        self._depth_processor: Optional[DepthProcessor] = None
        self._sensor_sync: Optional[SynchronizedSensorNode] = None
        self._transformer: Optional[CoordinateTransformer] = None

        self._initialized = False

    def initialize(self) -> bool:
        """
        初始化所有组件

        Returns:
            bool: 初始化是否成功
        """
        if self._initialized:
            return True

        if not VISION_MODULES_AVAILABLE:
            logger.error("Vision modules not available")
            return False

        try:
            # 初始化坐标变换器
            if self.config_path:
                self._transformer = CoordinateTransformer(config_path=self.config_path)
            else:
                self._transformer = CoordinateTransformer()

            # 初始化目标检测节点
            self._detector = ObjectDetectionNode(
                model_path=self.model_path,
                color_topic=self.color_topic,
                conf_threshold=self.conf_threshold,
                device=self.device,
                classes=self.target_classes,
            )
            if not self._detector.initialize():
                logger.error("Failed to initialize detector")
                return False

            # 初始化深度处理器
            self._depth_processor = DepthProcessor(depth_topic=self.depth_topic)
            self._depth_processor.start()

            # 初始化同步传感器节点
            self._sensor_sync = SynchronizedSensorNode(
                color_topic=self.color_topic,
                depth_topic=self.depth_topic,
            )
            self._sensor_sync.start()

            self._initialized = True
            logger.info("VisionPipeline initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize VisionPipeline: {e}")
            return False

    def parse_voice_command(self, text: str) -> VoiceCommand:
        """
        解析语音指令

        Args:
            text: 语音识别文本

        Returns:
            VoiceCommand对象
        """
        parsed = parse_instruction(text)
        return VoiceCommand(
            action=parsed.get("action", "unknown"),
            target=parsed.get("target"),
            attribute=parsed.get("attribute"),
            raw_text=text,
        )

    def transcribe_audio(self, audio_path: str) -> str:
        """
        将音频文件转写为文本

        Args:
            audio_path: 音频文件路径

        Returns:
            识别的文本
        """
        try:
            text = transcribe_file(audio_path)
            logger.info(f"Transcribed: {text}")
            return text
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return ""

    def detect_and_locate(
        self,
        target_class: str,
        attribute: Optional[str] = None,
        timeout: float = 10.0,
    ) -> Optional[TargetResult]:
        """
        检测并定位目标物体

        Args:
            target_class: 目标物体类别
            attribute: 目标属性（用于颜色筛选）
            timeout: 超时时间（秒）

        Returns:
            TargetResult对象，如果未找到目标返回None
        """
        if not self._initialized:
            self.initialize()

        start_time = time.time()
        last_detection = None

        while (time.time() - start_time) < timeout:
            # 获取同步的彩色图和深度图
            color_img, depth_img, stamp = self._sensor_sync.get_synchronized_frames(timeout=1.0)

            if color_img is None or depth_img is None:
                logger.warning("No synchronized frames received")
                continue

            # 目标检测
            detections = self._detector.detect_once(color_img)

            # 筛选目标类别
            matching = [
                d for d in detections
                if d.class_name.lower() == target_class.lower()
            ]

            if not matching:
                logger.debug(f"No {target_class} detected in this frame")
                continue

            # 选择置信度最高的检测
            best_detection = max(matching, key=lambda d: d.confidence)
            u, v = best_detection.bbox_center

            # 获取深度值
            depth_m = get_reliable_depth(depth_img, u, v)

            if depth_m is None:
                logger.warning(f"Invalid depth at ({u}, {v})")
                continue

            # 计算3D坐标
            target_pos = compute_target_position(
                detection=best_detection,
                depth_m=depth_m,
                transformer=self._transformer,
            )

            logger.info(f"Located {target_class} at arm coords: {target_pos.arm_coord}")
            last_detection = target_pos

            # 找到目标后立即返回
            return TargetResult(
                target=target_pos,
                command=VoiceCommand(
                    action="fetch",
                    target=target_class,
                    attribute=attribute,
                    raw_text="",
                ),
                timestamp=time.time(),
            )

        if last_detection is not None:
            # 超时但有历史检测结果
            logger.warning(f"Timeout, returning last known position")
            return TargetResult(
                target=last_detection,
                command=VoiceCommand(
                    action="fetch",
                    target=target_class,
                    attribute=attribute,
                    raw_text="",
                ),
                timestamp=time.time(),
            )

        logger.warning(f"Target {target_class} not found within {timeout}s")
        return None

    def locate_target_from_voice(
        self,
        text: str,
        timeout: float = 10.0,
    ) -> Optional[TargetResult]:
        """
        从语音指令定位目标物体

        这是主要的入口函数，用户说"把红色的杯子拿给我"这类指令，
        系统会识别出目标是"杯子"，然后进行定位。

        Args:
            text: 语音识别文本
            timeout: 超时时间

        Returns:
            TargetResult对象，如果未找到目标返回None
        """
        if not self._initialized:
            self.initialize()

        # 解析语音指令
        command = self.parse_voice_command(text)

        if command.action == "stop":
            logger.info("Stop command received")
            return None

        if command.target is None:
            logger.warning(f"Could not parse target from: {text}")
            return None

        logger.info(f"Looking for target: {command.target}, attribute: {command.attribute}")

        # 检测并定位目标
        result = self.detect_and_locate(
            target_class=command.target,
            attribute=command.attribute,
            timeout=timeout,
        )

        if result is not None:
            result.command = command

        return result

    def locate_target_from_audio(
        self,
        audio_path: str,
        timeout: float = 10.0,
    ) -> Optional[TargetResult]:
        """
        从音频文件定位目标物体

        Args:
            audio_path: 音频文件路径
            timeout: 超时时间

        Returns:
            TargetResult对象
        """
        # 转写音频
        text = self.transcribe_audio(audio_path)
        if not text:
            return None

        # 定位目标
        return self.locate_target_from_voice(text, timeout)

    def get_arm_coordinates(self, result: TargetResult) -> Tuple[float, float, float]:
        """
        从定位结果中提取机械臂坐标

        Args:
            result: 定位结果

        Returns:
            (x, y, z) 机械臂基座坐标系下的坐标
        """
        return result.target.arm_coord

    def shutdown(self):
        """关闭流水线，释放资源"""
        if self._depth_processor:
            self._depth_processor.stop()
        if self._sensor_sync:
            self._sensor_sync.stop()
        logger.info("VisionPipeline shutdown")


class GraspPlanner:
    """
    抓取规划器（基于目标位置）

    接收视觉定位结果，规划机械臂抓取路径。
    注意：实际抓取执行由 robot_control 模块负责。
    """

    def __init__(self, transformer: Optional[CoordinateTransformer] = None):
        self._transformer = transformer or CoordinateTransformer()

        # 抓取参数（根据实际机器人调整）
        self.pre_grasp_offset = 0.15   # 预抓取高度偏移（米）
        self.grasp_depth_offset = 0.05 # 抓取深度偏移（米）

    def plan_grasp_pose(
        self,
        target_pos: Tuple[float, float, float],
        hand: str = "right",
    ) -> Dict[str, Any]:
        """
        规划抓取姿态

        Args:
            target_pos: 目标在机械臂基座坐标系下的位置 (x, y, z)
            hand: 使用的机械臂 ("left" 或 "right")

        Returns:
            包含抓取规划的字典
        """
        x, y, z = target_pos

        # 预抓取位置（在目标上方）
        pre_grasp_pos = (x, y, z + self.pre_grasp_offset)

        # 实际抓取位置（目标位置减去一定深度）
        grasp_pos = (x, y, z + self.grasp_depth_offset)

        # 默认抓取姿态（掌心朝下）
        grasp_quat = [0.0, -0.70682518, 0.0, 0.70738827]

        return {
            "hand": hand,
            "pre_grasp": {
                "position": pre_grasp_pos,
                "orientation": grasp_quat,
            },
            "grasp": {
                "position": grasp_pos,
                "orientation": grasp_quat,
            },
            "retreat": {
                "position": pre_grasp_pos,
                "orientation": grasp_quat,
            },
        }

    def compute_ik_for_grasp(
        self,
        target_pos: Tuple[float, float, float],
        hand: str = "right",
    ) -> Optional[List[float]]:
        """
        计算IK获取关节角度

        Args:
            target_pos: 目标位置
            hand: 使用的机械臂

        Returns:
            14个关节角度，或None（需要robot_control模块配合）
        """
        # 此功能需要导入ArmController
        try:
            from ..robot_control.src.control.arm_controller import ArmController

            arm_ctrl = ArmController()
            quat = [0.0, -0.70682518, 0.0, 0.70738827]

            if hand == "left":
                return arm_ctrl.solve_ik(left_pos=list(target_pos), left_quat=quat)
            else:
                return arm_ctrl.solve_ik(right_pos=list(target_pos), right_quat=quat)

        except ImportError:
            logger.warning("ArmController not available, returning None")
            return None
        except Exception as e:
            logger.error(f"IK computation failed: {e}")
            return None


# 便捷函数
def locate_object_from_voice(
    text: str,
    config_path: Optional[str] = None,
    model_path: str = "ascend_models/yolov8n.pt",
    timeout: float = 10.0,
) -> Optional[Dict[str, Any]]:
    """
    便捷函数：从语音指令定位目标物体

    Args:
        text: 语音识别文本
        config_path: 配置文件路径
        model_path: YOLO模型路径
        timeout: 超时时间

    Returns:
        包含目标位置的字典，或None
    """
    pipeline = VisionPipeline(config_path=config_path, model_path=model_path)
    result = pipeline.locate_target_from_voice(text, timeout)

    if result is None:
        return None

    return result.to_dict()


def locate_object_from_audio(
    audio_path: str,
    config_path: Optional[str] = None,
    model_path: str = "ascend_models/yolov8n.pt",
    timeout: float = 10.0,
) -> Optional[Dict[str, Any]]:
    """
    便捷函数：从音频文件定位目标物体

    Args:
        audio_path: 音频文件路径
        config_path: 配置文件路径
        model_path: YOLO模型路径
        timeout: 超时时间

    Returns:
        包含目标位置的字典，或None
    """
    pipeline = VisionPipeline(config_path=config_path, model_path=model_path)
    result = pipeline.locate_target_from_audio(audio_path, timeout)

    if result is None:
        return None

    return result.to_dict()
