import websocket
import json
import threading
import time
import socket
import re
import logging

logger = logging.getLogger(__name__)

class WooshWebSocketClient:
    def __init__(self, url: str, debug: bool = False):
        """初始化 WebSocket 客户端
        
        Args:
            url: WebSocket 服务器地址，如 "ws://192.168.1.100:8080/"
            debug: 是否开启调试模式
        """
        self.url = url
        self.debug = debug
        self.ws = None
        self.connected = False
        self.lock = threading.RLock()
        self.requests = {}
        self.subscriptions = {}
        self.subscription_events = {}
        self.subscription_data = {}
        self.thread = None
        self.sn_counter = 0
    
    def connect(self):
        """建立 WebSocket 连接"""
        try:
            self.ws = websocket.WebSocketApp(
                self.url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            self.thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            self.thread.start()
            # 等待连接建立
            for _ in range(10):
                if self.connected:
                    logger.info("WebSocket connected successfully")
                    return True
                time.sleep(0.5)
            logger.error("WebSocket connection timeout")
            return False
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    def close(self):
        """关闭连接"""
        try:
            if self.ws:
                self.ws.close()
                self.connected = False
                logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
    
    def reconnect_test(self) -> bool:
        """测试连接是否正常
        
        Returns:
            bool: 连接正常返回 True
        """
        try:
            if not self.connected:
                return False
            # 发送一个简单的请求测试连接
            test_message = {"type": "woosh.robot.RobotState", "sn": self._generate_sn()}
            self.ws.send(json.dumps(test_message))
            return True
        except Exception as e:
            logger.error(f"Reconnect test failed: {e}")
            return False
    
    def request(self, message_type: str, body: dict = None, timeout: int = 8) -> dict:
        """发送请求并等待响应
        
        Args:
            message_type: 消息类型，如 "woosh.robot.RobotState"
            body: 请求参数
            timeout: 超时时间（秒）
        
        Returns:
            dict: 响应数据，失败返回 None
        
        Note:
            - 每个请求需要生成唯一的 sn 序列号
            - 使用 threading.Event 实现超时机制
            - 响应通过 sn 号匹配对应的请求
        """
        try:
            if not self.connected:
                logger.error("WebSocket not connected")
                return None
            
            sn = self._generate_sn()
            message = {
                "type": message_type,
                "sn": sn
            }
            if body:
                message.update(body)
            
            event = threading.Event()
            response_data = {}
            
            with self.lock:
                self.requests[sn] = (event, response_data)
            
            self.ws.send(json.dumps(message))
            
            if event.wait(timeout):
                with self.lock:
                    if sn in self.requests:
                        del self.requests[sn]
                return response_data
            else:
                logger.error(f"Request timeout: {message_type}")
                with self.lock:
                    if sn in self.requests:
                        del self.requests[sn]
                return None
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None
    
    def add_topic_callback(self, topic: str, callback: callable):
        """添加话题订阅回调
        
        Args:
            topic: 话题名称
            callback: 回调函数，接收消息数据作为参数
        """
        with self.lock:
            self.subscriptions[topic] = callback
    
    def submit_subscriptions(self):
        """发送订阅请求，开始接收订阅数据"""
        try:
            if not self.connected:
                logger.error("WebSocket not connected")
                return
            
            # 这里需要根据实际的订阅格式发送订阅请求
            # 示例：发送订阅消息
            subscription_message = {
                "type": "woosh.subscribe",
                "sn": self._generate_sn(),
                "topics": list(self.subscriptions.keys())
            }
            self.ws.send(json.dumps(subscription_message))
            logger.info(f"Submitted subscriptions: {list(self.subscriptions.keys())}")
        except Exception as e:
            logger.error(f"Failed to submit subscriptions: {e}")
    
    def on_open(self, ws):
        """WebSocket连接打开时的回调"""
        self.connected = True
        logger.info("WebSocket connection opened")
    
    def on_message(self, ws, message):
        """处理接收到的消息"""
        try:
            data = json.loads(message)
            if "sn" in data:
                # 处理请求响应
                sn = data.get("sn")
                with self.lock:
                    if sn in self.requests:
                        event, response_data = self.requests[sn]
                        response_data.update(data)
                        event.set()
            else:
                # 处理订阅消息
                message_type = data.get("type")
                with self.lock:
                    if message_type in self.subscriptions:
                        callback = self.subscriptions[message_type]
                        try:
                            callback(data)
                        except Exception as e:
                            logger.error(f"Callback error for {message_type}: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def on_error(self, ws, error):
        """WebSocket错误时的回调"""
        logger.error(f"WebSocket error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """WebSocket关闭时的回调"""
        self.connected = False
        logger.info(f"WebSocket connection closed: {close_status_code}, {close_msg}")
    
    def _generate_sn(self) -> int:
        """生成唯一的序列号"""
        with self.lock:
            self.sn_counter += 1
            return self.sn_counter
