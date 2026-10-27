# Orbbec ROS 2 image publisher

This package publishes the color, depth, and infrared frames available from the connected camera:

- `/camera/color/image_raw` (`rgb8`, `bgr8`, `rgba8`, or `bgra8`)
- `/camera/depth/image_raw` (`16UC1`, raw depth values)
- `/camera/ir_left/image_raw`, `/camera/ir_right/image_raw` (`mono8` or `mono16`, depending on available sensors)
- `/camera/imu/accel` (`geometry_msgs/Vector3Stamped`, m/s^2)
- `/camera/imu/gyro` (`geometry_msgs/Vector3Stamped`, rad/s)
- `/camera/depth/points` (`sensor_msgs/PointCloud2`, XYZ in meters)

Build on Linux x86_64 with ROS 2 Humble and this SDK checkout:

```bash
source /opt/ros/humble/setup.bash
cd /home/yang/OrbbecSDK/ros2
colcon build --packages-select orbbec_camera
source install/setup.bash
ros2 run orbbec_camera orbbec_camera_node
```

The package uses the SDK's default profile for each available sensor. Camera permissions may require installing the udev rules from `misc/scripts/99-obsensor-libusb.rules` and reconnecting the device.
