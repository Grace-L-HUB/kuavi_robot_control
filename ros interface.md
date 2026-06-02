
root@davinci-mini:/home/HwHiAiUser# rosnode info /ros_interface
--------------------------------------------------------------------------------
Node [/ros_interface]
Publications:
 * /avoid_3d_trigger [std_msgs/Bool]
 * /charge_cmd [woosh_msgs/Charge]
 * /charge_control/cancel [actionlib_msgs/GoalID]
 * /charge_control/goal [woosh_msgs/ChargeControlActionGoal]
 * /cmd_vel_control/cancel [actionlib_msgs/GoalID]
 * /cmd_vel_control/goal [woosh_msgs/StepControlActionGoal]
 * /driver_base/second_position/cancel [actionlib_msgs/GoalID]
 * /driver_base/second_position/goal [woosh_msgs/SecondPositionActionGoal]
 * /enable_follower [std_msgs/Bool]
 * /follow_base/local_costmap/set_footprint [geometry_msgs/Polygon]
 * /initialpose [geometry_msgs/PoseWithCovarianceStamped]
 * /kShelfLedColorPubName [woosh_msgs/LED]
 * /key_cmd_vel [geometry_msgs/Twist]
 * /lift_control/cancel [actionlib_msgs/GoalID]
 * /lift_control/goal [woosh_msgs/LiftControlActionGoal]
 * /lift_control2/cancel [actionlib_msgs/GoalID]
 * /lift_control2/goal [woosh_msgs/LiftControl2ActionGoal]
 * /lift_control3/cancel [actionlib_msgs/GoalID]
 * /lift_control3/goal [woosh_msgs/LiftControl3ActionGoal]
 * /manekineko [woosh_msgs/Manekineko]
 * /move_base/cancel [actionlib_msgs/GoalID]
 * /move_base/global_costmap/set_footprint [geometry_msgs/Polygon]
 * /move_base/global_plan [nav_msgs/Path]
 * /move_base/goal [woosh_msgs/MoveBaseActionGoal]
 * /move_base/local_costmap/set_footprint [geometry_msgs/Polygon]
 * /navigation_mode/cancel [actionlib_msgs/GoalID]
 * /navigation_mode/goal [woosh_msgs/NavigationModeActionGoal]
 * /rgbled [woosh_msgs/LED]
 * /robot_status [woosh_msgs/RobotStatus]
 * /roller1_control/cancel [actionlib_msgs/GoalID]
 * /roller1_control/goal [woosh_msgs/RollerControlActionGoal]
 * /roller2_control/cancel [actionlib_msgs/GoalID]
 * /roller2_control/goal [woosh_msgs/RollerControlActionGoal]
 * /rosout [rosgraph_msgs/Log]
 * /tractor_control/cancel [actionlib_msgs/GoalID]
 * /tractor_control/goal [woosh_msgs/TractorControlActionGoal]
 * /voice_synthesis [std_msgs/String]
 * /volume/percentSet [woosh_msgs/VolumeCtl]
 * /woosh_ar_track_charge/cancel [actionlib_msgs/GoalID]
 * /woosh_ar_track_charge/goal [woosh_msgs/ArTrackChargeActionGoal]
 * /woosh_auto_dock/cancel [actionlib_msgs/GoalID]
 * /woosh_auto_dock/goal [woosh_msgs/AutoDock2ActionGoal]
 * /woosh_rosbag_record/goal [woosh_msgs/WooshRosbagRecord]
 * /xarm_base/cancel [actionlib_msgs/GoalID]
 * /xarm_base/goal [woosh_msgs/ArmActionGoal]

Subscriptions:
 * /IO_input [woosh_msgs/IOs]
 * /battery [woosh_msgs/Battery]
 * /beacons [woosh_msgs/Beacons]
 * /charge_control/feedback [woosh_msgs/ChargeControlActionFeedback]
 * /charge_control/result [woosh_msgs/ChargeControlActionResult]
 * /charge_control/status [actionlib_msgs/GoalStatusArray]
 * /cmd_vel_control/feedback [woosh_msgs/StepControlActionFeedback]
 * /cmd_vel_control/result [woosh_msgs/StepControlActionResult]
 * /cmd_vel_control/status [actionlib_msgs/GoalStatusArray]
 * /driver_base/rf_remote_controller [woosh_msgs/RfRemoteController]
 * /driver_base/second_position/feedback [woosh_msgs/SecondPositionActionFeedback]
 * /driver_base/second_position/result [woosh_msgs/SecondPositionActionResult]
 * /driver_base/second_position/status [actionlib_msgs/GoalStatusArray]
 * /follow/remote_control_request [woosh_msgs/IOs]
 * /lift [woosh_msgs/IOModule]
 * /lift_control/feedback [woosh_msgs/LiftControlActionFeedback]
 * /lift_control/result [woosh_msgs/LiftControlActionResult]
 * /lift_control/status [actionlib_msgs/GoalStatusArray]
 * /lift_control2/feedback [woosh_msgs/LiftControl2ActionFeedback]
 * /lift_control2/result [woosh_msgs/LiftControl2ActionResult]
 * /lift_control2/status [actionlib_msgs/GoalStatusArray]
 * /lift_control3/feedback [woosh_msgs/LiftControl3ActionFeedback]
 * /lift_control3/result [woosh_msgs/LiftControl3ActionResult]
 * /lift_control3/status [actionlib_msgs/GoalStatusArray]
 * /localization_state [std_msgs/UInt32]
 * /move_base/feedback [woosh_msgs/MoveBaseActionFeedback]
 * /move_base/global_costmap/set_footprint [geometry_msgs/Polygon]
 * /move_base/global_plan [nav_msgs/Path]
 * /move_base/result [woosh_msgs/MoveBaseActionResult]
 * /move_base/status [actionlib_msgs/GoalStatusArray]
 * /navigation_mode/feedback [woosh_msgs/NavigationModeActionFeedback]
 * /navigation_mode/result [woosh_msgs/NavigationModeActionResult]
 * /navigation_mode/status [actionlib_msgs/GoalStatusArray]
 * /odom_twist [geometry_msgs/Twist]
 * /odometer [std_msgs/Float64]
 * /rfid_landmark [woosh_msgs/RFIDs]
 * /roller1 [woosh_msgs/IOModule]
 * /roller1_control/feedback [woosh_msgs/RollerControlActionFeedback]
 * /roller1_control/result [woosh_msgs/RollerControlActionResult]
 * /roller1_control/status [actionlib_msgs/GoalStatusArray]
 * /roller2 [woosh_msgs/IOModule]
 * /roller2_control/feedback [woosh_msgs/RollerControlActionFeedback]
 * /roller2_control/result [woosh_msgs/RollerControlActionResult]
 * /roller2_control/status [actionlib_msgs/GoalStatusArray]
 * /scan [sensor_msgs/LaserScan]
 * /scanner_status [woosh_msgs/ScannerStatus]
 * /status_code [std_msgs/UInt64]
 * /system_agent/wifi/status [std_msgs/String]
 * /tf [tf2_msgs/TFMessage]
 * /tf_static [tf2_msgs/TFMessage]
 * /tractor [woosh_msgs/IOModule]
 * /tractor_control/feedback [woosh_msgs/TractorControlActionFeedback]
 * /tractor_control/result [woosh_msgs/TractorControlActionResult]
 * /tractor_control/status [actionlib_msgs/GoalStatusArray]
 * /trigger_field [woosh_msgs/NavMode]
 * /volume/percent [woosh_msgs/VolumeCtl]
 * /woosh_ar_track_charge/feedback [woosh_msgs/ArTrackChargeActionFeedback]
 * /woosh_ar_track_charge/result [woosh_msgs/ArTrackChargeActionResult]
 * /woosh_ar_track_charge/status [actionlib_msgs/GoalStatusArray]
 * /woosh_auto_dock/feedback [woosh_msgs/AutoDock2ActionFeedback]
 * /woosh_auto_dock/result [woosh_msgs/AutoDock2ActionResult]
 * /woosh_auto_dock/status [actionlib_msgs/GoalStatusArray]
 * /woosh_rosbag_record/filename [std_msgs/String]
 * /xarm_base/feedback [woosh_msgs/ArmActionFeedback]
 * /xarm_base/result [woosh_msgs/ArmActionResult]
 * /xarm_base/status [actionlib_msgs/GoalStatusArray]

Services:
 * /exec_task
 * /ros_interface/get_loggers
 * /ros_interface/set_logger_level


contacting node http://169.254.128.2:45177/ ...
Pid: 2064
Connections:
 * topic: /rosout
    * to: /rosout
    * direction: outbound (40127 - 169.254.128.2:42260) [43]
    * transport: TCPROS
 * topic: /move_base/goal
    * to: /woosh_field_detector
    * direction: outbound (40127 - 169.254.128.2:42428) [50]
    * transport: TCPROS
 * topic: /move_base/goal
    * to: /move_base
    * direction: outbound (40127 - 169.254.128.2:44412) [221]
    * transport: TCPROS
 * topic: /move_base/cancel
    * to: /move_base
    * direction: outbound (40127 - 169.254.128.2:44422) [235]
    * transport: TCPROS
 * topic: /navigation_mode/goal
    * to: /move_base
    * direction: outbound (40127 - 169.254.128.2:44424) [224]
    * transport: TCPROS
 * topic: /navigation_mode/cancel
    * to: /move_base
    * direction: outbound (40127 - 169.254.128.2:44438) [222]
    * transport: TCPROS
 * topic: /cmd_vel_control/goal
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42284) [51]
    * transport: TCPROS
 * topic: /cmd_vel_control/cancel
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42312) [65]
    * transport: TCPROS
 * topic: /lift_control/goal
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42338) [72]
    * transport: TCPROS
 * topic: /lift_control/cancel
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42344) [73]
    * transport: TCPROS
 * topic: /lift_control2/goal
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42328) [67]
    * transport: TCPROS
 * topic: /lift_control2/cancel
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42360) [74]
    * transport: TCPROS
 * topic: /lift_control3/goal
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42362) [75]
    * transport: TCPROS
 * topic: /lift_control3/cancel
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42374) [76]
    * transport: TCPROS
 * topic: /roller1_control/goal
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42402) [79]
    * transport: TCPROS
 * topic: /roller1_control/cancel
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42300) [61]
    * transport: TCPROS
 * topic: /roller2_control/goal
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42302) [63]
    * transport: TCPROS
 * topic: /roller2_control/cancel
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42412) [80]
    * transport: TCPROS
 * topic: /tractor_control/goal
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42376) [77]
    * transport: TCPROS
 * topic: /tractor_control/cancel
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42392) [78]
    * transport: TCPROS
 * topic: /woosh_ar_track_charge/goal
    * to: /woosh_ar_track_charge
    * direction: outbound (40127 - 169.254.128.2:42264) [158]
    * transport: TCPROS
 * topic: /woosh_ar_track_charge/cancel
    * to: /woosh_ar_track_charge
    * direction: outbound (40127 - 169.254.128.2:42276) [160]
    * transport: TCPROS
 * topic: /driver_base/second_position/goal
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42424) [82]
    * transport: TCPROS
 * topic: /driver_base/second_position/cancel
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42414) [81]
    * transport: TCPROS
 * topic: /woosh_auto_dock/goal
    * to: /woosh_auto_dock_node
    * direction: outbound (40127 - 169.254.128.2:42588) [92]
    * transport: TCPROS
 * topic: /woosh_auto_dock/cancel
    * to: /woosh_auto_dock_node
    * direction: outbound (40127 - 169.254.128.2:42594) [52]
    * transport: TCPROS
 * topic: /charge_control/goal
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42524) [48]
    * transport: TCPROS
 * topic: /charge_control/cancel
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42530) [84]
    * transport: TCPROS
 * topic: /avoid_3d_trigger
    * to: /woosh_obstacle_detect_camera_1
    * direction: outbound (40127 - 169.254.128.2:42430) [59]
    * transport: TCPROS
 * topic: /move_base/global_costmap/set_footprint
    * to: /ros_interface
    * direction: outbound
    * transport: INTRAPROCESS
 * topic: /move_base/global_costmap/set_footprint
    * to: /move_base
    * direction: outbound (40127 - 169.254.128.2:44400) [115]
    * transport: TCPROS
 * topic: /move_base/local_costmap/set_footprint
    * to: /woosh_move_with_avoid_node
    * direction: outbound (40127 - 169.254.128.2:42432) [62]
    * transport: TCPROS
 * topic: /move_base/local_costmap/set_footprint
    * to: /woosh_laser_verify_node
    * direction: outbound (40127 - 169.254.128.2:42456) [68]
    * transport: TCPROS
 * topic: /move_base/local_costmap/set_footprint
    * to: /woosh_passages_control
    * direction: outbound (40127 - 169.254.128.2:42460) [46]
    * transport: TCPROS
 * topic: /move_base/local_costmap/set_footprint
    * to: /woosh_localization
    * direction: outbound (40127 - 169.254.128.2:42490) [70]
    * transport: TCPROS
 * topic: /move_base/local_costmap/set_footprint
    * to: /woosh_auto_dock_guiway
    * direction: outbound (40127 - 169.254.128.2:42510) [83]
    * transport: TCPROS
 * topic: /move_base/local_costmap/set_footprint
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42532) [85]
    * transport: TCPROS
 * topic: /move_base/local_costmap/set_footprint
    * to: /woosh_auto_dock_node
    * direction: outbound (40127 - 169.254.128.2:42574) [45]
    * transport: TCPROS
 * topic: /move_base/local_costmap/set_footprint
    * to: /move_base
    * direction: outbound (40127 - 169.254.128.2:44418) [112]
    * transport: TCPROS
 * topic: /initialpose
    * to: /woosh_localization
    * direction: outbound (40127 - 169.254.128.2:42472) [69]
    * transport: TCPROS
 * topic: /key_cmd_vel
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42544) [86]
    * transport: TCPROS
 * topic: /voice_synthesis
    * to: /voice_synthesis
    * direction: outbound (40127 - 169.254.128.2:42496) [71]
    * transport: TCPROS
 * topic: /rgbled
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42550) [87]
    * transport: TCPROS
 * topic: /charge_cmd
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42564) [88]
    * transport: TCPROS
 * topic: /move_base/global_plan
    * to: /ros_interface
    * direction: outbound
    * transport: INTRAPROCESS
 * topic: /move_base/global_plan
    * to: /woosh_field_detector
    * direction: outbound (40127 - 169.254.128.2:42462) [49]
    * transport: TCPROS
 * topic: /woosh_rosbag_record/goal
    * to: /woosh_rosbag_record_node
    * direction: outbound (40127 - 169.254.128.2:40576) [111]
    * transport: TCPROS
 * topic: /manekineko
    * to: /mobile_base_nodelet_manager
    * direction: outbound (40127 - 169.254.128.2:42570) [89]
    * transport: TCPROS
 * topic: /volume/percentSet
    * to: /woosh_volume_control
    * direction: outbound (40127 - 169.254.128.2:42250) [128]
    * transport: TCPROS
 * topic: /move_base/status
    * to: /move_base (http://169.254.128.2:38103/)
    * direction: inbound (55846 - 169.254.128.2:52539) [231]
    * transport: TCPROS
 * topic: /move_base/feedback
    * to: /move_base (http://169.254.128.2:38103/)
    * direction: inbound (55832 - 169.254.128.2:52539) [230]
    * transport: TCPROS
 * topic: /move_base/result
    * to: /move_base (http://169.254.128.2:38103/)
    * direction: inbound (55816 - 169.254.128.2:52539) [223]
    * transport: TCPROS
 * topic: /navigation_mode/status
    * to: /move_base (http://169.254.128.2:38103/)
    * direction: inbound (55864 - 169.254.128.2:52539) [234]
    * transport: TCPROS
 * topic: /navigation_mode/feedback
    * to: /move_base (http://169.254.128.2:38103/)
    * direction: inbound (55862 - 169.254.128.2:52539) [233]
    * transport: TCPROS
 * topic: /navigation_mode/result
    * to: /move_base (http://169.254.128.2:38103/)
    * direction: inbound (55850 - 169.254.128.2:52539) [232]
    * transport: TCPROS
 * topic: /cmd_vel_control/status
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52020 - 169.254.128.2:55849) [129]
    * transport: TCPROS
 * topic: /cmd_vel_control/feedback
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52024 - 169.254.128.2:55849) [130]
    * transport: TCPROS
 * topic: /cmd_vel_control/result
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52032 - 169.254.128.2:55849) [131]
    * transport: TCPROS
 * topic: /lift_control/status
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52274 - 169.254.128.2:55849) [193]
    * transport: TCPROS
 * topic: /lift_control/feedback
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52268 - 169.254.128.2:55849) [192]
    * transport: TCPROS
 * topic: /lift_control/result
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52258 - 169.254.128.2:55849) [191]
    * transport: TCPROS
 * topic: /lift_control2/status
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52306 - 169.254.128.2:55849) [196]
    * transport: TCPROS
 * topic: /lift_control2/feedback
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52296 - 169.254.128.2:55849) [195]
    * transport: TCPROS
 * topic: /lift_control2/result
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52282 - 169.254.128.2:55849) [194]
    * transport: TCPROS
 * topic: /lift_control3/status
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52328 - 169.254.128.2:55849) [199]
    * transport: TCPROS
 * topic: /lift_control3/feedback
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52326 - 169.254.128.2:55849) [198]
    * transport: TCPROS
 * topic: /lift_control3/result
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52314 - 169.254.128.2:55849) [197]
    * transport: TCPROS
 * topic: /roller1_control/status
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52036 - 169.254.128.2:55849) [132]
    * transport: TCPROS
 * topic: /roller1_control/feedback
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52052 - 169.254.128.2:55849) [133]
    * transport: TCPROS
 * topic: /roller1_control/result
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52062 - 169.254.128.2:55849) [134]
    * transport: TCPROS
 * topic: /roller2_control/status
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52072 - 169.254.128.2:55849) [135]
    * transport: TCPROS
 * topic: /roller2_control/feedback
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52124 - 169.254.128.2:55849) [150]
    * transport: TCPROS
 * topic: /roller2_control/result
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52136 - 169.254.128.2:55849) [151]
    * transport: TCPROS
 * topic: /tractor_control/status
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52362 - 169.254.128.2:55849) [202]
    * transport: TCPROS
 * topic: /tractor_control/feedback
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52348 - 169.254.128.2:55849) [201]
    * transport: TCPROS
 * topic: /tractor_control/result
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52332 - 169.254.128.2:55849) [200]
    * transport: TCPROS
 * topic: /woosh_ar_track_charge/status
    * to: /woosh_ar_track_charge (http://169.254.128.2:32825/)
    * direction: inbound (38440 - 169.254.128.2:40323) [152]
    * transport: TCPROS
 * topic: /woosh_ar_track_charge/feedback
    * to: /woosh_ar_track_charge (http://169.254.128.2:32825/)
    * direction: inbound (38442 - 169.254.128.2:40323) [153]
    * transport: TCPROS
 * topic: /woosh_ar_track_charge/result
    * to: /woosh_ar_track_charge (http://169.254.128.2:32825/)
    * direction: inbound (38450 - 169.254.128.2:40323) [154]
    * transport: TCPROS
 * topic: /driver_base/second_position/status
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52144 - 169.254.128.2:55849) [155]
    * transport: TCPROS
 * topic: /driver_base/second_position/feedback
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52146 - 169.254.128.2:55849) [156]
    * transport: TCPROS
 * topic: /driver_base/second_position/result
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52154 - 169.254.128.2:55849) [157]
    * transport: TCPROS
 * topic: /woosh_auto_dock/status
    * to: /woosh_auto_dock_node (http://169.254.128.2:35235/)
    * direction: inbound (34070 - 169.254.128.2:47723) [94]
    * transport: TCPROS
 * topic: /woosh_auto_dock/feedback
    * to: /woosh_auto_dock_node (http://169.254.128.2:35235/)
    * direction: inbound (34058 - 169.254.128.2:47723) [91]
    * transport: TCPROS
 * topic: /woosh_auto_dock/result
    * to: /woosh_auto_dock_node (http://169.254.128.2:35235/)
    * direction: inbound (34052 - 169.254.128.2:47723) [90]
    * transport: TCPROS
 * topic: /charge_control/status
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52160 - 169.254.128.2:55849) [159]
    * transport: TCPROS
 * topic: /charge_control/feedback
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52162 - 169.254.128.2:55849) [161]
    * transport: TCPROS
 * topic: /charge_control/result
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52164 - 169.254.128.2:55849) [162]
    * transport: TCPROS
 * topic: /tf
    * to: /robot_state_publisher (http://169.254.128.2:35569/)
    * direction: inbound (52260 - 169.254.128.2:48053) [183]
    * transport: TCPROS
 * topic: /tf
    * to: /woosh_robot_pose_ekf (http://169.254.128.2:45733/)
    * direction: inbound (53244 - 169.254.128.2:57411) [184]
    * transport: TCPROS
 * topic: /tf
    * to: /woosh_passages_control (http://169.254.128.2:38275/)
    * direction: inbound (44180 - 169.254.128.2:55309) [185]
    * transport: TCPROS
 * topic: /tf
    * to: /woosh_localization (http://169.254.128.2:38555/)
    * direction: inbound (36386 - 169.254.128.2:50353) [186]
    * transport: TCPROS
 * topic: /tf
    * to: /woosh_auto_dock_guiway (http://169.254.128.2:45217/)
    * direction: inbound (40852 - 169.254.128.2:52453) [187]
    * transport: TCPROS
 * topic: /tf
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52250 - 169.254.128.2:55849) [188]
    * transport: TCPROS
 * topic: /tf
    * to: /woosh_auto_dock_node (http://169.254.128.2:35235/)
    * direction: inbound (34018 - 169.254.128.2:47723) [189]
    * transport: TCPROS
 * topic: /tf
    * to: /move_base (http://169.254.128.2:38103/)
    * direction: inbound (55796 - 169.254.128.2:52539) [113]
    * transport: TCPROS
 * topic: /IO_input
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52170 - 169.254.128.2:55849) [163]
    * transport: TCPROS
 * topic: /tf_static
    * to: /robot_state_publisher (http://169.254.128.2:35569/)
    * direction: inbound (52268 - 169.254.128.2:48053) [190]
    * transport: TCPROS
 * topic: /lift
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52180 - 169.254.128.2:55849) [164]
    * transport: TCPROS
 * topic: /roller1
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52192 - 169.254.128.2:55849) [165]
    * transport: TCPROS
 * topic: /roller2
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52200 - 169.254.128.2:55849) [166]
    * transport: TCPROS
 * topic: /tractor
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52202 - 169.254.128.2:55849) [167]
    * transport: TCPROS
 * topic: /status_code
    * to: /woosh_robot_pose_ekf (http://169.254.128.2:45733/)
    * direction: inbound (53238 - 169.254.128.2:57411) [168]
    * transport: TCPROS
 * topic: /status_code
    * to: /woosh_move_with_avoid_node (http://169.254.128.2:40495/)
    * direction: inbound (45256 - 169.254.128.2:39169) [169]
    * transport: TCPROS
 * topic: /status_code
    * to: /move_base (http://169.254.128.2:38103/)
    * direction: inbound (40214 - 169.254.128.2:52539) [171]
    * transport: TCPROS
 * topic: /status_code
    * to: /woosh_localization (http://169.254.128.2:38555/)
    * direction: inbound (36350 - 169.254.128.2:50353) [172]
    * transport: TCPROS
 * topic: /status_code
    * to: /woosh_auto_dock_node (http://169.254.128.2:35235/)
    * direction: inbound (34044 - 169.254.128.2:47723) [44]
    * transport: TCPROS
 * topic: /status_code
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52416 - 169.254.128.2:55849) [217]
    * transport: TCPROS
 * topic: /odom_twist
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52422 - 169.254.128.2:55849) [218]
    * transport: TCPROS
 * topic: /odometer
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52436 - 169.254.128.2:55849) [219]
    * transport: TCPROS
 * topic: /battery
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52412 - 169.254.128.2:55849) [42]
    * transport: TCPROS
 * topic: /beacons
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52442 - 169.254.128.2:55849) [220]
    * transport: TCPROS
 * topic: /system_agent/wifi/status
    * to: /woosh_system_agent (http://169.254.128.2:44031/)
    * direction: inbound (33914 - 169.254.128.2:44979) [66]
    * transport: TCPROS
 * topic: /move_base/global_costmap/set_footprint
    * to: /ros_interface (http://169.254.128.2:45177/)
    * direction: inbound
    * transport: INTRAPROCESS
 * topic: /scanner_status
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52216 - 169.254.128.2:55849) [170]
    * transport: TCPROS
 * topic: /scan
    * to: /laser (http://169.254.128.2:44583/)
    * direction: inbound (47350 - 169.254.128.2:34587) [174]
    * transport: TCPROS
 * topic: /scan
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52226 - 169.254.128.2:55849) [175]
    * transport: TCPROS
 * topic: /rfid_landmark
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52236 - 169.254.128.2:55849) [176]
    * transport: TCPROS
 * topic: /move_base/global_plan
    * to: /ros_interface (http://169.254.128.2:45177/)
    * direction: inbound
    * transport: INTRAPROCESS
 * topic: /move_base/global_plan
    * to: /woosh_move_with_avoid_node (http://169.254.128.2:40495/)
    * direction: inbound (45266 - 169.254.128.2:39169) [179]
    * transport: TCPROS
 * topic: /move_base/global_plan
    * to: /move_base (http://169.254.128.2:38103/)
    * direction: inbound (40224 - 169.254.128.2:52539) [180]
    * transport: TCPROS
 * topic: /move_base/global_plan
    * to: /woosh_auto_dock_guiway (http://169.254.128.2:45217/)
    * direction: inbound (40840 - 169.254.128.2:52453) [181]
    * transport: TCPROS
 * topic: /move_base/global_plan
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52242 - 169.254.128.2:55849) [173]
    * transport: TCPROS
 * topic: /woosh_rosbag_record/filename
    * to: /woosh_rosbag_record_node (http://169.254.128.2:42827/)
    * direction: inbound (50248 - 169.254.128.2:35813) [114]
    * transport: TCPROS
 * topic: /localization_state
    * to: /woosh_localization (http://169.254.128.2:38555/)
    * direction: inbound (36360 - 169.254.128.2:50353) [178]
    * transport: TCPROS
 * topic: /driver_base/rf_remote_controller
    * to: /mobile_base_nodelet_manager (http://169.254.128.2:38035/)
    * direction: inbound (52244 - 169.254.128.2:55849) [182]
    * transport: TCPROS
 * topic: /volume/percent
    * to: /woosh_volume_control (http://169.254.128.2:33571/)
    * direction: inbound (43340 - 169.254.128.2:33625) [64]
    * transport: TCPROS
 * topic: /trigger_field
    * to: /woosh_field_detector (http://169.254.128.2:41781/)
    * direction: inbound (59510 - 169.254.128.2:38759) [216]
    * transport: TCPROS

