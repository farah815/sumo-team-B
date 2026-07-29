import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    package_name = 'robo'

    # مسار ملف وصف الروبوت
    urdf_path = os.path.join(get_package_share_directory(package_name), 'urdf', 'sumo.urdf')
    with open(urdf_path, 'r') as infp:
        robot_desc = infp.read()

    # مسار ملف المتاهة الحقيقي الذي أنشأناه
    world_path = os.path.join(get_package_share_directory(package_name), 'worlds', 'maze.sdf')
    
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # 1. تشغيل جازيبو مع ملف المتاهة الخاص بكِ
    start_gazebo_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': f'-r {world_path}'}.items()
    )

    # 2. نشر حالة الروبوت
    start_robot_state_publisher_cmd = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_desc, 'use_sim_time': True}]
    )

    # 3. إسقاط الروبوت في بداية المتاهة بأمان
    spawn_robot_cmd = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-topic', 'robot_description', '-entity', 'sumo_robot', '-x', '0.0', '-y', '2.5', '-z', '0.2'],     
        output='screen'
    )

    # 4. **جسر الاتصال (Bridge)** لربط حركة الروبوت وليدار المحاكاة بـ ROS 2 (السر في حركة الروبوت وقراءاته)
    bridge_cmd = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
            '/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan'
        ],
        output='screen'
    )

    # 5. تشغيل كود الملاحة الخاص بكِ
    start_navigator_node = Node(
        package=package_name,
        executable='navigator_node',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )


    return LaunchDescription([
        start_gazebo_cmd,
        start_robot_state_publisher_cmd,
        spawn_robot_cmd,
        bridge_cmd,
        start_navigator_node  # أضيفي هذه العقدة هنا ليعمل الكود
    ])