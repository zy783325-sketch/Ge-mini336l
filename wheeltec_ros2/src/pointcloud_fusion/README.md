# 双雷达点云融合

本包将前、后两台雷达点云变换到 `base_link` 后合并发布。

输入：

- `/front/lslidar_point_cloud`，frame：`laser_front`
- `/rear/lslidar_point_cloud`，frame：`laser_rear`

输出：

- `/points_fused`，frame：`base_link`

## 编译

```bash
cd ~/wheeltec_ros2
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select pointcloud_fusion
source install/setup.bash
```

## 启动

当前两台雷达使用稳定设备名：

- 前雷达：`/dev/lidar_front`
- 后雷达：`/dev/lidar_rear`

终端 1，启动雷达驱动：

```bash
ros2 launch lslidar_driver lsn10p_double_uart_launch.py \
  front_port:=/dev/lidar_front \
  rear_port:=/dev/lidar_rear
```

终端 2，启动融合节点：

```bash
ros2 launch pointcloud_fusion fuse_lidars.launch.py \
  front_yaw:=0.0 \
  rear_yaw:=3.141592653589793
```

当前临时假设为两台雷达背靠背：平移均为 `0`，前雷达 yaw 为 `0`，后雷达 yaw 为 `pi`。真实 TF 坐标确定后，修改 `front_x/y/z/yaw` 和 `rear_x/y/z/yaw` 参数即可，位置单位为米，角度单位为弧度。

每套驱动和融合 launch 只启动一次，避免重复占用串口和发布重复 TF。

## RViz

在 RViz 中设置：

```text
Fixed Frame: base_link
PointCloud2 Topic: /points_fused
```

当前默认 RViz 配置已设置为上述值。

## 检查

```bash
ros2 topic hz /front/lslidar_point_cloud
ros2 topic hz /rear/lslidar_point_cloud
ros2 topic hz /points_fused
ros2 topic echo /points_fused --once --field header
```

正常情况下，三路点云约为 `10 Hz`，融合消息的 `frame_id` 应为 `base_link`。

如果没有输出，检查 TF：

```bash
ros2 run tf2_ros tf2_echo base_link laser_front
ros2 run tf2_ros tf2_echo base_link laser_rear
```

如果设备名不存在，检查：

```bash
ls -l /dev/lidar_front /dev/lidar_rear
```

不要使用已经失效的 `/dev/ttyACM0` 和 `/dev/ttyACM1`。
