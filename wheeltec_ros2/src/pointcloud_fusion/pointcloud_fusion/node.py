from message_filters import ApproximateTimeSynchronizer, Subscriber
import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import PointCloud2
from tf2_ros import Buffer, TransformException, TransformListener
from tf2_sensor_msgs.tf2_sensor_msgs import do_transform_cloud


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
            front_transformed = do_transform_cloud(front, front_tf)
            rear_transformed = do_transform_cloud(rear, rear_tf)
        except TransformException as exc:
            self.get_logger().warning(f'Cannot transform input clouds: {exc}')
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
