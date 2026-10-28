# WITMotion IMU ROS 2 使用与移植说明

本文档适用于本目录中的 `wit_ros2_imu` 驱动。驱动通过串口读取维特智能（WITMotion）IMU 数据，并发布 ROS 2 标准 `sensor_msgs/msg/Imu` 消息以及包含欧拉角的自定义消息。

## 1. 功能概览

ROS 2 包名：`wit_ros2_imu`

节点可执行文件：`wit_ros2_imu`

默认参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `port` | `/dev/imu_usb` | 串口设备路径 |
| `baudrate` | `921600` | 串口波特率 |
| `protocol` | `TTL_STD` | 通信协议，见下文 |
| `modbusID` | `80` | RS485 设备地址，十进制 `80` 即十六进制 `0x50` |
| `output_rate_hz` | `500` | TTL 模式下配置 IMU 输出频率 |
| `configure_output_rate` | `true` | 启动时是否写入并保存 TTL 输出频率 |

支持的协议参数：

- `TTL_STD`：TTL 标准精度协议
- `TTL_HIGH`：TTL 高精度协议
- `CAN_STD`：CAN 标准精度协议
- `CAN_HIGH`：CAN 高精度协议
- `RS485_STD`：RS485 标准精度协议
- `RS485_HIGH`：RS485 高精度协议

## 2. 发布的话题

节点发布以下话题：

| 话题 | 消息类型 | 说明 |
| --- | --- | --- |
| `imu/data` | `sensor_msgs/msg/Imu` | 加速度、角速度和由欧拉角转换得到的四元数 |
| `imu/ImuDataWithRPY` | `imu_msg/msg/ImuData` | `Imu` 消息加 roll、pitch、yaw |

默认情况下话题是相对话题名，节点未设置命名空间时实际名称为 `/imu/data` 和 `/imu/ImuDataWithRPY`。消息的 `header.frame_id` 固定为 `imu_link`，因此在 RViz 或融合定位节点中使用前，需要提供对应的 TF，例如 `base_link -> imu_link`。

## 3. 工作区结构

`wit_ros2_imu` 依赖同一个工作区中的自定义消息包 `imu_msg`，迁移时不能只复制 IMU 包：

```text
wheeltec_ros2/
└── src/
    ├── imu_msg/
    │   ├── msg/ImuData.msg
    │   ├── CMakeLists.txt
    │   └── package.xml
    └── wit_ros2_imu/
        ├── config/imu.yaml
        ├── launch/wit_ros2_imu.launch.py
        ├── script/imu_usb.rules
        ├── script/bind_usb.sh
        ├── setup.py
        └── wit_ros2_imu/
            └── wit_ros2_imu.py
```

如果目标工作区已经有 `imu_msg`，请确认消息定义和接口一致；否则需要将本项目的 `imu_msg` 一并复制到目标工作区的 `src` 下。

## 4. 依赖安装

以下命令以 Ubuntu 22.04、ROS 2 Humble 为例：

```bash
sudo apt update
sudo apt install python3-serial python3-numpy
```

确认 ROS 2 环境已加载：

```bash
source /opt/ros/humble/setup.bash
```

## 5. 编译安装

将 `imu_msg` 和 `wit_ros2_imu` 放入目标 ROS 2 工作区的 `src` 后，在工作区根目录执行：

```bash
cd ~/wheeltec_ros2
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select imu_msg wit_ros2_imu
source install/setup.bash
```

如果目标工作区中还有其他包，也可以执行完整编译：

```bash
colcon build --symlink-install
source install/setup.bash
```

确认包已经被 ROS 2 找到：

```bash
ros2 pkg prefix imu_msg
ros2 pkg prefix wit_ros2_imu
```

## 6. 串口设备配置

### 6.1 临时使用实际串口

先查看设备：

```bash
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

可以直接把实际设备传给 launch：

```bash
ros2 launch wit_ros2_imu wit_ros2_imu.launch.py \
  port:=/dev/ttyUSB0
```

如果设备是 `/dev/ttyACM0`，将参数替换为 `/dev/ttyACM0`。当前驱动默认使用 `/dev/imu_usb`，这个软链接只有在 udev 规则匹配成功后才会出现。

### 6.2 固定设备名

当前仓库提供的规则文件 `script/imu_usb.rules` 匹配以下 USB 转串口芯片：

```text
Vendor ID: 1a86
Product ID: 7523
```

安装规则：

```bash
cd ~/wheeltec_ros2/src/wit_ros2_imu/script
sudo ./bind_usb.sh
```

重新插拔 IMU 后检查：

```bash
ls -l /dev/imu_usb
```

如果没有生成软链接，使用下面的命令查看实际 VID/PID：

```bash
lsusb
udevadm info -q property -n /dev/ttyUSB0 | grep -E 'ID_VENDOR_ID|ID_MODEL_ID'
```

然后按实际的 `idVendor` 和 `idProduct` 修改 `imu_usb.rules`。如果系统设备名是 `/dev/ttyACM0`，当前规则中的 `KERNEL=="ttyUSB*"` 也需要改成匹配 `ttyACM*`，或者直接使用实际串口路径。

当前规则设置了 `MODE:=0777`，便于快速调试，但会给所有本地用户开放串口权限。正式部署时建议使用 `GROUP="dialout", MODE="0660"`，并将运行 ROS 2 的用户加入 `dialout` 组：

```bash
sudo usermod -aG dialout "$USER"
```

加入用户组后需要重新登录系统。

## 7. 启动方式

### 7.1 使用默认参数

```bash
source /opt/ros/humble/setup.bash
source ~/wheeltec_ros2/install/setup.bash
ros2 launch wit_ros2_imu wit_ros2_imu.launch.py
```

### 7.2 TTL 标准协议

```bash
ros2 launch wit_ros2_imu wit_ros2_imu.launch.py \
  port:=/dev/imu_usb \
  baudrate:=921600 \
  protocol:=TTL_STD \
  output_rate_hz:=500 \
  configure_output_rate:=true
```

`output_rate_hz` 支持：`1`、`2`、`5`、`10`、`20`、`50`、`100`、`200`、`500`、`1000`。启动时如果 `configure_output_rate` 为 `true`，驱动会向 TTL 设备写入输出频率并保存配置。

### 7.3 TTL 高精度协议

```bash
ros2 launch wit_ros2_imu wit_ros2_imu.launch.py \
  port:=/dev/imu_usb \
  protocol:=TTL_HIGH \
  output_rate_hz:=500
```

### 7.4 RS485 协议

```bash
ros2 launch wit_ros2_imu wit_ros2_imu.launch.py \
  port:=/dev/ttyUSB0 \
  baudrate:=921600 \
  protocol:=RS485_STD \
  modbusID:=80 \
  configure_output_rate:=false
```

RS485 模式下驱动会轮询以下寄存器地址：

| 地址 | 数据 |
| --- | --- |
| `0x34` | 加速度 |
| `0x37` | 角速度 |
| `0x3A` | 磁场 |
| `0x3D` | 角度 |

RS485 高精度模式使用 `RS485_HIGH`。`configure_output_rate` 只对 TTL 协议执行写频率操作，RS485/CAN 模式不会通过该参数配置输出频率。

### 7.5 不使用 launch 文件直接启动

也可以直接使用 ROS 2 参数覆盖：

```bash
ros2 run wit_ros2_imu wit_ros2_imu --ros-args \
  -p port:=/dev/ttyUSB0 \
  -p baudrate:=921600 \
  -p protocol:=TTL_STD \
  -p output_rate_hz:=100 \
  -p configure_output_rate:=false
```

## 8. 数据验证

启动节点后，先确认节点存在：

```bash
ros2 node list
```

查看话题和消息类型：

```bash
ros2 topic list -t | grep -E 'imu/data|ImuDataWithRPY'
```

查看数据：

```bash
ros2 topic echo /imu/data
ros2 topic echo /imu/ImuDataWithRPY
```

查看发布频率：

```bash
ros2 topic hz /imu/data
```

查看连接和 QoS：

```bash
ros2 topic info -v /imu/data
```

正常情况下，`/imu/data` 的 `header.frame_id` 应为 `imu_link`，并且 `linear_acceleration`、`angular_velocity` 和 `orientation` 会持续更新。

## 9. 坐标系和数据单位注意事项

1. 当前代码将所有 IMU 消息的坐标系写为 `imu_link`。如果机器人使用其他坐标系名称，需要修改 `wit_ros2_imu.py` 中的 `imuMsg.header.frame_id`，或者在系统中发布正确的静态 TF。
2. 角速度发布单位为 ROS 标准要求的 `rad/s`。
3. 标准精度角度数据从度转换为弧度后用于生成四元数；高精度角度数据按千分之一度转换。
4. 当前代码使用 `raw_acc * 16 / 32768` 填入 `linear_acceleration`，没有额外乘以标准重力加速度 `9.80665`。如果设备原始加速度单位是 `g`，那么该字段数值实际上仍是 `g`，并不严格符合 `sensor_msgs/Imu` 要求的 `m/s^2`。接入 robot_localization 等融合节点前，应确认设备协议和实际单位，必要时在 `publishImu()` 中乘以 `9.80665`。
5. 当前消息的协方差矩阵保持默认值 0。使用 EKF/UKF 前建议根据传感器数据手册填写合理的协方差。
6. 当前驱动把姿态角直接转换为四元数，并不执行完整的姿态融合。磁力计数据会被解析，但不会填入 `sensor_msgs/Imu` 的磁场字段，因为该消息没有磁力计字段。

## 10. 常见问题

### 10.1 `Permission denied`

检查当前用户是否有串口权限：

```bash
groups
ls -l /dev/ttyUSB0 /dev/imu_usb 2>/dev/null
```

将用户加入 `dialout` 后重新登录，或检查 udev 规则是否匹配设备。

### 10.2 `could not open port` 或 `No such file or directory`

确认设备路径是否存在：

```bash
ls -l /dev/ttyUSB* /dev/ttyACM* /dev/imu_usb 2>/dev/null
```

先使用实际路径启动，确认硬件通信正常后再配置 udev 固定名称。

### 10.3 节点启动但没有话题数据

按以下顺序排查：

1. 检查串口是否被其他串口工具或节点占用。
2. 检查 `protocol` 是否与 IMU 的实际接口模式一致。
3. 检查波特率是否与设备当前配置一致。
4. TTL 模式下关闭频率写入，避免不匹配的设备拒绝配置：`configure_output_rate:=false`。
5. 直接查看终端输出，确认是否出现 `Serial opened` 和持续的 Accel/Gyro/Angle 打印。

### 10.4 RS485 模式没有数据

确认 `modbusID` 与设备地址一致，并确认 RS485 转换器对应的串口设备路径正确。RS485 模式不是 TTL 的连续主动上报模式，驱动会按 `0x34`、`0x37`、`0x3A`、`0x3D` 依次轮询。

### 10.5 RViz 中看不到 IMU

RViz 不会自动显示 `sensor_msgs/Imu` 的所有字段。先使用 `ros2 topic echo /imu/data` 确认数据，再在 RViz 中添加 `IMU` 显示，并将话题设为 `/imu/data`。如果出现 TF 错误，设置正确的 Fixed Frame，并发布 `base_link` 到 `imu_link` 的 TF。

## 11. 移植检查清单

- [ ] 目标系统已安装 ROS 2，并执行了对应的 `setup.bash`。
- [ ] `imu_msg` 和 `wit_ros2_imu` 都已复制到目标工作区的 `src`。
- [ ] 已安装 `python3-serial` 和 `python3-numpy`。
- [ ] 已根据设备实际 VID/PID 配置 udev 规则，或直接使用实际串口路径。
- [ ] `protocol`、`baudrate`、`modbusID` 与硬件配置一致。
- [ ] 已编译并 source 目标工作区的 `install/setup.bash`。
- [ ] `/imu/data` 能持续发布，消息 `frame_id` 为预期值。
- [ ] 已为 `imu_link` 配置机器人 TF。
- [ ] 接入融合算法前已确认加速度单位和协方差。
