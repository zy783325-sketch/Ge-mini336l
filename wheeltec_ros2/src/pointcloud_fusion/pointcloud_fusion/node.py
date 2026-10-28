import copy
import math
import struct

from message_filters import ApproximateTimeSynchronizer, Subscriber
import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import PointCloud2, PointField
from tf2_ros import Buffer, TransformException, TransformListener


class PointCloudFusion(Node):
    def __init__(self):
        super().__init__('pointcloud_fusion')
        self.declare_parameter('front_topic', '/front/lslidar_point_cloud')
        self.declare_parameter('rear_topic', '/rear/lslidar_point_cloud')
        self.declare_parameter('output_topic', '/points_fused')
        self.declare_parameter('target_frame', 'base_link')
        self.declare_parameter('sync_slop', 0.08)
        self.declare_parameter('queue_size', 10)
        self.declare_parameter('tf_timeout', 0.15)

        front_topic = self.get_parameter('front_topic').value
        rear_topic = self.get_parameter('rear_topic').value
        self.target_frame = self.get_parameter('target_frame').value
        slop = float(self.get_parameter('sync_slop').value)
        queue_size = int(self.get_parameter('queue_size').value)
        self.tf_timeout = float(self.get_parameter('tf_timeout').value)
        lidar_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
        )

        self.publisher = self.create_publisher(
            PointCloud2,
            self.get_parameter('output_topic').value,
            lidar_qos,
        )
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.front_sub = Subscriber(
            self, PointCloud2, front_topic, qos_profile=lidar_qos
        )
        self.rear_sub = Subscriber(
            self, PointCloud2, rear_topic, qos_profile=lidar_qos
        )
        self.synchronizer = ApproximateTimeSynchronizer(
            [self.front_sub, self.rear_sub], queue_size, slop
        )
        self.synchronizer.registerCallback(self.merge_clouds)

        self.get_logger().info(
            f'Fusing {front_topic} and {rear_topic} into '
            f'{self.get_parameter("output_topic").value} '
            f'in frame {self.target_frame}'
        )

    def merge_clouds(self, front, rear):
        try:
            timeout = rclpy.duration.Duration(seconds=self.tf_timeout)
            front_tf = self.tf_buffer.lookup_transform(
                self.target_frame,
                front.header.frame_id,
                rclpy.time.Time.from_msg(front.header.stamp),
                timeout=timeout,
            )
            rear_tf = self.tf_buffer.lookup_transform(
                self.target_frame,
                rear.header.frame_id,
                rclpy.time.Time.from_msg(rear.header.stamp),
                timeout=timeout,
            )
            front_transformed = self.transform_cloud(front, front_tf)
            rear_transformed = self.transform_cloud(rear, rear_tf)
        except TransformException as exc:
            self.get_logger().warning(f'Cannot transform input clouds: {exc}')
            return
        except (ValueError, struct.error) as exc:
            self.get_logger().error(f'Cannot transform input cloud: {exc}')
            return

        if (
            front_transformed.point_step != rear_transformed.point_step
            or front_transformed.fields != rear_transformed.fields
        ):
            self.get_logger().error(
                'Input clouds have incompatible PointCloud2 field layouts'
            )
            return

        merged = PointCloud2()
        merged.header.stamp = front.header.stamp
        merged.header.frame_id = self.target_frame
        merged.height = 1
        merged.width = front_transformed.width + rear_transformed.width
        merged.fields = front_transformed.fields
        merged.is_bigendian = front_transformed.is_bigendian
        merged.point_step = front_transformed.point_step
        merged.row_step = merged.width * merged.point_step
        merged.is_dense = front_transformed.is_dense and rear_transformed.is_dense
        merged.data = front_transformed.data + rear_transformed.data
        self.publisher.publish(merged)

    @staticmethod
    def transform_cloud(cloud, transform):
        fields = {field.name: field for field in cloud.fields}
        if not all(name in fields for name in ('x', 'y', 'z')):
            raise ValueError('PointCloud2 must contain x, y and z fields')

        formats = {PointCloudFusion.float_format(fields[name]) for name in 'xyz'}
        if len(formats) != 1:
            raise ValueError('x, y and z fields must use the same float type')
        value_format = formats.pop()
        endian = '>' if cloud.is_bigendian else '<'
        point_format = endian + value_format
        offsets = [fields[name].offset for name in 'xyz']

        rotation = transform.transform.rotation
        translation = transform.transform.translation
        qx, qy, qz, qw = rotation.x, rotation.y, rotation.z, rotation.w
        tx, ty, tz = translation.x, translation.y, translation.z

        result = copy.copy(cloud)
        result.data = bytearray(cloud.data)
        result.header.frame_id = transform.header.frame_id

        for row in range(cloud.height):
            row_offset = row * cloud.row_step
            for column in range(cloud.width):
                point_offset = row_offset + column * cloud.point_step
                x, y, z = (
                    struct.unpack_from(point_format, result.data, point_offset + offset)[0]
                    for offset in offsets
                )
                ix = 2.0 * (qy * z - qz * y)
                iy = 2.0 * (qz * x - qx * z)
                iz = 2.0 * (qx * y - qy * x)
                ox = x + qw * ix + qy * iz - qz * iy + tx
                oy = y + qw * iy + qz * ix - qx * iz + ty
                oz = z + qw * iz + qx * iy - qy * ix + tz
                for offset, value in zip(offsets, (ox, oy, oz)):
                    struct.pack_into(point_format, result.data, point_offset + offset, value)

        result.data = bytes(result.data)
        return result

    @staticmethod
    def float_format(field):
        if field.datatype == PointField.FLOAT32:
            return 'f'
        if field.datatype == PointField.FLOAT64:
            return 'd'
        raise ValueError(f'{field.name} field must be FLOAT32 or FLOAT64')


def main(args=None):
    rclpy.init(args=args)
    node = PointCloudFusion()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
