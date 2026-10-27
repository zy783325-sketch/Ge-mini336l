from typing import Callable, Optional

from geometry_msgs.msg import Vector3Stamped
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, PointCloud2


class CameraClient(Node):
    """Subscribe to every data topic published by the Orbbec camera node.

    Callbacks receive standard ROS messages. The application owns spinning this
    node and should destroy it before shutting down rclpy.
    """

    def __init__(
        self,
        node_name: str = "orbbec_camera_client",
        *,
        on_color: Optional[Callable[[Image], None]] = None,
        on_depth: Optional[Callable[[Image], None]] = None,
        on_ir_left: Optional[Callable[[Image], None]] = None,
        on_ir_right: Optional[Callable[[Image], None]] = None,
        on_accel: Optional[Callable[[Vector3Stamped], None]] = None,
        on_gyro: Optional[Callable[[Vector3Stamped], None]] = None,
        on_points: Optional[Callable[[PointCloud2], None]] = None,
    ) -> None:
        super().__init__(node_name)
        self._subscriptions = [
            self.create_subscription(Image, "/camera/color/image_raw", on_color or self._ignore, qos_profile_sensor_data),
            self.create_subscription(Image, "/camera/depth/image_raw", on_depth or self._ignore, qos_profile_sensor_data),
            self.create_subscription(Image, "/camera/ir_left/image_raw", on_ir_left or self._ignore, qos_profile_sensor_data),
            self.create_subscription(Image, "/camera/ir_right/image_raw", on_ir_right or self._ignore, qos_profile_sensor_data),
            self.create_subscription(Vector3Stamped, "/camera/imu/accel", on_accel or self._ignore, qos_profile_sensor_data),
            self.create_subscription(Vector3Stamped, "/camera/imu/gyro", on_gyro or self._ignore, qos_profile_sensor_data),
            self.create_subscription(PointCloud2, "/camera/depth/points", on_points or self._ignore, qos_profile_sensor_data),
        ]

    @staticmethod
    def _ignore(_message: object) -> None:
        pass
