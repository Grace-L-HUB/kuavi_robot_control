# ROBOT-API v1.1.1
Base URLs:

# 机器人信息
## POST 获取机器人信息
- **接口地址**：`POST /woosh/robot/RobotInfo`
- **请求体**
```json
{
  "robotId": 30001
}
```

### 请求参数
|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|body|body|object|否|请求消息体|none|
|» robotId|body|integer|否|机器人ID|仅向调度系统请求时需赋值|

### 返回示例（成功）
```json
{
  "body": {
    "abnormalCodes": {
      "scs": []
    },
    "battery": {
      "batteryCycle": 0,
      "chargeCycle": 0,
      "chargeState": 1,
      "health": 0,
      "power": 93,
      "robotId": 30001,
      "tempMax": 0
    },
    "deviceState": {
      "state": 3
    },
    "genral": {
      "displayModel": "Robase200",
      "modelData": {
        "height": 1550,
        "length": 1250,
        "load": 150,
        "weight": 50,
        "width": 670
      },
      "serialNumber": 30001,
      "serviceId": "RB2000030100000000Z",
      "type": 1,
      "urdfName": "wooshmodel_robase200_cp_y",
      "version": {
        "rc": "1.0.0-1",
        "system": "UROS20210720"
      }
    },
    "hardwareState": {
      "beacon": 0,
      "board": 0,
      "camera": [0, 0],
      "crash": 0,
      "esb": 0,
      "imu": 0,
      "lidar": [0, 0],
      "lift": [0, 0],
      "light": 0,
      "magnetism": 0,
      "motor": [0, 0],
      "plc": 0,
      "power": 0,
      "roller": [0, 0],
      "seanner": 0,
      "sonar": [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
      "tractor": 0
    },
    "mode": {
      "ctrl": 1,
      "work": 3
    },
    "model": {
      "model": [
        {"x": 0.35, "y": 0.265, "z": 0},
        {"x": 0.4, "y": 0.215, "z": 0},
        {"x": 0.4, "y": -0.215, "z": 0},
        {"x": 0.35, "y": -0.265, "z": 0},
        {"x": -0.35, "y": -0.265, "z": 0},
        {"x": -0.4, "y": -0.215, "z": 0},
        {"x": -0.4, "y": 0.215, "z": 0},
        {"x": -0.35, "y": 0.265, "z": 0}
      ],
      "robotId": 30001
    },
    "network": {
      "isConnected": false,
      "robotIp": "172.20.254.63",
      "schIp": ""
    },
    "operationState": {
      "nav": 2,
      "robotId": 30001
    },
    "poseSpeed": {
      "mapId": 0,
      "mileage": 0,
      "pose": {
        "theta": -0.255771846,
        "x": 4.23276472,
        "y": -6.6727581
      },
      "robotId": 30001
    },
    "robotId": 30001,
    "scene": {
      "mapId": 0,
      "mapName": "wooshmap",
      "robotId": 30001,
      "sceneName": "wooshmap",
      "version": "147"
    },
    "setting": {
      "allow": {
        "autoCharge": true,
        "autoPark": true,
        "goodsCheck": true,
        "mechanismCheck": false
      },
      "identity": {
        "name": "30001"
      },
      "power": {
        "alarm": 5,
        "full": 98,
        "idle": 80,
        "low": 20
      },
      "server": {
        "ip": "172.20.8.85",
        "port": 5420
      }
    },
    "state": 4,
    "statusCodes": {
      "scs": [
        {
          "code": "130104000000",
          "level": 0,
          "msg": "收到新的导航任务，导航避障开始",
          "robotId": 30001,
          "state": 4,
          "taskId": "68240893101",
          "time": "1682409385879",
          "type": 1
        },
        {
          "code": "130104000031",
          "level": 1,
          "msg": "避障成功",
          "robotId": 30001,
          "state": 4,
          "taskId": "68240893101",
          "time": "1682409386081",
          "type": 1
        }
      ]
    },
    "taskProc": {
      "action": {
        "state": 1,
        "type": 1,
        "waitId": 0
      },
      "dest": "U5",
      "msg": "",
      "robotId": 30001,
      "robotTaskId": "68240893101",
      "state": 3,
      "time": 1682409349,
      "type": 1
    }
  },
  "msg": "",
  "ok": true,
  "type": "woosh.robot.RobotInfo"
}
```

### 返回结果
|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|OK|成功|Inline|

### 返回数据结构（200）
|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» body|object|true|none|应答消息体|详见字典“woosh.robot.RobotInfo”|
|» msg|string|true|none|应答状态消息|none|
|» ok|boolean|true|none|应答结果|TRUE: 成功, FALSE: 失败|
|» type|string|true|none|应答消息类型|woosh.robot.RobotInfo|

---

## POST 获取常规信息
- **接口地址**：`POST /woosh/robot/General`
- **请求体**
```json
{
  "robotId": 30001
}
```

### 请求参数
|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|body|body|object|否|请求消息体|none|
|» robotId|body|integer|否|机器人ID|仅向调度系统请求时需赋值|

### 返回示例（成功）
```json
{
  "body": {
    "displayModel": "Robase200",
    "modelData": {
      "height": 1550,
      "length": 1250,
      "load": 150,
      "weight": 50,
      "width": 670
    },
    "serialNumber": 30001,
    "serviceId": "RB2000030100000000Z",
    "type": 1,
    "urdfName": "wooshmodel_robase200_cp_y",
    "version": {
      "rc": "1.0.0-1",
      "system": "UROS20210720"
    }
  },
  "msg": "",
  "ok": true,
  "type": "woosh.robot.General"
}
```

### 返回结果
|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|OK|成功|Inline|

---

## POST 获取配置信息
- **接口地址**：`POST /woosh/robot/Setting`
- **请求体**
```json
{
  "robotId": 30001
}
```

### 返回示例（成功）
```json
{
  "body": {
    "allow": {
      "autoCharge": true,
      "autoPark": true,
      "goodsCheck": true,
      "mechanismCheck": false
    },
    "identity": {
      "name": "30001"
    },
    "power": {
      "alarm": 5,
      "full": 98,
      "idle": 80,
      "low": 20
    },
    "server": {
      "ip": "172.20.8.85",
      "port": 5420
    }
  },
  "msg": "",
  "ok": true,
  "type": "woosh.robot.Setting"
}
```

---

## POST 获取机器人状态
- **接口地址**：`POST /woosh/robot/RobotState`
- **请求体**
```json
{
  "robotId": 30001
}
```

### 返回示例（成功）
```json
{
  "body": {
    "robotId": 30001,
    "state": 4
  },
  "msg": "",
  "ok": true,
  "type": "woosh.robot.RobotState"
}
```

---

## POST 获取模式信息
- **接口地址**：`POST /woosh/robot/Mode`
- **请求体**
```json
{
  "robotId": 30001
}
```

### 返回示例（成功）
```json
{
  "body": {
    "ctrl": 1,
    "work": 3
  },
  "msg": "",
  "ok": true,
  "type": "woosh.robot.Mode"
}
```

---

## POST 获取位姿速度
- **接口地址**：`POST /woosh/robot/PoseSpeed`
- **请求体**
```json
{
  "robotId": 30001
}
```

### 返回示例（成功）
```json
{
  "body": {
    "mapId": 0,
    "mileage": 0,
    "pose": {
      "theta": 2.89655304,
      "x": -8.88137531,
      "y": 0.518660784
    },
    "robotId": 30001
  },
  "msg": "",
  "ok": true,
  "type": "woosh.robot.PoseSpeed"
}
```

---

## POST 获取电池信息
- **接口地址**：`POST /woosh/robot/Battery`
- **请求体**
```json
{
  "robotId": 30001
}
```

### 返回示例（成功）
```json
{
  "body": {
    "batteryCycle": 0,
    "chargeCycle": 0,
    "chargeState": 1,
    "health": 0,
    "power": 91,
    "robotId": 30001,
    "tempMax": 0
  },
  "msg": "",
  "ok": true,
  "type": "woosh.robot.Battery"
}
```

---

## POST 获取网络信息
- **接口地址**：`POST /woosh/robot/Network`
- **请求体**
```json
{
  "robotId": 30001
}
```

### 返回示例（成功）
```json
{
  "body": {
    "isConnected": false,
    "robotIp": "172.20.254.63",
    "schIp": ""
  },
  "msg": "",
  "ok": true,
  "type": "woosh.robot.Network"
}
```

---

## POST 获取场景信息
- **接口地址**：`POST /woosh/robot/Scene`
- **请求体**
```json
{
  "robotId": 30001
}
```

### 返回示例（成功）
```json
{
  "body": {
    "mapId": 0,
    "mapName": "wooshmap",
    "sceneName": "wooshmap",
    "version": "147"
  },
  "msg": "",
  "ok": true,
  "type": "woosh.robot.Scene"
}
```

---

## POST 获取任务进度
- **接口地址**：`POST /woosh/robot/TaskProc`
- **请求体**
```json
{
  "robotId": 30001
}
```

### 返回示例（成功）
```json
{
  "body": {
    "action": {
      "state": 1,
      "type": 1,
      "waitId": 0
    },
    "dest": "K10",
    "msg": "",
    "robotId": 30001,
    "robotTaskId": "68241434201",
    "state": 3,
    "time": 1682416646,
    "type": 1
  },
  "msg": "",
  "ok": true,
  "type": "woosh.robot.TaskProc"
}
```

---

## POST 获取设备状态
- **接口地址**：`POST /woosh/robot/DeviceState`
- **请求体**
```json
{
  "robotId": 30001
}
```

### 返回示例（成功）
```json
{
  "body": {
    "robotId": 30001,
    "state": 3
  },
  "msg": "",
  "ok": true,
  "type": "woosh.robot.DeviceState"
}
```

---

## POST 获取硬件状态
- **接口地址**：`POST /woosh/robot/HardwareState`
- **请求体**
```json
{
  "robotId": 30001
}
```

### 返回示例（成功）
```json
{
  "body": {
    "beacon": 0,
    "board": 0,
    "camera": [0, 0],
    "crash": 0,
    "esb": 0,
    "imu": 0,
    "lidar": [0, 0],
    "lift": [0, 0],
    "light": 0,
    "magnetism": 0,
    "motor": [0, 0],
    "plc": 0,
    "power": 0,
    "robotId": 30001,
    "roller": [0, 0],
    "seanner": 0,
    "sonar": [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    "tractor": 0
  },
  "msg": "",
  "ok": true,
  "type": "woosh.robot.HardwareState"
}
```

---

## POST 获取运行状态
- **接口地址**：`POST /woosh/robot/OperationState`
- **请求体**
```json
{
  "robotId": 30001
}
```

### 返回示例（成功）
```json
{
  "body": {
    "nav": 2,
    "robotId": 30001
  },
  "msg": "",
  "ok": true,
  "type": "woosh.robot.OperationState"
}
```

---

## POST 获取机器人模型
- **接口地址**：`POST /woosh/robot/Model`
- **请求体**
```json
{
  "robotId": 30001
}
```

### 返回示例（成功）
```json
{
  "body": {
    "model": [
      {"x": 0.35, "y": 0.265, "z": 0},
      {"x": 0.4, "y": 0.215, "z": 0},
      {"x": 0.4, "y": -0.215, "z": 0},
      {"x": 0.35, "y": -0.265, "z": 0},
      {"x": -0.35, "y": -0.265, "z": 0},
      {"x": -0.4, "y": -0.215, "z": 0},
      {"x": -0.4, "y": 0.215, "z": 0},
      {"x": -0.35, "y": 0.265, "z": 0}
    ],
    "robotId": 30001
  },
  "msg": "",
  "ok": true,
  "type": "woosh.robot.Model"
}
```

---

## POST 获取历史任务
- **接口地址**：`POST /woosh/robot/TaskHistory`
- **说明**：任务状态信息(最近五十条)
- **请求体**
```json
{}
```

### 返回示例（成功）
```json
{
  "body": {
    "tes": [
      {
        "dest": "",
        "msg": "",
        "robotTaskId": "68242105502",
        "state": 7,
        "time": 1682421626,
        "type": 0
      }
    ]
  },
  "msg": "Request succeed",
  "ok": true,
  "type": "woosh.robot.TaskHistory"
}
```

---

## POST 获取状态码信息
- **接口地址**：`POST /woosh/robot/count/StatusCodes`
- **请求体**
```json
{
  "robotId": 30001
}
```

### 返回示例（成功）
```json
{
  "body": {
    "scs": [
      {
        "code": "130104000061",
        "level": 1,
        "msg": "直行",
        "state": 4,
        "taskId": "68241437402",
        "time": "1682420920688",
        "type": 1
      }
    ]
  },
  "msg": "",
  "ok": true,
  "type": "woosh.robot.count.StatusCodes"
}
```

---

## POST 获取异常码信息
- **接口地址**：`POST /woosh/robot/count/AbnormalCodes`
- **请求体**
```json
{
  "robotId": 30001
}
```

### 返回示例（成功）
```json
{
  "body": {
    "scs": []
  },
  "msg": "",
  "ok": true,
  "type": "woosh.robot.count.AbnormalCodes"
}
```

---

## POST 请求导航路径
- **接口地址**：`POST /woosh/robot/NavPath`
- **请求体**
```json
{}
```

## POST 请求全局规划路径
- **接口地址**：`POST /woosh/robot/PlanPath`
- **请求体**
```json
{}
```

# 机器人配置
## POST 设置机器人标识
- **接口地址**：`POST /woosh/robot/setting/Identity`
- **请求体**
```json
{
  "robotId": 30001,
  "name": "A666"
}
```

### 返回示例（成功）
```json
{
  "body": {
    "name": "A666",
    "robotId": 30001
  },
  "msg": "Request succeed",
  "ok": true,
  "type": "woosh.robot.setting.Identity"
}
```

---

## POST 设置连接服务器配置
- **接口地址**：`POST /woosh/robot/setting/Server`
- **请求体**
```json
{
  "robotId": 30001,
  "ip": "172.20.8.85",
  "port": 5420
}
```

---

## POST 开关自主回充
- **接口地址**：`POST /woosh/robot/setting/AutoCharge`
- **请求体**
```json
{
  "robotId": 30001,
  "allow": true
}
```

---

## POST 开关自主泊车
- **接口地址**：`POST /woosh/robot/setting/AutoPark`
- **请求体**
```json
{
  "allow": true,
  "robotId": 0
}
```

---

## POST 开关货物检测
- **接口地址**：`POST /woosh/robot/setting/GoodsCheck`
- **请求体**
```json
{
  "allow": true,
  "robotId": 0
}
```

---

## POST 机器人电量配置
- **接口地址**：`POST /woosh/robot/setting/Power`
- **请求体**
```json
{
  "robotId": 30001,
  "alarm": 10,
  "low": 20,
  "idle": 80,
  "full": 98
}
```

# 场景地图
## POST 获取场景列表
- **接口地址**：`POST /woosh/map/SceneList`
- **请求体**
```json
{}
```

### 返回示例（成功）
```json
{
  "body": {
    "scenes": [
      {
        "maps": ["wooshmap"],
        "name": "wooshmap"
      }
    ]
  },
  "msg": "",
  "ok": true,
  "type": "woosh.map.SceneList"
}
```

---

## POST 获取场景数据
- **接口地址**：`POST /woosh/map/SceneData`
- **请求体**
```json
{
  "name": "wooshmap"
}
```

---

## POST 下载地图
- **接口地址**：`POST /woosh/map/Download`
- **请求体**
```json
{
  "sceneName": "wooshmap"
}
```

---

## POST 上传地图
- **接口地址**：`POST /woosh/map/Upload`
- **请求体**
```json
{}
```

---

## POST 修改地图或场景名
- **接口地址**：`POST /woosh/map/Rename`
- **请求体**
```json
{
  "old_scene_name": "string",
  "new_scene_name": "string",
  "old_map_name": "string",
  "new_map_name": "string"
}
```

---

## POST 删除场景或地图
- **接口地址**：`POST /woosh/map/Delete`
- **请求体**
```json
{
  "scene_name": "string",
  "map_name": "string"
}
```

---

## POST 场景文件MD5请求
- **接口地址**：`POST /woosh/map/SceneMd5`
- **请求体**
```json
{
  "sceneName": "wooshmap"
}
```

---

## POST 场景同步
- **接口地址**：`POST /woosh/map/SceneSync`
- **请求体**
```json
{}
```

---

## POST 获取场景数据(Easy)
- **接口地址**：`POST /woosh/map/SceneDataEasy`
- **请求体**
```json
{
  "name": ""
}
```

# 机器人请求
## POST 切换工作模式
- **接口地址**：`POST /woosh/robot/SwitchWorkMode`
- **请求体**
```json
{
  "mode": 3
}
```

---

## POST 初始化机器人
- **接口地址**：`POST /woosh/robot/InitRobot`
- **请求体**
```json
{
  "isRecord": true
}
```

---

## POST 设置机器人位姿
- **接口地址**：`POST /woosh/robot/SetRobotPose`
- **请求体**
```json
{
  "pose": {
    "x": 12.3,
    "y": 5.6,
    "theta": 1.57
  }
}
```

---

## POST 切换控制模式
- **接口地址**：`POST /woosh/robot/SwitchControlMode`
- **请求体**
```json
{
  "mode": 1
}
```

---

## POST 切换地图
- **接口地址**：`POST /woosh/robot/SwitchMap`
- **请求体**
```json
{
  "sceneName": "wooshmap",
  "mapName": "wooshmap"
}
```

---

## POST 构图请求
- **接口地址**：`POST /woosh/robot/BuildMap`
- **请求体**
```json
{}
```

---

## POST 部署请求
- **接口地址**：`POST /woosh/robot/Deployment`
- **请求体**
```json
{}
```

---

## POST 执行预定义任务
- **接口地址**：`POST /woosh/robot/ExecPreTask`
- **请求体**
```json
{
  "taskSetId": 0
}
```

---

## POST 执行任务
- **接口地址**：`POST /woosh/robot/ExecTask`
- **请求体**
```json
{
  "taskId": 0,
  "type": 0,
  "direction": 0,
  "taskTypeNo": 0,
  "markNo": "string"
}
```

---

## POST 动作指令
- **接口地址**：`POST /woosh/robot/ActionOrder`
- **请求体**
```json
{
  "order": 0
}
```

---

## POST 规划导航路径
- **接口地址**：`POST /woosh/robot/PlanNavPath`
- **请求体**
```json
{
  "start": {
    "x": 0,
    "y": 0,
    "theta": 0
  },
  "end": {
    "x": 0,
    "y": 0,
    "theta": 0
  },
  "tolerance": 0
}
```

---

## POST 改变导航路径
- **接口地址**：`POST /woosh/robot/ChangeNavPath`
- **请求体**
```json
{}
```

---

## POST 改变导航模式
- **接口地址**：`POST /woosh/robot/ChangeNavMode`
- **请求体**
```json
{}
```

---

## POST 语音播报
- **接口地址**：`POST /woosh/robot/Speak`
- **请求体**
```json
{
  "text": "开始前往目标点"
}
```

---

## POST 速度控制
- **接口地址**：`POST /woosh/robot/Twist`
- **请求体**
```json
{}
```

---

## POST 跟随
- **接口地址**：`POST /woosh/robot/Follow`
- **请求体**
```json
{}
```

---

## POST WIFi信息
- **接口地址**：`POST /woosh/robot/RobotWiFi`
- **请求体**
```json
{}
```

---

## POST 设置机器人占用
- **接口地址**：`POST /woosh/robot/SetOccupancy`
- **请求体**
```json
{
  "pose": {
    "x": 12.3,
    "y": 5.6,
    "theta": 1.57
  }
}
```

# 调度请求
## POST 获取调度机器人信息
- **接口地址**：`POST /woosh/dispatch/robot/Robot`
- **请求体**
```json
{
  "id": 30001
}
```

---

## POST 获取调度机器人列表
- **接口地址**：`POST /woosh/dispatch/robot/Robots`
- **请求体**
```json
{}
```

---

## POST 切换场景
- **接口地址**：`POST /woosh/dispatch/system/SwitchScene`
- **请求体**
```json
{
  "name": "wooshmap"
}
```

---

## POST 获取当前场景
- **接口地址**：`POST /woosh/dispatch/system/SceneSettings`
- **请求体**
```json
{}
```

---

## POST 查找任务
- **接口地址**：`POST /woosh/dispatch/task/FindTask`
- **请求体**
```json
{
  "id": 0,
  "gteType": 1,
  "lteType": 2,
  "robotId": 30001,
  "page": 0
}
```

---

## POST 任务指令
- **接口地址**：`POST /woosh/dispatch/task/TaskOrder`
- **请求体**
```json
{
  "id": 681348376,
  "order": 2
}
```

---

## POST 指定机器人充电
- **接口地址**：`POST /woosh/dispatch/system/GotoCharge`
- **请求体**
```json
{
  "robot": 30001
}
```

---

## POST 置顶任务
- **接口地址**：`POST /woosh/dispatch/task/StickTask`
- **请求体**
```json
{
  "id": 681348378,
  "unstick": false
}
```

---

## POST 添加任务
- **接口地址**：`POST /woosh/task/AddTask`
- **请求体**
```json
{
  "tset": {
    "base": {
      "name": "A10-K11",
      "priority": 0,
      "robots": [],
      "rtype": 1
    },
    "custom": {
      "auto_complete": true
    },
    "tasks": [
      {
        "base": {
          "cannot_cancel": false,
          "custom": "",
          "direction": 0,
          "id": 1,
          "mark_no": "A10",
          "name": "A10",
          "type": 1,
          "type_no": 0,
          "wait_time": 0
        }
      }
    ]
  }
}
```

---

## POST 充电配置
- **接口地址**：`POST /woosh/dispatch/system/ChargeSettings`
- **请求体**
```json
{
  "settings": [
    {
      "level": 1,
      "guardPower": 10,
      "lowPower": 20,
      "workPower": 60,
      "fullPower": 100,
      "time": 0
    }
  ]
}
```

---

## POST 泊车充电记录表
- **接口地址**：`POST /woosh/dispatch/system/PacAccountList`
- **请求体**
```json
{}
```

---

## POST 修改泊车充电记录
- **接口地址**：`POST /woosh/dispatch/system/PacAccount`
- **请求体**
```json
{}
```

# 设备请求/callbox
## POST 上线
- **接口地址**：`POST /woosh/device/callbox/Online`
- **请求体**
```json
{
  "callbox": {
    "no": "cb110",
    "keyNum": 4,
    "keys": [{"id": 1},{"id": 2},{"id": 3},{"id": 4}]
  }
}
```

---

## POST 下线
- **接口地址**：`POST /woosh/device/callbox/Offline`
- **请求体**
```json
{
  "no": "cb110"
}
```

---

## POST 呼叫
- **接口地址**：`POST /woosh/device/callbox/Call`
- **请求体**
```json
{
  "event": {
    "no": "cb110",
    "key": 1,
    "type": 1
  }
}
```

---

## POST 获取指定呼叫盒
- **接口地址**：`POST /woosh/device/callbox/Callbox`
- **请求体**
```json
{
  "no": "cb110"
}
```

---

## POST 获取呼叫盒列表
- **接口地址**：`POST /woosh/device/callbox/Callboxs`
- **请求体**
```json
{}
```

---

## POST 获取呼叫器列表
- **接口地址**：`POST /woosh/device/callbox/Callers`
- **请求体**
```json
{}
```

# 测试
## POST etcd watch
- **接口地址**：`POST /v3alpha/watch`
- **请求体**
```json
{}
```

## GET google
- **接口地址**：`GET /`
- **返回示例**
```json
{}
```

# 数据模型