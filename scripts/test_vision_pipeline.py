#!/usr/bin/env python3
"""
测试视觉感知流水线

演示如何从语音指令到目标3D定位的完整流程。
"""

import sys
import os
import logging

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_semantic_parser():
    """测试语义解析器"""
    logger.info("=" * 50)
    logger.info("测试语义解析器")
    logger.info("=" * 50)

    from vision_lim import parse_instruction

    test_cases = [
        "把红色的杯子拿给我",
        "递给我蓝色的球",
        "把瓶子拿过来",
        "停止",
    ]

    for text in test_cases:
        result = parse_instruction(text)
        logger.info(f"输入: {text}")
        logger.info(f"解析: {result}")
        logger.info("-" * 30)


def test_coordinate_transform():
    """测试坐标变换"""
    logger.info("=" * 50)
    logger.info("测试坐标变换")
    logger.info("=" * 50)

    from vision_lim import (
        CoordinateTransformer,
        TargetPosition,
        pixel_to_camera_coord,
        camera_to_arm_base,
    )
    import numpy as np

    # 使用默认内参创建变换器
    transformer = CoordinateTransformer()

    # 测试像素到相机坐标
    u, v = 160, 120  # 图像中心
    depth_m = 0.5   # 0.5米深度

    cam_coord = pixel_to_camera_coord(u, v, depth_m, transformer.color_intrinsics)
    logger.info(f"像素({u}, {v}) + 深度{depth_m}m -> 相机坐标{cam_coord}")

    # 测试相机到机械臂基座
    arm_coord = camera_to_arm_base(cam_coord, transformer.T_cam_to_arm)
    logger.info(f"相机坐标{cam_coord} -> 机械臂基座{arm_coord}")

    # 测试CoordinateTransformer
    result = transformer.pixel_to_arm_base(u, v, depth_m)
    logger.info(f"像素({u}, {v}) + 深度{depth_m}m -> 机械臂基座{result}")

    logger.info("-" * 30)


def test_config_loading():
    """测试配置加载"""
    logger.info("=" * 50)
    logger.info("测试配置加载")
    logger.info("=" * 50)

    from vision_lim import load_intrinsics_from_yaml
    import os

    # 尝试加载配置文件
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', 'vision_lim', 'config', 'camera_intrinsics.yaml'
    )

    if os.path.exists(config_path):
        configs = load_intrinsics_from_yaml(config_path)
        logger.info(f"加载配置文件: {config_path}")
        logger.info(f"彩色相机内参: {configs['color_camera']}")
        logger.info(f"深度相机内参: {configs['depth_camera']}")
    else:
        logger.warning(f"配置文件不存在: {config_path}")
        logger.info("使用默认内参")

    logger.info("-" * 30)


def test_yolo_detector_mock():
    """模拟测试YOLO检测器（无需实际运行ROS）"""
    logger.info("=" * 50)
    logger.info("模拟测试YOLO检测器")
    logger.info("=" * 50)

    from vision_lim import YOLODetector, Detection
    import numpy as np

    # 创建模拟图像
    mock_image = np.zeros((240, 320, 3), dtype=np.uint8)

    # 尝试初始化检测器
    detector = YOLODetector(
        model_path="ascend_models/yolov8n.pt",
        conf_threshold=0.5,
        device="cpu",
        classes=["cup", "bottle", "ball", "phone"],
    )

    initialized = detector.initialize()
    if initialized:
        logger.info("YOLO检测器初始化成功")

        # 模拟检测结果
        mock_detection = Detection(
            class_name="cup",
            confidence=0.85,
            bbox_center=(160, 120),
            bbox=(100, 80, 220, 160),
        )
        logger.info(f"模拟检测结果: {mock_detection}")
    else:
        logger.warning("YOLO检测器初始化失败（这是预期的，如果没有安装模型）")

    logger.info("-" * 30)


def test_depth_processing_mock():
    """模拟测试深度处理"""
    logger.info("=" * 50)
    logger.info("模拟测试深度处理")
    logger.info("=" * 50)

    from vision_lim import get_reliable_depth
    import numpy as np

    # 创建模拟深度图像（毫米单位）
    mock_depth = np.ones((240, 320), dtype=np.uint16) * 500  # 0.5米
    mock_depth[100:140, 100:140] = 0  # 无效区域

    # 测试获取深度值
    depth = get_reliable_depth(mock_depth, 160, 120)
    logger.info(f"中心点深度: {depth}m")

    depth = get_reliable_depth(mock_depth, 120, 120)
    logger.info(f"无效区域深度（应该搜索邻近）: {depth}m")

    logger.info("-" * 30)


def test_pipeline_integration():
    """测试流水线集成（模拟）"""
    logger.info("=" * 50)
    logger.info("模拟测试完整流水线")
    logger.info("=" * 50)

    from vision_lim import VisionPipeline, VoiceCommand, TargetResult

    # 模拟语音指令
    text = "把红色的杯子拿给我"

    # 创建流水线（不连接ROS）
    pipeline = VisionPipeline(
        config_path=None,  # 使用默认配置
        model_path="ascend_models/yolov8n.pt",
    )

    # 解析语音指令
    command = pipeline.parse_voice_command(text)
    logger.info(f"语音指令: {text}")
    logger.info(f"解析结果: {command.to_dict()}")

    if command.target:
        logger.info(f"需要定位的目标: {command.target} (属性: {command.attribute})")
        logger.info("注意: 实际定位需要ROS图像话题和YOLO模型")
    else:
        logger.warning("无法识别目标")

    logger.info("-" * 30)


def test_grasp_planner():
    """测试抓取规划器"""
    logger.info("=" * 50)
    logger.info("测试抓取规划器")
    logger.info("=" * 50)

    from vision_lim import GraspPlanner

    planner = GraspPlanner()

    # 假设目标在机械臂基座坐标系下的位置
    target_pos = (0.3, -0.2, 0.1)  # x, y, z (米)

    # 规划抓取
    plan = planner.plan_grasp_pose(target_pos, hand="right")
    logger.info(f"目标位置: {target_pos}")
    logger.info(f"预抓取位置: {plan['pre_grasp']['position']}")
    logger.info(f"抓取位置: {plan['grasp']['position']}")

    logger.info("-" * 30)


def main():
    """主函数"""
    logger.info("视觉感知流水线测试")
    logger.info("=" * 50)

    # 基础功能测试（不需要ROS）
    test_semantic_parser()
    test_coordinate_transform()
    test_config_loading()
    test_depth_processing_mock()
    test_grasp_planner()

    # YOLO检测器测试（需要模型文件）
    test_yolo_detector_mock()

    # 流水线集成测试（模拟）
    test_pipeline_integration()

    logger.info("=" * 50)
    logger.info("所有测试完成")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
