# LSLidar N10P ROS 2 双雷达数据接口使用与移植

本文对应镭神 LSLidar N10P/N10Plus 串口版雷达，适用于 ROS 2 Humble 和工作空间 `~/wheeltec_ros2`。当前配置使用两个串口雷达：前雷达固定为 `/dev/lidar_front`，后雷达固定为 `/dev/lidar_rear`。

两个雷达由同一个 launch 文件启动，原始数据分别发布到独立话题；另有 `pointcloud_fusion` 包将两路点云变换到统一坐标系后合并。

## 1. 数据话题

| 雷达 | LaserScan 话题 | PointCloud2 话题 | 坐标系 |
| --- | --- | --- | --- |
| 前雷达 | `/front/scan` | `/front/lslidar_point_cloud` | `laser_front` |
| 后雷达 | `/rear/scan` | `/rear/lslidar_point_cloud` | `laser_rear` |

话题类型：

| 话题类型 | ROS 消息类型 | 含义 |
| --- | --- | --- |
| LaserScan | `sensor_msgs/msg/LaserScan` | 二维激光扫描数据，距离单位为米，角度单位为弧度 |
| PointCloud2 | `sensor_msgs/msg/PointCloud2` | 雷达点云，坐标单位为米 |

每条消息都包含 `header.stamp` 时间戳和 `header.frame_id` 坐标系标识。当前两个雷达的扫描频率配置为 10 Hz，N10Plus 串口波特率为 460800。

当前配置对两个雷达都屏蔽自身坐标系后方 180°：

```text
屏蔽角度：90° 到 270°
保留角度：0° 到 90°、270° 到 360°
```

配置参数使用 0.01° 为单位：

```yaml
angle_disable_min: [9000]
angle_disable_max: [27000]
```

角度屏蔽同时作用于 LaserScan 和 PointCloud2。这里的“前方/后方”以每个雷达自身的 0° 方向为基准；如果雷达实际安装方向不同，应调整雷达安装方向或修改角度范围。

## 2. 编译与启动

确认两个雷达已经连接，并检查串口设备：

```bash
ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

安装 udev 固定别名后，默认设备为：

```text
前雷达：/dev/lidar_front
后雷达：/dev/lidar_rear
```

用户需要属于 `dialout` 组，否则无法读写串口：

```bash
id -nG
```

如果没有 `dialout`：

```bash
sudo usermod -aG dialout "$USER"
```

执行后注销并重新登录。

编译雷达消息和驱动：

```bash
source /opt/ros/humble/setup.bash
cd ~/wheeltec_ros2
colcon build --symlink-install \
  --packages-select lslidar_msgs lslidar_driver
source install/setup.bash
```

为两台雷达安装固定串口别名。规则脚本按 USB 转串口的硬件序列号匹配，不依赖 `ttyACM` 编号：

```bash
cd ~/wheeltec_ros2/src/lslidar_ros2
sudo ./wheeltec_udev.sh
```

拔出并重新插入两台雷达后检查：

```bash
ls -l /dev/lidar_front /dev/lidar_rear
```

当前脚本中的序列号为：

```text
前雷达适配器：0002
后雷达适配器：5B8E671812
```

换电脑或更换 USB 转串口适配器时，如果序列号不同，先运行以下命令查看新序列号：

```bash
for dev in /dev/ttyACM* /dev/ttyUSB*; do
  [ -e "$dev" ] || continue
  echo "=== $dev ==="
  udevadm info --query=property --name="$dev" \
    | grep -E 'ID_VENDOR_ID|ID_MODEL_ID|ID_SERIAL_SHORT'
done
```

然后修改 `wheeltec_udev.sh` 顶部的 `FRONT_SERIAL` 和 `REAR_SERIAL`，重新执行脚本。

启动双雷达：

```bash
source /opt/ros/humble/setup.bash
source ~/wheeltec_ros2/install/setup.bash

ros2 launch lslidar_driver lsn10p_double_uart_launch.py \
  front_port:=/dev/lidar_front \
  rear_port:=/dev/lidar_rear
```

启动文件位置：

```text
~/wheeltec_ros2/src/lslidar_ros2/lslidar_driver/launch/lsn10p_double_uart_launch.py
```

双雷达参数文件位置：

```text
~/wheeltec_ros2/src/lslidar_ros2/lslidar_driver/config/lslidar_n10p_double_uart.yaml
```

启动文件使用同一份公共参数文件，然后分别覆盖两个节点的串口、坐标系和相对话题名称。参数文件使用 `/**` 通配节点配置，因此 `/front/lslidar_driver_node` 和 `/rear/lslidar_driver_node` 都能读取 `lidar_model: "N10Plus"` 等公共参数。

如果两个设备名称不是默认值，可以在启动时覆盖：

```bash
ros2 launch lslidar_driver lsn10p_double_uart_launch.py \
  front_port:=/dev/ttyUSB0 \
  rear_port:=/dev/ttyUSB1
```

不要同时启动单雷达 launch 和双雷达 launch，否则两个进程可能争用同一个串口。

## 3. 调用接口

### 包内提供的接口

| 接口 | 用途 |
| --- | --- |
| `lslidar_driver_node` | 读取一个 N10P 串口并发布雷达数据 |
| `lsn10p_double_uart_launch.py` | 同时启动前后两个 N10P 串口驱动节点 |
| `lslidar_n10p_double_uart.yaml` | 两个节点共用的 N10P 参数、坐标和角度屏蔽配置 |

### 命令行查看接口

查看所有雷达话题：

```bash
ros2 topic list | grep -E 'front|rear'
```

查看前雷达数据：

```bash
ros2 topic echo /front/scan --once
ros2 topic echo /front/lslidar_point_cloud --once
```

查看后雷达数据：

```bash
ros2 topic echo /rear/scan --once
ros2 topic echo /rear/lslidar_point_cloud --once
```

查看发布频率：

```bash
ros2 topic hz /front/scan
ros2 topic hz /rear/scan
ros2 topic hz /front/lslidar_point_cloud
ros2 topic hz /rear/lslidar_point_cloud
```

查看消息类型和发布者：

```bash
ros2 topic info /front/scan -v
ros2 topic info /rear/scan -v
ros2 topic info /front/lslidar_point_cloud -v
ros2 topic info /rear/lslidar_point_cloud -v
```

### Python 订阅示例

应用程序不需要直接打开串口，只需要订阅驱动发布的话题。下面示例同时订阅两个雷达的 LaserScan：

```python
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


class LidarClient(Node):
    def __init__(self):
        super().__init__('lidar_client')
        self.front_subscription = self.create_subscription(
            LaserScan,
            '/front/scan',
            self.on_front_scan,
            10,
        )
        self.rear_subscription = self.create_subscription(
            LaserScan,
            '/rear/scan',
            self.on_rear_scan,
            10,
        )

    def on_front_scan(self, message):
        valid_ranges = [
            distance for distance in message.ranges
            if message.range_min <= distance <= message.range_max
        ]
        self.get_logger().info(
            f'front scan: {len(valid_ranges)} valid points, '
            f'frame={message.header.frame_id}'
        )

    def on_rear_scan(self, message):
        valid_ranges = [
            distance for distance in message.ranges
            if message.range_min <= distance <= message.range_max
        ]
        self.get_logger().info(
            f'rear scan: {len(valid_ranges)} valid points, '
            f'frame={message.header.frame_id}'
        )


def main():
    rclpy.init()
    node = LidarClient()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
```

如果需要读取点云，可以订阅对应的 `PointCloud2` 话题：

```python
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2


def on_front_points(message):
    points = point_cloud2.read_points(
        message,
        field_names=('x', 'y', 'z'),
        skip_nans=True,
    )
    first_point = next(iter(points), None)
    print('front first point:', first_point)
```

订阅点云时使用：

```python
self.create_subscription(
    PointCloud2,
    '/front/lslidar_point_cloud',
    on_front_points,
    10,
)
```

后雷达只需把话题改为 `/rear/lslidar_point_cloud`。

## 4. 实际运行步骤

先打开**终端一**启动双雷达驱动，并保持运行：

```bash
source /opt/ros/humble/setup.bash
source ~/wheeltec_ros2/install/setup.bash
ros2 launch lslidar_driver lsn10p_double_uart_launch.py
```

日志中应分别出现：

```text
Only accepting serial data from: /dev/lidar_front
Only accepting serial data from: /dev/lidar_rear
Lidar model: N10Plus
Successfully opened serial port ... at 460800 baud.
```

再打开**终端二**查看数据：

```bash
source /opt/ros/humble/setup.bash
source ~/wheeltec_ros2/install/setup.bash

ros2 topic hz /front/scan
ros2 topic hz /rear/scan
```

正常情况下两个话题都应接近 10 Hz。停止驱动时在终端一按 `Ctrl+C`。

使用 RViz2 查看两路扫描：

```bash
source /opt/ros/humble/setup.bash
source ~/wheeltec_ros2/install/setup.bash
rviz2
```

在 RViz2 中：

1. 将 `Fixed Frame` 设置为 `laser_front` 或其他已经存在的固定坐标系。
2. 添加一个 `LaserScan`，Topic 选择 `/front/scan`。
3. 再添加一个 `LaserScan`，Topic 选择 `/rear/scan`。
4. 需要查看点云时添加两个 `PointCloud2`，分别选择 `/front/lslidar_point_cloud` 和 `/rear/lslidar_point_cloud`。

### 双雷达点云融合

当前融合节点发布 `/points_fused`，消息坐标系为 `base_link`。启动前后雷达驱动后，另开终端启动融合：

```bash
source /opt/ros/humble/setup.bash
source ~/wheeltec_ros2/install/setup.bash
ros2 launch pointcloud_fusion fuse_lidars.launch.py \
  front_yaw:=0.0 \
  rear_yaw:=3.141592653589793
```

目前先按两台雷达背靠背设置临时 TF：前雷达 yaw 为 `0`，后雷达 yaw 为 `pi`，两台雷达平移均暂设为 `0`。真实安装坐标确定后，按实测值替换 `front_x/y/z/yaw` 和 `rear_x/y/z/yaw` 参数；位置单位为米，角度单位为弧度。错误外参会导致融合点云错位。

RViz2 查看融合结果时设置：

```text
Fixed Frame: base_link
PointCloud2 Topic: /points_fused
```

检查融合数据：

```bash
ros2 topic hz /points_fused
ros2 topic echo /points_fused --once --field header
```

正常情况下融合话题约为 10 Hz，消息 `frame_id` 为 `base_link`。原始前后雷达话题仍可单独查看。每套双雷达驱动和融合 launch 只启动一次，避免串口争用和重复 TF。

## 5. 移植到其他 ROS 2 工作空间

1. 将以下目录复制到目标工作空间的 `src/` 下：

   ```text
   ~/wheeltec_ros2/src/lslidar_ros2/lslidar_msgs
   ~/wheeltec_ros2/src/lslidar_ros2/lslidar_driver
   ```

2. 保留 `lslidar_msgs` 的消息和服务定义，以及 `lslidar_driver` 的 `src/`、`include/`、`config/`、`launch/` 和 `rviz/`。
3. 安装依赖。Humble 示例：

   ```bash
   sudo apt update
   sudo apt install python3-colcon-common-extensions \
     ros-humble-diagnostic-updater libpcap-dev \
     libpcl-all-dev ros-humble-pcl-conversions
   ```

4. 在目标工作空间编译：

   ```bash
   source /opt/ros/humble/setup.bash
   cd ~/wheeltec_ros2
   colcon build --symlink-install \
     --packages-select lslidar_msgs lslidar_driver
   source install/setup.bash
   ```

5. 确认目标机器的两个串口名称，并按实际名称启动：

   ```bash
   ros2 launch lslidar_driver lsn10p_double_uart_launch.py \
     front_port:=/dev/lidar_front \
     rear_port:=/dev/lidar_rear
   ```

串口版 N10P 使用 460800 baud。双雷达 launch 默认使用 `/dev/lidar_front` 和 `/dev/lidar_rear`，因此不受 `/dev/ttyACM0`、`/dev/ttyACM1` 等动态编号影响。

## 6. 常见检查

- **找不到 `/dev/lidar_front` 或 `/dev/lidar_rear`**：重新执行 `sudo ./wheeltec_udev.sh`，拔插雷达并检查序列号是否与脚本一致。
- **串口已断开或重新插拔后无数据**：检查 `/dev/lidar_front` 和 `/dev/lidar_rear` 是否仍指向当前设备；不要依赖可能变化的 `/dev/ttyACM0`、`/dev/ttyACM1` 编号，并用稳定设备名重新启动驱动。
- **权限不足**：运行 `id -nG`，确认用户在 `dialout` 组；修改组后注销并重新登录。
- **Unable to open serial port**：确认没有同时运行单雷达 launch、另一个雷达节点或串口工具。
- **Lidar model error**：确认使用的是双雷达 launch，且 YAML 第一行是 `/**:`；两个节点需要读到 `lidar_model: "N10Plus"`。
- **只启动一个雷达**：确认前后端口不同，不能把两个参数都设置成同一个设备。
- **没有 LaserScan 数据**：检查 `/front/scan` 和 `/rear/scan`，不要只检查 `/scan`；双雷达话题带有命名空间。
- **只有点云没有扫描**：确认 `publish_scan: true`，并检查 `laserscan_topic` 是否为相对名称 `scan`。
- **角度屏蔽方向不对**：当前屏蔽范围是每个雷达自身坐标系的 90° 到 270°；根据实际安装朝向调整 `angle_disable_min/max`。
- **RViz 看不到数据**：查看原始数据时选择 `/front/scan`、`/rear/scan` 或对应点云话题，并使用存在的 TF 坐标系；查看融合数据时选择 `Fixed Frame: base_link`、Topic `/points_fused`，并确认融合 launch 正在运行。
- **融合话题没有数据**：确认前后原始点云都有发布、融合 launch 只运行一份，并检查 `base_link` 到 `laser_front`、`laser_rear` 的 TF 是否存在。

常用检查命令：

```bash
ros2 node list
ros2 topic list | grep -E 'front|rear'
ros2 topic info /front/scan -v
ros2 topic info /rear/scan -v
ros2 topic hz /front/scan
ros2 topic hz /rear/scan
```
