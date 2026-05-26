"""
Kuavo ROS 消息/服务类型统一导入。

本仓库已内置 robot_control/ros_ws/src/kuavo_msgs，编译后优先使用 kuavo_msgs。
旧环境可能仍使用 kuavo_sdk / motion_capture_ik 包名，此处做兼容回退。
"""
import logging

logger = logging.getLogger(__name__)

KUAVO_MSGS_SOURCE = None

try:
    from kuavo_msgs.msg import (
        armTargetPoses,
        robotHeadMotionData,
        lejuClawState,
        twoArmHandPoseCmd,
        ikSolveParam,
    )
    from kuavo_msgs.srv import (
        changeArmCtrlMode,
        changeArmCtrlModeRequest,
        controlLejuClaw,
        controlLejuClawRequest,
        twoArmHandPoseCmdSrv,
        fkSrv,
    )

    KUAVO_MSGS_SOURCE = "kuavo_msgs"
except ImportError:
    try:
        from kuavo_sdk.msg import armTargetPoses, robotHeadMotionData, lejuClawState
        from kuavo_sdk.srv import (
            changeArmCtrlMode,
            changeArmCtrlModeRequest,
            controlLejuClaw,
            controlLejuClawRequest,
        )
        from motion_capture_ik.msg import twoArmHandPoseCmd, ikSolveParam
        from motion_capture_ik.srv import twoArmHandPoseCmdSrv, fkSrv

        KUAVO_MSGS_SOURCE = "kuavo_sdk+motion_capture_ik"
        logger.warning(
            "kuavo_msgs not found; using kuavo_sdk / motion_capture_ik (legacy). "
            "Prefer: catkin build kuavo_msgs in kuavo-ros-opensource"
        )
    except ImportError as e:
        armTargetPoses = None
        robotHeadMotionData = None
        lejuClawState = None
        twoArmHandPoseCmd = None
        ikSolveParam = None
        changeArmCtrlMode = None
        changeArmCtrlModeRequest = None
        controlLejuClaw = None
        controlLejuClawRequest = None
        twoArmHandPoseCmdSrv = None
        fkSrv = None
        KUAVO_MSGS_SOURCE = None
        logger.warning(f"Kuavo ROS types unavailable: {e}")

KUAVO_ARM_TARGET_MSG = armTargetPoses is not None
KUAVO_ARM_MODE_SRV = changeArmCtrlMode is not None
KUAVO_IK_SRV = twoArmHandPoseCmdSrv is not None and twoArmHandPoseCmd is not None
KUAVO_FK_SRV = fkSrv is not None
KUAVO_CLAW_SRV = controlLejuClaw is not None
KUAVO_CLAW_STATE_MSG = lejuClawState is not None
KUAVO_HEAD_MSG = robotHeadMotionData is not None
