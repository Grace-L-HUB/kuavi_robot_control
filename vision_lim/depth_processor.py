"""深度图处理模块：订阅ROS深度图像话题，处理深度值。"""

from __future__ import annotations

import logging
import time
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ROS相关导入
ROS_AVAILABLE = False
try:
    import rospy
    from sensor_msgs.msg import Image
    from cv_bridge import CvBridge
    ROS_AVAILABLE = True
except ImportError:
    pass


class ROSDepthListener:
    """ROS深度图像话题监听器"""

    def __init__(self, depth_topic: str = "/camera_1/depth/image_rect_raw"):
        """
        初始化ROS深度图像监听器

        Args:
            depth_topic: 深度图像ROS话题名称
        """
        self.depth_topic = depth_topic
        self._subscriber = None
        self._bridge = None
        self._latest_depth_image: Optional[np.ndarray] = None
        self._latest_depth_stamp: Optional[float] = None
        self._lock = __import__('threading').Lock()
        self._initialized = False

        if not ROS_AVAILABLE:
            logger.warning("ROS not available, depth listener disabled")
            return

        try:
            self._bridge = CvBridge()
        except Exception as e:
            logger.error(f"Failed to initialize CV bridge: {e}")

    def start(self):
        """开始订阅ROS深度图像话题"""
        if not ROS_AVAILABLE or self._subscriber is not None:
            return

        try:
            self._subscriber = rospy.Subscriber(
                self.depth_topic,
                Image,
                self._depth_callback,
                queue_size=1
            )
            logger.info(f"Subscribed to depth image topic: {self.depth_topic}")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to subscribe to depth topic: {e}")

    def _depth_callback(self, msg: Image):
        """深度图像回调"""
        try:
            # 尝试转换为16UC1格式（毫米单位）
            # 如果失败则尝试32FC1格式（米单位）
            try:
                cv_depth = self._bridge.imgmsg_to_cv2(msg, "16UC1")
            except Exception:
                cv_depth = self._bridge.imgmsg_to_cv2(msg, "32FC1")

            stamp = msg.header.stamp.to_sec()

            with self._lock:
                self._latest_depth_image = cv_depth
                self._latest_depth_stamp = stamp
        except Exception as e:
            logger.error(f"Error converting depth image: {e}")

    def get_latest_depth_image(self) -> Tuple[Optional[np.ndarray], Optional[float]]:
        """
        获取最新的一帧深度图像

        Returns:
            (depth_image, timestamp) 元组
            depth_image: 16UC1格式（毫米）或32FC1格式（米），取决于相机
            timestamp: ROS时间戳
        """
        with self._lock:
            if self._latest_depth_image is None:
                return None, None
            return self._latest_depth_image.copy(), self._latest_depth_stamp

    def stop(self):
        """停止订阅"""
        if self._subscriber is not None:
            self._subscriber.unregister()
            self._subscriber = None


def get_reliable_depth(
    depth_image: np.ndarray,
    u: int,
    v: int,
    window_size: int = 5,
) -> Optional[float]:
    """
    获取可靠的深度值（处理无效点和噪声）

    策略:
        1. 若(u,v)处深度有效，直接返回
        2. 否则取周围窗口内有效深度的中位数

    Args:
        depth_image: 深度图像
            - 16UC1格式：单位为毫米，需转换为米
            - 32FC1格式：单位为米
        u, v: 像素坐标
        window_size: 搜索窗口大小（奇数）

    Returns:
        深度值（单位：米），若无有效深度返回None
    """
    if depth_image is None or depth_image.size == 0:
        return None

    h, w = depth_image.shape[:2]

    # 检查坐标是否在图像范围内
    if not (0 <= u < w and 0 <= v < h):
        logger.warning(f"Pixel ({u}, {v}) out of image bounds ({w}, {h})")
        return None

    # 获取当前像素的深度值
    depth = depth_image[v, u]

    # 判断深度图像格式并验证深度值有效性
    if depth_image.dtype == np.uint16:
        # 16UC1格式，单位为毫米
        # 无效深度通常为0或很大的值（如65535）
        if depth > 0 and depth < 65535:
            return float(depth) / 1000.0  # 转换为米
    elif depth_image.dtype == np.float32:
        # 32FC1格式，单位为米
        if np.isfinite(depth) and depth > 0.0 and depth < 10.0:  # 合理深度范围0-10米
            return float(depth)

    # 当前点无效，搜索周围窗口
    return _search_window_depth(depth_image, u, v, window_size)


def _search_window_depth(
    depth_image: np.ndarray,
    u: int,
    v: int,
    window_size: int,
) -> Optional[float]:
    """
    在指定窗口内搜索有效深度值

    Args:
        depth_image: 深度图像
        u, v: 中心像素坐标
        window_size: 窗口大小（奇数）

    Returns:
        有效深度值（米），或None
    """
    h, w = depth_image.shape[:2]
    half = window_size // 2

    # 定义搜索窗口边界
    u_min = max(0, u - half)
    u_max = min(w, u + half + 1)
    v_min = max(0, v - half)
    v_max = min(h, v + half + 1)

    # 提取窗口
    window = depth_image[v_min:v_max, u_min:u_max]

    # 收集有效深度值
    valid_depths = []

    if depth_image.dtype == np.uint16:
        # 16UC1格式
        mask = (window > 0) & (window < 65535)
        if np.any(mask):
            valid_depths = window[mask] / 1000.0  # 转换为米
    elif depth_image.dtype == np.float32:
        # 32FC1格式
        mask = np.isfinite(window) & (window > 0.0) & (window < 10.0)
        if np.any(mask):
            valid_depths = window[mask]

    if not valid_depths:
        # 扩大搜索窗口递归查找
        if window_size < 15:
            return _search_window_depth(depth_image, u, v, window_size + 2)
        logger.warning(f"No valid depth found in window around ({u}, {v})")
        return None

    # 使用中位数作为可靠的深度值
    median_depth = float(np.median(valid_depths))
    return median_depth


def depth_to_pointcloud(
    depth_image: np.ndarray,
    fx: float,
    fy: float,
    cx: float,
    cy: float,
) -> Optional[np.ndarray]:
    """
    将深度图像转换为点云（相机坐标系）

    Args:
        depth_image: 深度图像
        fx, fy, cx, cy: 相机内参

    Returns:
        Nx3 numpy数组，每行是(x, y, z)点坐标，单位米
    """
    if depth_image is None or depth_image.size == 0:
        return None

    h, w = depth_image.shape[:2]

    # 创建像素坐标网格
    u_coords, v_coords = np.meshgrid(np.arange(w), np.arange(h))

    # 展平
    u_flat = u_coords.flatten()
    v_flat = v_coords.flatten()

    # 获取深度值
    if depth_image.dtype == np.uint16:
        z_flat = depth_image.flatten().astype(np.float32) / 1000.0
    else:
        z_flat = depth_image.flatten().astype(np.float32)

    # 过滤无效深度
    valid_mask = (z_flat > 0) & (z_flat < 10.0) & np.isfinite(z_flat)
    u_valid = u_flat[valid_mask]
    v_valid = v_flat[valid_mask]
    z_valid = z_flat[valid_mask]

    # 计算3D坐标
    x_valid = (u_valid - cx) * z_valid / fx
    y_valid = (v_valid - cy) * z_valid / fy

    points = np.stack([x_valid, y_valid, z_valid], axis=1)

    logger.info(f"Generated point cloud with {len(points)} valid points")
    return points


class DepthProcessor:
    """深度图像处理器"""

    def __init__(
        self,
        depth_topic: str = "/camera_1/depth/image_rect_raw",
        depth_scale: float = 1000.0,  # 毫米到米的换算
    ):
        """
        初始化深度处理器

        Args:
            depth_topic: 深度图像ROS话题
            depth_scale: 深度值缩放因子（16UC1格式为1000，32FC1格式为1）
        """
        self.depth_topic = depth_topic
        self.depth_scale = depth_scale
        self._listener = ROSDepthListener(depth_topic=depth_topic)

    def start(self):
        """启动深度图像订阅"""
        if ROS_AVAILABLE:
            try:
                if not rospy.core.is_initialized():
                    rospy.init_node('depth_processor_node', anonymous=True)
                self._listener.start()
            except Exception as e:
                logger.error(f"Failed to start depth listener: {e}")

    def stop(self):
        """停止深度图像订阅"""
        self._listener.stop()

    def get_depth_at(self, u: int, v: int) -> Optional[float]:
        """
        获取指定像素位置的深度值

        Args:
            u, v: 像素坐标

        Returns:
            深度值（米），或None
        """
        depth_image, _ = self._listener.get_latest_depth_image()
        if depth_image is None:
            return None
        return get_reliable_depth(depth_image, u, v)

    def get_depth_image(self) -> Tuple[Optional[np.ndarray], Optional[float]]:
        """
        获取原始深度图像

        Returns:
            (depth_image, timestamp)
        """
        return self._listener.get_latest_depth_image()


class SynchronizedSensorNode:
    """
    同步彩色图像和深度图像的传感器节点

    用于确保在计算3D坐标时，使用的彩色图和深度图是同一时刻的
    """

    def __init__(
        self,
        color_topic: str = "/camera_1/color/image_raw",
        depth_topic: str = "/camera_1/depth/image_rect_raw",
        sync_threshold: float = 0.05,  # 时间同步阈值（秒）
    ):
        """
        初始化同步传感器节点

        Args:
            color_topic: 彩色图像话题
            depth_topic: 深度图像话题
            sync_threshold: 时间同步阈值
        """
        self.color_topic = color_topic
        self.depth_topic = depth_topic
        self.sync_threshold = sync_threshold

        self._color_listener = ROSImageListenerBase(color_topic)
        self._depth_listener = ROSDepthListener(depth_topic)

        self._initialized = False

    def start(self):
        """启动订阅"""
        if ROS_AVAILABLE and not self._initialized:
            try:
                if not rospy.core.is_initialized():
                    rospy.init_node('sync_sensor_node', anonymous=True)
                self._color_listener.start()
                self._depth_listener.start()
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to start sensor nodes: {e}")

    def get_synchronized_frames(
        self,
        timeout: float = 5.0,
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[float]]:
        """
        获取同步的彩色图和深度图

        Args:
            timeout: 超时时间

        Returns:
            (color_image, depth_image, timestamp)
        """
        if not self._initialized:
            self.start()

        start_time = time.time()
        last_color_stamp = None
        last_depth_stamp = None

        while (time.time() - start_time) < timeout:
            color_img, color_stamp = self._color_listener.get_latest_color_image()
            depth_img, depth_stamp = self._depth_listener.get_latest_depth_image()

            # 检查是否有有效数据
            if color_img is None or depth_img is None:
                time.sleep(0.01)
                continue

            # 检查时间同步
            if color_stamp is not None and depth_stamp is not None:
                time_diff = abs(color_stamp - depth_stamp)
                if time_diff < self.sync_threshold:
                    return color_img, depth_img, color_stamp

                # 记录最新的时间戳
                last_color_stamp = color_stamp
                last_depth_stamp = depth_stamp

            time.sleep(0.01)

        # 超时，返回最新帧（可能不完全同步）
        if color_img is not None and depth_img is not None:
            logger.warning("Timeout, returning latest frames (may not be synchronized)")
            return color_img, depth_img, color_stamp or depth_stamp

        return None, None, None

    def stop(self):
        """停止订阅"""
        self._color_listener.stop()
        self._depth_listener.stop()


class ROSImageListenerBase:
    """ROS彩色图像监听器（基础版本）"""

    def __init__(self, color_topic: str = "/camera_1/color/image_raw"):
        self.color_topic = color_topic
        self._subscriber = None
        self._bridge = None
        self._latest_color_image: Optional[np.ndarray] = None
        self._latest_color_stamp: Optional[float] = None
        self._lock = __import__('threading').Lock()

        if not ROS_AVAILABLE:
            return

        try:
            self._bridge = CvBridge()
        except Exception as e:
            logger.error(f"Failed to initialize CV bridge: {e}")

    def start(self):
        if not ROS_AVAILABLE or self._subscriber is not None:
            return

        self._subscriber = rospy.Subscriber(
            self.color_topic,
            Image,
            self._color_callback,
            queue_size=1
        )

    def _color_callback(self, msg: Image):
        try:
            cv_image = self._bridge.imgmsg_to_cv2(msg, "bgr8")
            stamp = msg.header.stamp.to_sec()
            with self._lock:
                self._latest_color_image = cv_image
                self._latest_color_stamp = stamp
        except Exception as e:
            logger.error(f"Error converting color image: {e}")

    def get_latest_color_image(self) -> Tuple[Optional[np.ndarray], Optional[float]]:
        with self._lock:
            if self._latest_color_image is None:
                return None, None
            return self._latest_color_image.copy(), self._latest_color_stamp

    def stop(self):
        if self._subscriber is not None:
            self._subscriber.unregister()
            self._subscriber = None
