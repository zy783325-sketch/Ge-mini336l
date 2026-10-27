#include <cstring>
#include <cmath>
#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "geometry_msgs/msg/vector3_stamped.hpp"
#include "libobsensor/ObSensor.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/image_encodings.hpp"
#include "sensor_msgs/msg/image.hpp"
#include "sensor_msgs/msg/point_cloud2.hpp"
#include "sensor_msgs/point_cloud2_iterator.hpp"

class OrbbecCameraNode : public rclcpp::Node {
public:
    OrbbecCameraNode()
        : Node("orbbec_camera"), pipeline_() {
        color_publisher_ = create_publisher<sensor_msgs::msg::Image>("camera/color/image_raw", 10);
        depth_publisher_ = create_publisher<sensor_msgs::msg::Image>("camera/depth/image_raw", 10);
        ir_left_publisher_ = create_publisher<sensor_msgs::msg::Image>("camera/ir_left/image_raw", 10);
        ir_right_publisher_ = create_publisher<sensor_msgs::msg::Image>("camera/ir_right/image_raw", 10);
        accel_publisher_ = create_publisher<geometry_msgs::msg::Vector3Stamped>("camera/imu/accel", rclcpp::SensorDataQoS());
        gyro_publisher_ = create_publisher<geometry_msgs::msg::Vector3Stamped>("camera/imu/gyro", rclcpp::SensorDataQoS());
        point_cloud_publisher_ = create_publisher<sensor_msgs::msg::PointCloud2>("camera/depth/points", rclcpp::SensorDataQoS());

        auto config = std::make_shared<ob::Config>();
        enableStream(config, OB_SENSOR_COLOR);
        enableStream(config, OB_SENSOR_DEPTH);
        enableStream(config, OB_SENSOR_IR_LEFT);
        enableStream(config, OB_SENSOR_IR_RIGHT);
        pipeline_.start(config, [this](std::shared_ptr<ob::FrameSet> frames) { publishFrames(frames); });

        try {
            imu_pipeline_ = std::make_shared<ob::Pipeline>(pipeline_.getDevice());
            auto imu_config = std::make_shared<ob::Config>();
            imu_config->enableAccelStream();
            imu_config->enableGyroStream();
            imu_pipeline_->start(imu_config, [this](std::shared_ptr<ob::FrameSet> frames) { publishImu(frames); });
        }
        catch (const ob::Error &e) {
            RCLCPP_WARN(get_logger(), "IMU streams unavailable: %s", e.getMessage());
            imu_pipeline_.reset();
        }

        point_cloud_filter_.setCameraParam(pipeline_.getCameraParam());
        point_cloud_filter_.setCreatePointFormat(OB_FORMAT_POINT);
    }

    ~OrbbecCameraNode() override {
        if (imu_pipeline_) {
            imu_pipeline_->stop();
        }
        pipeline_.stop();
    }

private:
    void enableStream(const std::shared_ptr<ob::Config> &config, OBSensorType type) {
        try {
            auto profiles = pipeline_.getStreamProfileList(type);
            if (!profiles || profiles->count() == 0) {
                return;
            }
            auto profile = std::const_pointer_cast<ob::StreamProfile>(profiles->getProfile(OB_PROFILE_DEFAULT));
            config->enableStream(profile);
        }
        catch (const ob::Error &e) {
            RCLCPP_WARN(get_logger(), "Skipping sensor %d: %s", static_cast<int>(type), e.getMessage());
        }
    }

    void publishImage(const std::shared_ptr<ob::Frame> &frame,
                      const rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr &publisher,
                      const std::string &frame_id) {
        if (!frame) {
            return;
        }

        auto video = frame->as<ob::VideoFrame>();
        const auto width = video->width();
        const auto height = video->height();
        std::string encoding;
        uint32_t step = 0;
        switch (video->format()) {
        case OB_FORMAT_RGB:
            encoding = sensor_msgs::image_encodings::RGB8;
            step = width * 3;
            break;
        case OB_FORMAT_BGR:
            encoding = sensor_msgs::image_encodings::BGR8;
            step = width * 3;
            break;
        case OB_FORMAT_RGBA:
            encoding = sensor_msgs::image_encodings::RGBA8;
            step = width * 4;
            break;
        case OB_FORMAT_BGRA:
            encoding = sensor_msgs::image_encodings::BGRA8;
            step = width * 4;
            break;
        case OB_FORMAT_Y8:
            encoding = sensor_msgs::image_encodings::MONO8;
            step = width;
            break;
        case OB_FORMAT_Y16:
        case OB_FORMAT_Z16:
            encoding = frame->type() == OB_FRAME_DEPTH ? sensor_msgs::image_encodings::TYPE_16UC1
                                                       : sensor_msgs::image_encodings::MONO16;
            step = width * 2;
            break;
        default:
            if (frame->type() == OB_FRAME_COLOR) {
                auto color = frame->as<ob::ColorFrame>();
                ob::FormatConvertFilter converter;
                switch (video->format()) {
                case OB_FORMAT_MJPG: converter.setFormatConvertType(FORMAT_MJPG_TO_RGB); break;
                case OB_FORMAT_YUYV: converter.setFormatConvertType(FORMAT_YUYV_TO_RGB); break;
                case OB_FORMAT_UYVY: converter.setFormatConvertType(FORMAT_UYVY_TO_RGB); break;
                default:
                    RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 5000, "Unsupported image format: %d", video->format());
                    return;
                }
                color = converter.process(color)->as<ob::ColorFrame>();
                auto image = std::make_unique<sensor_msgs::msg::Image>();
                image->header.stamp = now();
                image->header.frame_id = frame_id;
                image->width = color->width();
                image->height = color->height();
                image->encoding = sensor_msgs::image_encodings::RGB8;
                image->is_bigendian = false;
                image->step = image->width * 3;
                const auto size = image->step * image->height;
                image->data.resize(size);
                std::memcpy(image->data.data(), color->data(), size);
                publisher->publish(std::move(image));
                return;
            }
            RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 5000, "Unsupported image format: %d", video->format());
            return;
        }

        auto image = std::make_unique<sensor_msgs::msg::Image>();
        image->header.stamp = now();
        image->header.frame_id = frame_id;
        image->width = width;
        image->height = height;
        image->encoding = encoding;
        image->is_bigendian = false;
        image->step = step;
        const auto size = frame->dataSize();
        image->data.resize(size);
        std::memcpy(image->data.data(), frame->data(), size);
        publisher->publish(std::move(image));
    }

    void publishFrames(const std::shared_ptr<ob::FrameSet> &frames) {
        try {
            if (!frames) {
                return;
            }
            publishImage(frames->colorFrame(), color_publisher_, "camera_color_optical_frame");
            publishImage(frames->depthFrame(), depth_publisher_, "camera_depth_optical_frame");
            publishImage(frames->getFrame(OB_FRAME_IR_LEFT), ir_left_publisher_, "camera_ir_left_optical_frame");
            publishImage(frames->getFrame(OB_FRAME_IR_RIGHT), ir_right_publisher_, "camera_ir_right_optical_frame");
            publishPointCloud(frames);
        }
        catch (const ob::Error &e) {
            RCLCPP_ERROR_THROTTLE(get_logger(), *get_clock(), 5000, "Orbbec SDK error: %s", e.getMessage());
        }
    }

    void publishImu(const std::shared_ptr<ob::FrameSet> &frames) {
        if (!frames) {
            return;
        }
        const auto stamp = now();
        if (auto frame = frames->getFrame(OB_FRAME_ACCEL)) {
            const auto value = frame->as<ob::AccelFrame>()->value();
            geometry_msgs::msg::Vector3Stamped message;
            message.header.stamp = stamp;
            message.header.frame_id = "camera_imu_optical_frame";
            message.vector.x = value.x;
            message.vector.y = value.y;
            message.vector.z = value.z;
            accel_publisher_->publish(message);
        }
        if (auto frame = frames->getFrame(OB_FRAME_GYRO)) {
            const auto value = frame->as<ob::GyroFrame>()->value();
            geometry_msgs::msg::Vector3Stamped message;
            message.header.stamp = stamp;
            message.header.frame_id = "camera_imu_optical_frame";
            message.vector.x = value.x;
            message.vector.y = value.y;
            message.vector.z = value.z;
            gyro_publisher_->publish(message);
        }
    }

    void publishPointCloud(const std::shared_ptr<ob::FrameSet> &frames) {
        const auto depth = frames->depthFrame();
        if (!depth) {
            return;
        }
        point_cloud_filter_.setPositionDataScaled(depth->getValueScale());
        auto points_frame = point_cloud_filter_.process(frames);
        if (!points_frame) {
            return;
        }

        const auto count = points_frame->dataSize() / sizeof(OBPoint);
        const auto *points = static_cast<const OBPoint *>(points_frame->data());
        sensor_msgs::msg::PointCloud2 cloud;
        cloud.header.stamp = now();
        cloud.header.frame_id = "camera_depth_optical_frame";
        cloud.height = 1;
        cloud.width = count;
        cloud.is_dense = false;
        sensor_msgs::PointCloud2Modifier modifier(cloud);
        modifier.setPointCloud2FieldsByString(1, "xyz");
        modifier.resize(count);
        sensor_msgs::PointCloud2Iterator<float> x(cloud, "x");
        sensor_msgs::PointCloud2Iterator<float> y(cloud, "y");
        sensor_msgs::PointCloud2Iterator<float> z(cloud, "z");
        for (uint32_t i = 0; i < count; ++i, ++x, ++y, ++z) {
            *x = points[i].x / 1000.0f;
            *y = points[i].y / 1000.0f;
            *z = points[i].z / 1000.0f;
        }
        point_cloud_publisher_->publish(std::move(cloud));
    }

    ob::Pipeline pipeline_;
    std::shared_ptr<ob::Pipeline> imu_pipeline_;
    ob::PointCloudFilter point_cloud_filter_;
    rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr color_publisher_;
    rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr depth_publisher_;
    rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr ir_left_publisher_;
    rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr ir_right_publisher_;
    rclcpp::Publisher<geometry_msgs::msg::Vector3Stamped>::SharedPtr accel_publisher_;
    rclcpp::Publisher<geometry_msgs::msg::Vector3Stamped>::SharedPtr gyro_publisher_;
    rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr point_cloud_publisher_;
};

int main(int argc, char **argv) {
    rclcpp::init(argc, argv);
    try {
        rclcpp::spin(std::make_shared<OrbbecCameraNode>());
    }
    catch (const ob::Error &e) {
        RCLCPP_FATAL(rclcpp::get_logger("orbbec_camera"), "Orbbec SDK error: %s", e.getMessage());
        rclcpp::shutdown();
        return 1;
    }
    rclcpp::shutdown();
    return 0;
}
