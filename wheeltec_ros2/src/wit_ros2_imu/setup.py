from glob import glob
from setuptools import find_packages, setup

package_name = 'wit_ros2_imu'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='bgzerol',
    maintainer_email='bgzerol@todo.todo',
    description='ROS 2 driver for WitMotion IMU devices',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'wit_ros2_imu = wit_ros2_imu.wit_ros2_imu:main'
        ],
    },
)
