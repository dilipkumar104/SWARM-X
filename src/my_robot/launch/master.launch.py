#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
master.launch.py — SWARM-X Complete Robot Stack

Starts every node in the correct order with full parameter control.

┌────────────────────────────────────────────────────────────┐
│  Always started:                                           │
│    robot_state_publisher  (URDF → TF tree)                 │
│    odometry_node          (dead-reckoning /odom + TF)      │
│    motor_controller       (/cmd_vel → L298N GPIO)          │
│    obstacle_avoider       (Lidar + HC-SR04 fused FSM)      │
│    diagnostics_node       (topic health monitor)           │
│                                                            │
│  Conditional (set flag:=true to enable):                   │
│    use_esp32:=true   → micro_ros_agent + ultrasonic_listener│
│    use_slam:=true    → slam_toolbox online_async           │
│    use_nav2:=true    → Nav2 (planner, controller, AMCL)    │
│    use_rviz:=true    → RViz2 with pre-built config         │
└────────────────────────────────────────────────────────────┘

Quick examples:
  # Minimal — just drive and avoid obstacles:
  ros2 launch my_robot master.launch.py

  # Build a map while driving:
  ros2 launch my_robot master.launch.py use_esp32:=true use_slam:=true use_rviz:=true

  # Full autonomous navigation with a pre-built map:
  ros2 launch my_robot master.launch.py use_nav2:=true use_rviz:=true map:=/home/pi/maps/room.yaml

  # Everything ON:
  ros2 launch my_robot master.launch.py use_esp32:=true use_slam:=true use_nav2:=true use_rviz:=true
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    LogInfo,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    Command,
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    pkg          = get_package_share_directory('my_robot')
    urdf_path    = os.path.join(pkg, 'urdf', 'robot.urdf.xacro')
    slam_cfg     = os.path.join(pkg, 'config', 'slam_toolbox.yaml')
    nav2_params  = os.path.join(pkg, 'config', 'nav2_params.yaml')
    rviz_cfg     = os.path.join(pkg, 'rviz', 'swarmx.rviz')

    # ══════════════════════════════════════════════════════════════════
    #  LAUNCH ARGUMENTS
    # ══════════════════════════════════════════════════════════════════
    args = [
        # ── Feature toggles ───────────────────────────────────────────
        DeclareLaunchArgument(
            'use_esp32', default_value='true',
            description='Start micro_ros_agent + ultrasonic_listener for ESP32+HC-SR04'),
        DeclareLaunchArgument(
            'use_slam', default_value='false',
            description='Launch SLAM Toolbox to build a map in real-time'),
        DeclareLaunchArgument(
            'use_nav2', default_value='false',
            description='Launch Nav2 autonomous navigation stack'),
        DeclareLaunchArgument(
            'use_rviz', default_value='false',
            description='Launch RViz2 visualisation (on laptop, not on Pi)'),

        # ── Map file (only used when use_nav2:=true) ──────────────────
        DeclareLaunchArgument(
            'map', default_value='',
            description='Full path to a pre-built map YAML file for Nav2/AMCL'),

        # ── ESP32 serial ──────────────────────────────────────────────
        DeclareLaunchArgument(
            'serial_port', default_value='/dev/ttyUSB0',
            description='ESP32 USB serial port'),
        DeclareLaunchArgument(
            'baud_rate', default_value='115200'),

        # ── Motor controller GPIO pins (BCM) ──────────────────────────
        DeclareLaunchArgument('ena_pin',           default_value='12'),
        DeclareLaunchArgument('in1_pin',           default_value='23'),
        DeclareLaunchArgument('in2_pin',           default_value='24'),
        DeclareLaunchArgument('enb_pin',           default_value='13'),
        DeclareLaunchArgument('in3_pin',           default_value='27'),
        DeclareLaunchArgument('in4_pin',           default_value='22'),
        DeclareLaunchArgument('max_speed',         default_value='1.0'),
        DeclareLaunchArgument('track_width',       default_value='0.20'),
        DeclareLaunchArgument('heartbeat_timeout', default_value='0.5'),

        # ── Obstacle avoider ──────────────────────────────────────────
        DeclareLaunchArgument('obstacle_distance', default_value='0.5'),
        DeclareLaunchArgument('critical_distance', default_value='0.15'),
        DeclareLaunchArgument('forward_speed',     default_value='0.2'),
        DeclareLaunchArgument('rotate_speed',      default_value='0.5'),
        DeclareLaunchArgument('rotate_angle_deg',  default_value='90.0'),
        DeclareLaunchArgument('front_arc_deg',     default_value='60.0'),
    ]

    # ══════════════════════════════════════════════════════════════════
    #  ALWAYS-ON NODES
    # ══════════════════════════════════════════════════════════════════

    # 1. Robot State Publisher — loads URDF, publishes /robot_description
    #    and static TF frames (base_link → laser, wheels, ultrasonic_link)
    robot_state_pub = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': Command(['xacro ', urdf_path]),
            'use_sim_time': False,
        }],
    )

    # 2. Motor Controller — /cmd_vel → L298N GPIO PWM
    motor_node = Node(
        package='my_robot',
        executable='motor_controller',
        name='motor_controller',
        output='screen',
        emulate_tty=True,
        parameters=[{
            'ena_pin':           LaunchConfiguration('ena_pin'),
            'in1_pin':           LaunchConfiguration('in1_pin'),
            'in2_pin':           LaunchConfiguration('in2_pin'),
            'enb_pin':           LaunchConfiguration('enb_pin'),
            'in3_pin':           LaunchConfiguration('in3_pin'),
            'in4_pin':           LaunchConfiguration('in4_pin'),
            'max_speed':         LaunchConfiguration('max_speed'),
            'track_width':       LaunchConfiguration('track_width'),
            'heartbeat_timeout': LaunchConfiguration('heartbeat_timeout'),
        }],
    )

    # 3. Obstacle Avoider — fused Lidar + HC-SR04 state machine
    avoider_node = Node(
        package='my_robot',
        executable='obstacle_avoider',
        name='obstacle_avoider',
        output='screen',
        emulate_tty=True,
        parameters=[{
            'obstacle_distance': LaunchConfiguration('obstacle_distance'),
            'critical_distance': LaunchConfiguration('critical_distance'),
            'forward_speed':     LaunchConfiguration('forward_speed'),
            'rotate_speed':      LaunchConfiguration('rotate_speed'),
            'rotate_angle_deg':  LaunchConfiguration('rotate_angle_deg'),
            'front_arc_deg':     LaunchConfiguration('front_arc_deg'),
        }],
    )

    # 4. Dead-Reckoning Odometry — /cmd_vel → /odom + TF odom→base_link
    odom_node = Node(
        package='my_robot',
        executable='odometry_node',
        name='odometry_node',
        output='screen',
        emulate_tty=True,
    )

    # 5. Diagnostics — topic heartbeat monitor
    diag_node = Node(
        package='my_robot',
        executable='diagnostics_node',
        name='diagnostics_node',
        output='screen',
        emulate_tty=True,
    )

    # 6. IR Sensor (MLX90614) — thermal survivor detection
    ir_node = Node(
        package='my_robot',
        executable='ir_sensor_node',
        name='ir_sensor_node',
        output='screen',
        emulate_tty=True,
    )

    # 7. IMU (MPU6050) — orientation data
    imu_node = Node(
        package='my_robot',
        executable='imu_node',
        name='imu_node',
        output='screen',
        emulate_tty=True,
    )

    # 8. Battery Monitor — voltage tracking
    battery_node = Node(
        package='my_robot',
        executable='battery_monitor',
        name='battery_monitor',
        output='screen',
        emulate_tty=True,
    )

    # 9. System Monitor — CPU/RAM/temp
    system_node = Node(
        package='my_robot',
        executable='system_monitor',
        name='system_monitor',
        output='screen',
        emulate_tty=True,
    )

    # ══════════════════════════════════════════════════════════════════
    #  CONDITIONAL: ESP32 + HC-SR04 (use_esp32:=true)
    # ══════════════════════════════════════════════════════════════════

    # micro-ROS agent — serial bridge for ESP32
    micro_ros_agent = ExecuteProcess(
        cmd=[
            'ros2', 'run', 'micro_ros_agent', 'micro_ros_agent',
            'serial', '--dev', LaunchConfiguration('serial_port'),
            '-b',              LaunchConfiguration('baud_rate'),
        ],
        name='micro_ros_agent',
        output='screen',
        condition=IfCondition(LaunchConfiguration('use_esp32')),
    )

    # Ultrasonic listener — waits 2 s for agent to be ready
    ultrasonic_listener = TimerAction(
        period=2.0,
        actions=[
            Node(
                package='my_robot',
                executable='ultrasonic_listener',
                name='ultrasonic_listener',
                output='screen',
                emulate_tty=True,
                condition=IfCondition(LaunchConfiguration('use_esp32')),
            )
        ],
    )

    # ══════════════════════════════════════════════════════════════════
    #  CONDITIONAL: SLAM Toolbox (use_slam:=true)
    # ══════════════════════════════════════════════════════════════════
    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('slam_toolbox'),
                'launch',
                'online_async_launch.py',
            ])
        ]),
        launch_arguments={
            'slam_params_file': slam_cfg,
            'use_sim_time':     'false',
        }.items(),
        condition=IfCondition(LaunchConfiguration('use_slam')),
    )

    # ══════════════════════════════════════════════════════════════════
    #  CONDITIONAL: Nav2 Navigation (use_nav2:=true)
    # ══════════════════════════════════════════════════════════════════
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg, 'launch', 'navigation.launch.py')
        ),
        launch_arguments={
            'params_file': nav2_params,
            'map':         LaunchConfiguration('map'),
        }.items(),
        condition=IfCondition(LaunchConfiguration('use_nav2')),
    )

    # ══════════════════════════════════════════════════════════════════
    #  CONDITIONAL: RViz2 (use_rviz:=true)
    # ══════════════════════════════════════════════════════════════════
    rviz_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg, 'launch', 'rviz.launch.py')
        ),
        launch_arguments={
            'rviz_config': rviz_cfg,
        }.items(),
        condition=IfCondition(LaunchConfiguration('use_rviz')),
    )

    # ══════════════════════════════════════════════════════════════════
    #  ASSEMBLE
    # ══════════════════════════════════════════════════════════════════
    return LaunchDescription(
        args + [
            LogInfo(msg='━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'),
            LogInfo(msg='  🤖 SWARM-X — Master Launch'),
            LogInfo(msg='  Flags: use_esp32 | use_slam | use_nav2 | use_rviz'),
            LogInfo(msg='━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'),

            # ── Always on ───────────────────────────────────────────
            robot_state_pub,
            motor_node,
            avoider_node,
            odom_node,
            diag_node,
            ir_node,
            imu_node,
            battery_node,
            system_node,

            # ── Conditional ─────────────────────────────────────────
            micro_ros_agent,
            ultrasonic_listener,
            slam_launch,
            nav2_launch,
            rviz_launch,
        ]
    )
