from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [Node(package="orbbec_camera", executable="orbbec_camera_node", name="orbbec_camera", output="screen")]
    )
