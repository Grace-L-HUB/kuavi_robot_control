"""YOLO目标检测模块：订阅ROS彩色图像话题，进行目标检测。"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ROS相关导入（可选，运行时检查）
ROS_AVAILABLE = False
try:
    import rospy
    from sensor_msgs.msg import Image
    from cv_bridge import CvBridge
    ROS_AVAILABLE = True
except ImportError:
    pass

# YOLO相关导入（可选）
YOLO_AVAILABLE = False
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    pass

# ONNX Runtime（昇腾/PC通用推理后端）
ONNXRUNTIME_AVAILABLE = False
try:
    import onnxruntime as ort
    ONNXRUNTIME_AVAILABLE = True
except ImportError:
    pass


@dataclass
class Detection:
    """检测结果数据结构"""
    class_name: str           # 物体类别（如"cup", "bottle"）
    confidence: float        # 置信度 (0-1)
    bbox_center: Tuple[int, int]  # 边界框中心像素坐标 (u, v)
    bbox: Tuple[int, int, int, int]  # 边界框 (x1, y1, x2, y2)

    def to_dict(self) -> dict:
        return {
            "class_name": self.class_name,
            "confidence": float(self.confidence),
            "bbox_center": self.bbox_center,
            "bbox": self.bbox,
        }


class YOLODetector:
    """YOLO目标检测器，支持多种推理后端"""

    def __init__(
        self,
        model_path: str = "ascend_models/yolov8n.pt",
        conf_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        device: str = "auto",
        classes: Optional[List[str]] = None,
    ):
        """
        初始化YOLO检测器

        Args:
            model_path: 模型文件路径（.pt或.onnx格式）
            conf_threshold: 置信度阈值
            iou_threshold: NMS IoU阈值
            device: 推理设备 ("auto", "cuda", "cpu", "mlu")
            classes: 目标类别列表，用于映射类别索引到名称
        """
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.classes = classes or []

        self._model = None
        self._session = None  # ONNX Runtime session
        self._npu_detector = None  # 昇腾 .om
        self._input_shape = (640, 640)  # YOLOv8默认输入尺寸
        self._initialized = False

    def _init_ultralytics(self) -> bool:
        """使用Ultralytics库初始化YOLO（PC开发环境）"""
        if not YOLO_AVAILABLE:
            logger.error("Ultralytics YOLO not available. Install: pip install ultralytics")
            return False

        try:
            # 自动选择设备
            device = self.device
            if device == "auto":
                device = "cuda" if _check_cuda_available() else "cpu"

            self._model = YOLO(self.model_path)
            self._model.to(device)
            logger.info(f"YOLO model loaded from {self.model_path}, device={device}")
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to load Ultralytics YOLO model: {e}")
            return False

    def _init_onnx(self) -> bool:
        """使用ONNX Runtime初始化YOLO（昇腾/跨平台部署）"""
        if not ONNXRUNTIME_AVAILABLE:
            logger.error("ONNX Runtime not available. Install: pip install onnxruntime")
            return False

        try:
            # ONNX Runtime provider选择
            providers = []
            if self.device == "mlu" or self.device == " ascend":
                providers = ['AscendExecutionProvider', 'CPUExecutionProvider']
            elif self.device == "cuda" and _check_cuda_available():
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            else:
                providers = ['CPUExecutionProvider']

            self._session = ort.InferenceSession(self.model_path, providers=providers)
            logger.info(f"ONNX model loaded from {self.model_path}, providers={providers}")
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to load ONNX model: {e}")
            return False

    def _init_ascend_om(self) -> bool:
        """昇腾 NPU .om 模型"""
        try:
            from .ascend.yolo_npu import YoloNpuDetector, can_use_yolo_npu

            if not can_use_yolo_npu(self.model_path):
                logger.error(
                    "Ascend OM 不可用：需 acl 模块且模型存在 %s", self.model_path
                )
                return False
            device_id = 0 if self.device in ("auto", "mlu", "ascend", "npu") else 0
            self._npu_detector = YoloNpuDetector(
                self.model_path,
                device_id=device_id,
                conf_threshold=self.conf_threshold,
                iou_threshold=self.iou_threshold,
            )
            logger.info("YOLO OM loaded on Ascend NPU: %s", self.model_path)
            self._initialized = True
            return True
        except Exception as e:
            logger.error("Failed to load Ascend OM YOLO: %s", e)
            return False

    def initialize(self) -> bool:
        """
        初始化检测器，尝试多种后端

        Returns:
            bool: 初始化是否成功
        """
        if self._initialized:
            return True

        # 根据文件后缀选择后端
        model_ext = self.model_path.lower().split('.')[-1]

        if model_ext == 'pt':
            return self._init_ultralytics()
        elif model_ext == 'om':
            return self._init_ascend_om()
        elif model_ext in ('onnx',):
            return self._init_onnx()
        else:
            # 尝试自动检测
            if YOLO_AVAILABLE:
                return self._init_ultralytics()
            elif ONNXRUNTIME_AVAILABLE:
                return self._init_onnx()

        logger.error("No suitable YOLO backend available")
        return False

    def detect_objects(self, image: np.ndarray) -> List[Detection]:
        """
        对输入图像进行目标检测

        Args:
            image: BGR格式的彩色图像 (H, W, 3)

        Returns:
            Detection对象列表
        """
        if not self._initialized:
            if not self.initialize():
                logger.error("Detector not initialized")
                return []

        try:
            if self._model is not None:
                # Ultralytics YOLO推理
                return self._detect_ultralytics(image)
            elif self._npu_detector is not None:
                return self._detect_ascend_om(image)
            elif self._session is not None:
                # ONNX Runtime推理
                return self._detect_onnx(image)
            else:
                return []
        except Exception as e:
            logger.error(f"Detection failed: {e}")
            return []

    def _detect_ultralytics(self, image: np.ndarray) -> List[Detection]:
        """Ultralytics YOLO推理"""
        results = self._model(image, conf=self.conf_threshold, iou=self.iou_threshold, verbose=False)

        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])

                # 获取边界框坐标
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                # 计算中心点
                u, v = int((x1 + x2) / 2), int((y1 + y2) / 2)

                # 获取类别名称
                if self.classes and cls_id < len(self.classes):
                    class_name = self.classes[cls_id]
                else:
                    class_name = f"class_{cls_id}"

                detections.append(Detection(
                    class_name=class_name,
                    confidence=conf,
                    bbox_center=(u, v),
                    bbox=(x1, y1, x2, y2),
                ))

        return detections

    def _detect_ascend_om(self, image: np.ndarray) -> List[Detection]:
        """昇腾 NPU YOLO 推理"""
        raw = self._npu_detector.detect(image)
        detections = []
        for det in raw:
            x1, y1, x2, y2 = det["bbox"]
            u, v = det["bbox_center"]
            detections.append(
                Detection(
                    class_name=det["class_name"],
                    confidence=det["confidence"],
                    bbox_center=(u, v),
                    bbox=(x1, y1, x2, y2),
                )
            )
        return detections

    def _detect_onnx(self, image: np.ndarray) -> List[Detection]:
        """ONNX Runtime YOLO推理"""
        # 预处理：resize + normalize
        input_tensor = self._preprocess_image(image)

        # 推理
        inputs = {self._session.get_inputs()[0].name: input_tensor}
        outputs = self._session.run(None, inputs)

        # 后处理：解析输出
        detections = self._postprocess_onnx(outputs[0], image.shape)

        return detections

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """图像预处理"""
        import cv2

        # Resize到模型输入尺寸
        resized = cv2.resize(image, self._input_shape)

        # 归一化 + 转换格式
        blob = resized.astype(np.float32) / 255.0

        # HWC -> CHW
        blob = np.transpose(blob, (2, 0, 1))

        # 添加batch维度
        blob = np.expand_dims(blob, axis=0)

        return blob

    def _postprocess_onnx(self, output: np.ndarray, original_shape: Tuple) -> List[Detection]:
        """ONNX输出后处理"""
        detections = []
        h_orig, w_orig = original_shape[:2]

        # 解析YOLOv8输出格式（1, 84, 8400）或（1, 8400, 84）
        # 84 = 4(box) + 80(classes) 或自定义类别数
        if output.ndim == 3:
            # (batch, 84, 8400) -> transpose -> (batch, 8400, 84)
            output = np.transpose(output, (0, 2, 1))

        # 遍历所有检测框
        for detection in output[0]:  # batch=0
            # 前4个是box (cx, cy, w, h)
            cx, cy, w, h = detection[:4]
            # 其余是类别分数
            scores = detection[4:]

            if scores.size == 0:
                continue

            max_score = float(np.max(scores))
            if max_score < self.conf_threshold:
                continue

            cls_id = int(np.argmax(scores))

            # 转换到原图坐标
            x1 = int((cx - w / 2) * w_orig / self._input_shape[0])
            y1 = int((cy - h / 2) * h_orig / self._input_shape[1])
            x2 = int((cx + w / 2) * w_orig / self._input_shape[0])
            y2 = int((cy + h / 2) * h_orig / self._input_shape[1])

            # 限制在图像范围内
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w_orig, x2), min(h_orig, y2)

            u, v = int((x1 + x2) / 2), int((y1 + y2) / 2)

            if self.classes and cls_id < len(self.classes):
                class_name = self.classes[cls_id]
            else:
                class_name = f"class_{cls_id}"

            detections.append(Detection(
                class_name=class_name,
                confidence=max_score,
                bbox_center=(u, v),
                bbox=(x1, y1, x2, y2),
            ))

        return detections


class ROSImageListener:
    """ROS图像话题监听器"""

    def __init__(self, color_topic: str = "/camera_1/color/image_raw"):
        """
        初始化ROS图像监听器

        Args:
            color_topic: 彩色图像ROS话题名称
        """
        self.color_topic = color_topic
        self._subscriber = None
        self._bridge = None
        self._latest_color_image: Optional[np.ndarray] = None
        self._latest_color_stamp: Optional[float] = None
        self._lock_color = __import__('threading').Lock()

        if not ROS_AVAILABLE:
            logger.warning("ROS not available, image listener disabled")
            return

        try:
            self._bridge = CvBridge()
        except Exception as e:
            logger.error(f"Failed to initialize CV bridge: {e}")

    def start(self):
        """开始订阅ROS图像话题"""
        if not ROS_AVAILABLE or self._subscriber is not None:
            return

        try:
            self._subscriber = rospy.Subscriber(
                self.color_topic,
                Image,
                self._color_callback,
                queue_size=1
            )
            logger.info(f"Subscribed to color image topic: {self.color_topic}")
        except Exception as e:
            logger.error(f"Failed to subscribe to color topic: {e}")

    def _color_callback(self, msg: Image):
        """彩色图像回调"""
        try:
            cv_image = self._bridge.imgmsg_to_cv2(msg, "bgr8")
            stamp = msg.header.stamp.to_sec()

            with self._lock_color:
                self._latest_color_image = cv_image
                self._latest_color_stamp = stamp
        except Exception as e:
            logger.error(f"Error converting color image: {e}")

    def get_latest_color_image(self) -> Tuple[Optional[np.ndarray], Optional[float]]:
        """
        获取最新的一帧彩色图像

        Returns:
            (image, timestamp) 元组，timestamp为ROS时间戳
        """
        with self._lock_color:
            if self._latest_color_image is None:
                return None, None
            return self._latest_color_image.copy(), self._latest_color_stamp


class ObjectDetectionNode:
    """目标检测ROS节点：订阅图像 + 检测"""

    def __init__(
        self,
        model_path: str = "ascend_models/yolov8n.pt",
        color_topic: str = "/camera_1/color/image_raw",
        conf_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        device: str = "auto",
        classes: Optional[List[str]] = None,
    ):
        """
        初始化目标检测节点

        Args:
            model_path: YOLO模型路径
            color_topic: 彩色图像ROS话题
            conf_threshold: 置信度阈值
            iou_threshold: NMS IoU阈值
            device: 推理设备
            classes: 目标类别列表
        """
        self._detector = YOLODetector(
            model_path=model_path,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            device=device,
            classes=classes,
        )
        self._image_listener = ROSImageListener(color_topic=color_topic)
        self._initialized = False

    def initialize(self) -> bool:
        """初始化检测器和图像监听器"""
        if self._initialized:
            return True

        # 初始化YOLO模型
        if not self._detector.initialize():
            logger.error("Failed to initialize YOLO detector")
            return False

        # 启动ROS图像订阅
        if ROS_AVAILABLE:
            try:
                if not rospy.core.is_initialized():
                    rospy.init_node('yolo_detection_node', anonymous=True)
                self._image_listener.start()
            except Exception as e:
                logger.error(f"Failed to initialize ROS: {e}")
                return False

        self._initialized = True
        logger.info("ObjectDetectionNode initialized successfully")
        return True

    def detect_once(self, image: np.ndarray) -> List[Detection]:
        """
        对单帧图像进行检测

        Args:
            image: BGR格式图像

        Returns:
            检测结果列表
        """
        if not self._initialized:
            self.initialize()
        return self._detector.detect_objects(image)

    def detect_from_ros(self, timeout: float = 5.0) -> Tuple[List[Detection], Optional[float]]:
        """
        从ROS话题获取图像并检测

        Args:
            timeout: 超时时间（秒）

        Returns:
            (检测结果列表, 图像时间戳)
        """
        if not self._initialized:
            self.initialize()

        start_time = time.time()
        while (time.time() - start_time) < timeout:
            image, stamp = self._image_listener.get_latest_color_image()
            if image is not None:
                detections = self._detector.detect_objects(image)
                return detections, stamp
            time.sleep(0.01)

        logger.warning(f"No image received within {timeout}s timeout")
        return [], None

    def find_target(
        self,
        target_class: str,
        attribute: Optional[str] = None,
        min_confidence: float = 0.5,
    ) -> Optional[Detection]:
        """
        在检测结果中查找指定目标

        Args:
            target_class: 目标类别（如"cup", "bottle"）
            attribute: 目标属性（如"red", "blue"），用于颜色匹配
            min_confidence: 最小置信度

        Returns:
            匹配的检测结果，如果没有找到返回None
        """
        if not self._initialized:
            self.initialize()

        # 从ROS获取图像并检测
        detections, _ = self.detect_from_ros()

        if not detections:
            return None

        # 过滤匹配的类别
        matching = [d for d in detections
                    if d.class_name.lower() == target_class.lower()
                    and d.confidence >= min_confidence]

        if not matching:
            return None

        # 按置信度排序，返回最高置信度的结果
        matching.sort(key=lambda x: x.confidence, reverse=True)
        result = matching[0]

        logger.info(f"Found target: {result.class_name}, conf={result.confidence:.3f}, "
                    f"center=({result.bbox_center[0]}, {result.bbox_center[1]})")

        return result


# 工具函数
def _check_cuda_available() -> bool:
    """检查CUDA是否可用"""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def detect_objects(image: np.ndarray) -> List[Detection]:
    """
    便捷函数：对输入图像进行目标检测

    Args:
        image: BGR格式的彩色图像 (H, W, 3)

    Returns:
        Detection对象列表
    """
    detector = YOLODetector()
    if not detector.initialize():
        return []
    return detector.detect_objects(image)
