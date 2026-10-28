from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    arguments = [
        DeclareLaunchArgument('front_x', default_value='0.0'),
        DeclareLaunchArgument('front_y', default_value='0.0'),
        DeclareLaunchArgument('front_z', default_value='0.0'),
        DeclareLaunchArgument('front_yaw', default_value='0.0'),
        DeclareLaunchArgument('rear_x', default_value='0.0'),
        DeclareLaunchArgument('rear_y', default_value='0.0'),
        DeclareLaunchArgument('rear_z', default_value='0.0'),
        DeclareLaunchArgument('rear_yaw', default_value='3.141592653589793'),
    ]

    transforms = [
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='front_lidar_tf',
            arguments=[
                '--x', LaunchConfiguration('front_x'),
                '--y', LaunchConfiguration('front_y'),
                '--z', LaunchConfiguration('front_z'),
                '--yaw', LaunchConfiguration('front_yaw'),
                '--pitch', '0',
                '--roll', '0',
                '--frame-id', 'base_link',
                '--child-frame-id', 'laser_front',
            ],
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='rear_lidar_tf',
            arguments=[
                '--x', LaunchConfiguration('rear_x'),
                '--y', LaunchConfiguration('rear_y'),
                '--z', LaunchConfiguration('rear_z'),
                '--yaw', LaunchConfiguration('rear_yaw'),
                '--pitch', '0',
                '--roll', '0',
                '--frame-id', 'base_link',
                '--child-frame-id', 'laser_rear',
            ],
        ),
    ]

    fusion = Node(
        package='pointcloud_fusion',
        executable='pointcloud_fusion',
        name='pointcloud_fusion',
        output='screen',
        parameters=[{
            'front_topic': '/front/lslidar_point_cloud',
            'rear_topic': '/rear/lslidar_point_cloud',
            'output_topic': '/points_fused',
            'target_frame': 'base_link',
        }],
    )

    return LaunchDescription(arguments + transforms + [fusion])
