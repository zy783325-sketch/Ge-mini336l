from setuptools import setup


package_name = 'pointcloud_fusion'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/fuse_lidars.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Wheeltec ROS 2 users',
    maintainer_email='maintainer@example.com',
    description='Transform and merge front and rear lidar PointCloud2 data.',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'pointcloud_fusion = pointcloud_fusion.node:main',
        ],
    },
)
