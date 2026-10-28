import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LifecycleNode


def generate_launch_description():
    package_share = get_package_share_directory('lslidar_driver')
    driver_config = os.path.join(
        package_share, 'config', 'lslidar_n10p_double_uart.yaml'
    )

    front_port = LaunchConfiguration('front_port')
    rear_port = LaunchConfiguration('rear_port')

    front_node = LifecycleNode(
        package='lslidar_driver',
        executable='lslidar_driver_node',
        name='lslidar_driver_node',
        namespace='front',
        output='screen',
        parameters=[driver_config, {
            'serial_port': front_port,
            'frame_id': 'laser_front',
            'pointcloud_topic': 'lslidar_point_cloud',
            'laserscan_topic': 'scan',
        }],
    )

    rear_node = LifecycleNode(
        package='lslidar_driver',
        executable='lslidar_driver_node',
        name='lslidar_driver_node',
        namespace='rear',
        output='screen',
        parameters=[driver_config, {
            'serial_port': rear_port,
            'frame_id': 'laser_rear',
            'pointcloud_topic': 'lslidar_point_cloud',
            'laserscan_topic': 'scan',
        }],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'front_port',
            default_value='/dev/lidar_front',
            description='Serial port for the front N10P',
        ),
        DeclareLaunchArgument(
            'rear_port',
            default_value='/dev/lidar_rear',
            description='Serial port for the rear N10P',
        ),
        front_node,
        rear_node,
    ])
