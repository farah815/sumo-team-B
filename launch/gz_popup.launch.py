from launch import LaunchDescription

from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable

from launch.launch_description_sources import PythonLaunchDescriptionSource

from launch_ros.actions import Node

from launch_ros.substitutions import FindPackageShare, FindPackagePrefix

from launch.substitutions import PathJoinSubstitution, Command


def generate_launch_description():

    # Gazebo resource path
    share_dir = PathJoinSubstitution([
        FindPackagePrefix("sumo"),
        "share",
    ])

    env = SetEnvironmentVariable(
        name="GZ_SIM_RESOURCE_PATH",
        value=share_dir
    )


    # Robot xacro
    xacro_file = PathJoinSubstitution([
        FindPackageShare("sumo"),
        "urdf",
        "sumo.xacro"
    ])


    robot_description = {
        "robot_description": Command([
            "xacro ",
            xacro_file
        ])
    }


    # Gazebo Sim
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare("ros_gz_sim"),
                "launch",
                "gz_sim.launch.py"
            ])
        ),
        launch_arguments={
            "gz_args": "-r empty.sdf"
        }.items()
    )


    # Robot TF publisher
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[
            robot_description,
            {
                "use_sim_time": True
            }
        ]
    )


    # Spawn robot in Gazebo
    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-topic",
            "robot_description",
            "-name",
            "sumo"
        ]
    )


    # ROS-Gazebo bridge
    bridge_config = PathJoinSubstitution([
        FindPackageShare("sumo"),
        "config",
        "bridge_parameters.yaml"
    ])

    ros_gz_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        output="screen",
        parameters=[
            {
                "config_file": bridge_config
            }
        ]
    )


    # RViz config
    rviz_config = PathJoinSubstitution([
        FindPackageShare("sumo"),
        "rviz",
        "robot.rviz"
    ])


    # Start RViz
    rviz2 = Node(
        package="rviz2",
        executable="rviz2",
        output="screen",
        arguments=[
            "-d",
            rviz_config
        ],
        parameters=[
            {
                "use_sim_time": True
            }
        ]
    )


    return LaunchDescription([
        env,
        gazebo,
        robot_state_publisher,
        spawn_robot,
        ros_gz_bridge,
        rviz2
    ])