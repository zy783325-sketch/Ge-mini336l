# Orbbec ROS 2 相机数据接口使用与移植

本文对应 `orbbec_camera` ROS 2 包，适用于 ROS 2 Humble、Linux x86_64 和 OrbbecSDK v1。驱动使用标准 ROS 2 消息发布图像、IMU 和点云；应用程序可以用任意 ROS 2 客户端订阅，也可以使用文中的 Python `CameraClient`。

## 1. 数据话题

| 话题 | ROS 消息类型 | 含义 |
| --- | --- | --- |
| `/camera/color/image_raw` | `sensor_msgs/msg/Image` | 彩色相机图像。通常为 `rgb8`，具体编码见消息的 `encoding` 字段。 |
| `/camera/depth/image_raw` | `sensor_msgs/msg/Image` | 深度图，编码为 `16UC1`。每像素是 SDK 输出的原始无符号 16 位深度值；不要直接假设单位为米。 |
| `/camera/ir_left/image_raw` | `sensor_msgs/msg/Image` | 左红外图像，通常为 `mono8` 或 `mono16`，以 `encoding` 字段为准。 |
| `/camera/ir_right/image_raw` | `sensor_msgs/msg/Image` | 右红外图像，通常为 `mono8` 或 `mono16`，以 `encoding` 字段为准。 |
| `/camera/imu/accel` | `geometry_msgs/msg/Vector3Stamped` | 三轴加速度，`vector.x/y/z` 单位为 `m/s^2`。 |
| `/camera/imu/gyro` | `geometry_msgs/msg/Vector3Stamped` | 三轴角速度，`vector.x/y/z` 单位为 `rad/s`。 |
| `/camera/depth/points` | `sensor_msgs/msg/PointCloud2` | 从深度帧生成的 XYZ 点云，坐标单位为米；当前不包含 RGB 颜色字段。 |

每个图像和向量消息都有 `header.stamp` 时间戳和 `header.frame_id` 坐标系标识。IMU 分别发布加速度和角速度，不发布融合后的姿态四元数。设备不支持或未开启的传感器不会产生对应数据。

## 2. 编译与启动

确保 Orbbec 相机没有被 `OBMultiStream` 等其他进程占用，然后执行：

```bash
source /opt/ros/humble/setup.bash
cd /home/yang/OrbbecSDK/ros2
colcon build --packages-select orbbec_camera
source install/setup.bash
ros2 run orbbec_camera orbbec_camera_node
```

也可以用 launch 启动：

```bash
ros2 launch orbbec_camera orbbec_camera.launch.py
```

节点会持续运行，按 `Ctrl+C` 停止。另开终端检查数据：

```bash
source /opt/ros/humble/setup.bash
source /home/yang/OrbbecSDK/ros2/install/setup.bash
ros2 topic list
ros2 topic hz /camera/color/image_raw
ros2 topic hz /camera/imu/accel
ros2 topic hz /camera/depth/points
```

查看彩色图像可运行 `ros2 run rqt_image_view rqt_image_view`，再选择 `/camera/color/image_raw`。RViz2 中添加 `PointCloud2` 显示并选择 `/camera/depth/points` 可查看点云。

## 3. 调用接口

### 包内提供的接口

包提供一个驱动可执行程序、一个 launch 启动文件，以及 Python 订阅辅助类：

| 接口 | 用途 |
| --- | --- |
| `orbbec_camera_node` | 启动相机驱动，打开设备并发布相机数据。 |
| `ros2 launch orbbec_camera orbbec_camera.launch.py` | 通过 launch 启动同一个驱动节点。 |
| `orbbec_camera.CameraClient` | Python 订阅类，一次创建全部数据话题的订阅；把消息交给构造时提供的回调。 |

`CameraClient` 可传入以下可选回调参数。每个回调接收一个标准 ROS 消息对象；不传回调时，该数据会被接收后忽略。

| 回调参数 | 订阅的话题 | 回调收到的消息类型 |
| --- | --- | --- |
| `on_color` | `/camera/color/image_raw` | `sensor_msgs.msg.Image` |
| `on_depth` | `/camera/depth/image_raw` | `sensor_msgs.msg.Image` |
| `on_ir_left` | `/camera/ir_left/image_raw` | `sensor_msgs.msg.Image` |
| `on_ir_right` | `/camera/ir_right/image_raw` | `sensor_msgs.msg.Image` |
| `on_accel` | `/camera/imu/accel` | `geometry_msgs.msg.Vector3Stamped` |
| `on_gyro` | `/camera/imu/gyro` | `geometry_msgs.msg.Vector3Stamped` |
| `on_points` | `/camera/depth/points` | `sensor_msgs.msg.PointCloud2` |

图像回调可读取 `width`、`height`、`encoding`、`step`、`data`；向量回调可读取 `vector.x/y/z`；点云回调可读取 `width`、`height`、`fields`、`data`。具体话题的含义和单位见“数据话题”章节。

### 调用方法

这里有两个分别运行的程序：

1. **相机驱动**连接 Orbbec 相机，读取相机数据并发布成 ROS 2 话题。它就是 `orbbec_camera_node`。
2. **你的 Python 程序**不直接打开相机，而是订阅驱动发布的话题。收到一条消息时，ROS 2 自动调用你登记的函数。

可以把话题理解成数据通道，把回调理解成“有新数据时要执行的函数”。例如，`on_color(image)` 是你定义的函数；每收到一张彩色图，ROS 2 就把图像消息交给这个函数。示例里的 `print(...)` 只是展示如何访问消息内容，你可以把它替换为自己的图像处理、保存或算法调用。

先定义回调函数，再把函数作为对应参数传给 `CameraClient`。`rclpy.spin(client)` 会让订阅程序持续等待消息并运行回调，所以程序会一直运行，直到按 `Ctrl+C`。

### 示例代码

```python
import rclpy
from orbbec_camera import CameraClient


def on_color(image):
    print("color:", image.width, image.height, image.encoding, len(image.data))


def on_depth(image):
    print("depth:", image.width, image.height, image.encoding)


def on_accel(message):
    v = message.vector
    print("accel m/s^2:", v.x, v.y, v.z)


def on_gyro(message):
    v = message.vector
    print("gyro rad/s:", v.x, v.y, v.z)


def on_points(cloud):
    print("point cloud:", cloud.width, "points, frame:", cloud.header.frame_id)


rclpy.init()
client = CameraClient(
    on_color=on_color,
    on_depth=on_depth,
    on_ir_left=lambda msg: print("left IR:", msg.width, msg.height, msg.encoding),
    on_ir_right=lambda msg: print("right IR:", msg.width, msg.height, msg.encoding),
    on_accel=on_accel,
    on_gyro=on_gyro,
    on_points=on_points,
)
try:
    rclpy.spin(client)
finally:
    client.destroy_node()
    rclpy.shutdown()
```

代码中几个关键位置：

- `def on_color(image):` 定义收到彩色图时要运行的函数。`image` 是标准 ROS 图像消息；宽、高、编码和像素字节分别可从 `image.width`、`image.height`、`image.encoding`、`image.data` 读取。
- `on_accel` 和 `on_gyro` 从 `message.vector.x/y/z` 读取三个轴的数值，单位分别是 `m/s^2` 和 `rad/s`。
- `CameraClient(on_color=on_color, ...)` 把函数与对应话题关联起来。例如“彩色话题来数据时调用 `on_color`”。
- `rclpy.spin(client)` 开始持续收消息。没有这一行，订阅程序很快就会退出，也来不及处理数据。
- `finally` 中的两行在退出时释放 ROS 节点并关闭 ROS Python 客户端。

### 实际运行步骤

先编译一次包：

```bash
source /opt/ros/humble/setup.bash
cd /home/yang/OrbbecSDK/ros2
colcon build --packages-select orbbec_camera
```

打开**终端一**启动相机驱动，让它保持运行：

```bash
source /opt/ros/humble/setup.bash
source /home/yang/OrbbecSDK/ros2/install/setup.bash
ros2 run orbbec_camera orbbec_camera_node
```

桌面上已提供可直接运行的示例文件 `read_camera.py`。打开**终端二**运行订阅程序：

```bash
source /opt/ros/humble/setup.bash
source /home/yang/OrbbecSDK/ros2/install/setup.bash
python3 /home/yang/桌面/read_camera.py
```

终端二会打印收到的数据摘要。终端一负责相机和发布话题，终端二负责接收数据和执行你的回调；两边都要运行。停止时分别在对应终端按 `Ctrl+C`。不要再启动第二个相机驱动，因为相机设备通常不能被两个程序同时打开。

深度图像的像素数据在 `image.data`，但其原始 `16UC1` 值不要直接当作米；若需要米制 XYZ，订阅 `/camera/depth/points`。点云示例只打印点数和坐标系名称，实际点数据在 `PointCloud2` 的字段中。

对于希望直接订阅而不依赖 Python 辅助类的程序，可订阅上表话题，使用对应标准 ROS 消息类型。点云可通过 `sensor_msgs_py.point_cloud2.read_points` 读取 XYZ 字段。

## 4. 移植到其他 ROS 2 工作空间

1. 将 `/home/yang/OrbbecSDK/ros2/orbbec_camera` 整个目录复制到目标工作空间的 `src/` 下。保留其中的 `CMakeLists.txt`、`package.xml`、`src/`、`orbbec_camera/` 和 `launch/`。
2. 目标机器需要安装匹配架构的 OrbbecSDK。此包需要 SDK 源码/开发目录，目录内应有 `OrbbecSDKConfig.cmake`、`include/` 和对应平台的 `lib/`；仅复制 ROS 包不包含 SDK 头文件。
3. 安装 ROS 依赖。Humble 示例：

   ```bash
   sudo apt install ros-humble-rclcpp ros-humble-rclpy \
     ros-humble-sensor-msgs ros-humble-sensor-msgs-py \
     ros-humble-geometry-msgs ros-humble-ament-cmake-python \
     ros-humble-launch ros-humble-launch-ros
   ```

4. source 目标 ROS 发行版，并将 `ORBBEC_SDK_ROOT` 指向目标机器上的 SDK 根目录编译：

   ```bash
   source /opt/ros/humble/setup.bash
   cd ~/robot_ws
   colcon build --packages-select orbbec_camera \
     --cmake-args -DORBBEC_SDK_ROOT=/path/to/OrbbecSDK
   source install/setup.bash
   ```

5. 如设备权限不足，按 SDK 提供的 udev 规则安装脚本/规则并重新插拔相机。运行驱动前关闭其他正在占用相机的程序。

此包的 CMake 会将所选 SDK 平台目录中的 `.so` 运行库安装到 ROS 包旁，节点通过相对 RPATH 加载它们。当前实现针对 Linux x86_64；移植到 ARM 或其他操作系统时，必须使用相应平台的 SDK 库，并检查 CMake 中 `linux_x64` 相关安装逻辑及运行时依赖。ROS 发行版不同也需安装对应发行版的依赖包。

## 5. 常见检查

- 设备占用：退出 `OBMultiStream`、另一个 ROS 相机节点或其他访问相机的程序。
- 没有某个话题的数据：确认相机型号支持该传感器，并检查节点启动日志和 `ros2 topic hz <话题>`。
- 找不到包：重新 source `/opt/ros/<发行版>/setup.bash` 和目标工作空间的 `install/setup.bash`。
- 图像画面不可见：驱动只发布话题，不会自动打开窗口；使用 `rqt_image_view` 或 RViz2 订阅。
