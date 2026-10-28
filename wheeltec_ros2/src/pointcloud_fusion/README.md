# 双雷达点云融合

本包订阅 Wheeltec 双雷达驱动发布的前、后雷达点云，将两路点云分别通过 TF 变换到同一个目标坐标系，再合并为一条 `sensor_msgs/msg/PointCloud2`。

默认输入：

- `/front/lslidar_point_cloud`，frame `laser_front`
- `/rear/lslidar_point_cloud`，frame `laser_rear`

默认输出：

- `/points_fused`，frame `base_link`

## 编译

在 ROS 2 Humble 环境中：

```bash
cd ~/wheeltec_ros2
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-select pointcloud_fusion
source install/setup.bash
```

## 启动

先启动双雷达驱动，再启动融合节点：

```bash
ros2 launch pointcloud_fusion fuse_lidars.launch.py
```

当前 launch 会发布以下静态 TF：

- `base_link -> laser_front`，預設平移为零，朝向为零
- `base_link -> laser_rear`，預設平移为零，yaw 为 `pi`

这些默认值只是让节点能启动的示例值，不代表雷达的真实安装外参。请根据雷达相对车体中心的测量位置和朝向设置参数，单位为米和弧度。例如：

```bash
ros2 launch pointcloud_fusion fuse_lidars.launch.py \
  front_x:=0.30 front_y:=0.0 front_z:=0.20 front_yaw:=0.0 \
  rear_x:=-0.30 rear_y:=0.0 rear_z:=0.20 rear_yaw:=3.14159265
```

这里的数值仅为格式示例，应替换成实际测量的安装外参。若机器人已有 URDF/TF 在发布 `base_link` 到两个雷达的变换，不要同时启动本 launch 中的重复静态 TF。可以直接运行融合可执行文件：

```bash
ros2 run pointcloud_fusion pointcloud_fusion
```

融合节点参数包括 `front_topic`、`rear_topic`、`output_topic`、`target_frame`、`sync_slop`、`queue_size` 和 `tf_timeout`。输出点云的字段布局沿用前雷达点云；两路字段布局不同则丢弃该组消息并报告错误。

## 验证与 RViz

```bash
ros2 topic hz /points_fused
ros2 topic echo /points_fused --once --field header
```

RViz 的 `Fixed Frame` 设为 `base_link`，添加 `PointCloud2` 显示并选择 `/points_fused`。

若日志提示找不到 transform，检查：

```bash
ros2 run tf2_ros tf2_echo base_link laser_front
ros2 run tf2_ros tf2_echo base_link laser_rear
```

## 注意事项

- 两台雷达必须各自有正确的 TF 外参。错误外参会导致点云重叠、错位或方向相反。
- 两路点云使用近似时间同步，默认最大时间差为 `0.08` 秒；运动较快时应缩小该值或使用硬件同步。
- 本包负责坐标变换和拼接，不做体素降采样、去噪或运动畸变校正。
- 两个驱动实例各启动一次即可。重复启动双雷达 launch 会造成重复串口访问和重复点云发布。
