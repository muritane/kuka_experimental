import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.substitutions import (
    Command,
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
)

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    declared_arguments = []

    declared_arguments.append(
        DeclareLaunchArgument(
            "prefix",
            default_value="",
            description="Prefix of the joint names, useful for \
            multi-robot setup. If changed than also joint names in the controllers' configuration \
            have to be updated.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "use_mock_hw",
            default_value="false",
            description="Start robot with fake hardware mirroring command to its states.",
        )
    )

    declared_arguments.append(
        DeclareLaunchArgument(
            "use_mock_sensor_commands",
            default_value="false",
            description="Enable fake command interfaces for sensors used for simple simulations. \
            Used only if 'use_mock_hardware' parameter is true.",
        )
    )

    declared_arguments.append(
        DeclareLaunchArgument(
            "log_level",
            default_value="info",
            description="Set the logging level of the loggers of all started nodes.",
        )
    )

    declared_arguments.append(
        DeclareLaunchArgument(
            "log_level_all",
            default_value="info",
            description="Set the logging level of the loggers of all started nodes.",
        )
    )

    # initialize arguments
    prefix = LaunchConfiguration("prefix")
    use_mock_hw = LaunchConfiguration("use_mock_hw")
    use_mock_sensor_commands = LaunchConfiguration("use_mock_sensor_commands")
    log_level = LaunchConfiguration("log_level")
    log_level_all = LaunchConfiguration("log_level_all")

    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution(
                [FindPackageShare("kuka_kr16_support"), "urdf", "kr16_2.urdf.xacro"]
            ),
            " ",
            "prefix:=",
            prefix,
            " ",
            "use_mock_hw:=",
            use_mock_hw,
            " ",
            "use_mock_sensor_commands:=",
            use_mock_sensor_commands,
            " ",
        ]
    )

    robot_description = {"robot_description": robot_description_content}

    robot_controllers = PathJoinSubstitution(
        [
            FindPackageShare("common_6dof_position_only_system"),
            "config",
            "kuka_6dof_controller_position.yaml",
        ]
    )

    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node_max_update_rate",
        output="both",
        arguments=[
            "--ros-args",
            "--log-level",
            ["KukaSystemPositionOnlyHardware:=", log_level],
            "--ros-args",
            "--log-level",
            log_level_all,
        ],
        parameters=[robot_description, robot_controllers],
    )

    robot_state_pub_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[robot_description],
        output="both",
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager",
            "/controller_manager",
        ],
    )

    robot_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["position_trajectory_controller", "-c", "/controller_manager"],
    )

    delay_robot_controller_spawner_after_joint_state_broadcaster_spawner = (
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=joint_state_broadcaster_spawner,
                on_exit=[robot_controller_spawner],
            )
        )
    )

    position_goals = PathJoinSubstitution(
        [
            FindPackageShare("kuka_kr16_support"),
            "config/controller",
            "kuka_6dof_joint_trajectory_controller_goals.yaml",
        ]
    )

    joint_trajecotory_controller = Node(
        package="ros2_controllers_test_nodes",
        executable="publisher_joint_trajectory_controller",
        name="publisher_joint_trajectory_controller",
        parameters=[position_goals],
        output="both",
    )

    delay_joint_trajecotory_controller_after_joint_state_broadcaster_spawner = (
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=joint_state_broadcaster_spawner,
                on_exit=[joint_trajecotory_controller],
            )
        )
    )

    nodes = [
        control_node,
        robot_state_pub_node,
        joint_state_broadcaster_spawner,
        delay_robot_controller_spawner_after_joint_state_broadcaster_spawner,
        delay_joint_trajecotory_controller_after_joint_state_broadcaster_spawner,
    ]

    return LaunchDescription(declared_arguments + nodes)
