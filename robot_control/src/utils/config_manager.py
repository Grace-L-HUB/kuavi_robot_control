import yaml
import os
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str):
        """加载配置文件
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = {}
        self._load_config()
    
    def get(self, key: str, default=None):
        """获取配置值
        
        Args:
            key: 支持点号分隔，如 "robot.websocket.ip"
            default: 默认值
        """
        try:
            keys = key.split('.')
            value = self.config
            for k in keys:
                if k in value:
                    value = value[k]
                else:
                    return default
            return value
        except Exception as e:
            logger.error(f"Error getting config value: {e}")
            return default
    
    def set(self, key: str, value):
        """修改配置值"""
        try:
            keys = key.split('.')
            config = self.config
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            config[keys[-1]] = value
            logger.info(f"Set config {key} to {value}")
        except Exception as e:
            logger.error(f"Error setting config value: {e}")
    
    def save(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"Config saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f)
                logger.info(f"Config loaded from {self.config_path}")
            else:
                logger.warning(f"Config file not found: {self.config_path}")
                # 创建默认配置
                self._create_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            # 创建默认配置
            self._create_default_config()
    
    def _create_default_config(self):
        """创建默认配置"""
        self.config = {
            "robot": {
                "name": "wheeled_robot",
                "websocket": {
                    "ip": "192.168.1.100",
                    "port": 8080,
                    "timeout": 8,
                    "reconnect_interval": 5
                },
                "ros": {
                    "master_uri": "http://192.168.1.100:11311",
                    "arm_topic": "/kuavo_arm_traj",
                    "gripper_service": "/control_robot_leju_claw",
                    "control_mode_service": "/arm_traj_change_mode"
                }
            },
            "motion": {
                "max_linear_speed": 0.5,
                "max_angular_speed": 1.0,
                "default_speed": 0.15,
                "approach_distance": 0.3
            },
            "grasp": {
                "gripper_close_position": 90,
                "gripper_open_position": 0,
                "pre_grasp_height": 0.15,
                "lift_height": 0.2
            },
            "debug": {
                "enable_log": True,
                "log_level": "INFO",
                "save_images": False
            }
        }
        # 保存默认配置
        self.save()
