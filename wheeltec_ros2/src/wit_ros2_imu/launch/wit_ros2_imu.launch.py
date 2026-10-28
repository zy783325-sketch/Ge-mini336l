from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import PythonExpression
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'port',
            default_value='/dev/imu_usb',
            description='Serial device path',
        ),
        DeclareLaunchArgument(
            'baudrate',
            default_value='921600',
            description='Serial baud rate',
        ),
        DeclareLaunchArgument(
            'protocol',
            default_value='TTL_STD',
            description=(
                'TTL_STD, TTL_HIGH, CAN_STD, CAN_HIGH, RS485_STD or RS485_HIGH'
            ),
        ),
        DeclareLaunchArgument(
            'modbusID',
            default_value='80',
            description='RS485 device address in decimal (0x50 = 80)',
        ),
        DeclareLaunchArgument(
            'output_rate_hz',
            default_value='500',
            description='WIT TTL output rate in Hz',
        ),
        DeclareLaunchArgument(
            'configure_output_rate',
            default_value='true',
            description='Configure and save the WIT TTL output rate on startup',
        ),
        Node(
            package='wit_ros2_imu',
            executable='wit_ros2_imu',
            name='wit_ros2_imu',
            output='screen',
            parameters=[{
                'port': LaunchConfiguration('port'),
                'baudrate': PythonExpression([
                    'int("', LaunchConfiguration('baudrate'), '")'
                ]),
                'protocol': LaunchConfiguration('protocol'),
                'modbusID': PythonExpression([
                    'int("', LaunchConfiguration('modbusID'), '")'
                ]),
                'output_rate_hz': PythonExpression([
                    'int("', LaunchConfiguration('output_rate_hz'), '")'
                ]),
                'configure_output_rate': LaunchConfiguration(
                    'configure_output_rate'
                ),
            }],
        ),
    ])
