cmake_minimum_required(VERSION 3.8)
project(orbbec_camera)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
set(ORBBEC_SDK_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../.." CACHE PATH "Path to the OrbbecSDK checkout")
find_package(OrbbecSDK REQUIRED CONFIG
  PATHS "${ORBBEC_SDK_ROOT}"
  NO_DEFAULT_PATH)

add_executable(orbbec_camera_node src/orbbec_camera_node.cpp)
target_compile_features(orbbec_camera_node PRIVATE cxx_std_17)
ament_target_dependencies(orbbec_camera_node rclcpp sensor_msgs geometry_msgs)
target_link_libraries(orbbec_camera_node OrbbecSDK::OrbbecSDK)
set_target_properties(orbbec_camera_node PROPERTIES INSTALL_RPATH "$ORIGIN")

install(TARGETS orbbec_camera_node DESTINATION lib/${PROJECT_NAME})
file(GLOB ORBBEC_RUNTIME_LIBRARIES
  "${OrbbecSDK_LIBS_DIR}/*.so*")
install(FILES ${ORBBEC_RUNTIME_LIBRARIES} DESTINATION lib/${PROJECT_NAME})
ament_python_install_package(${PROJECT_NAME})
install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})

ament_package()
