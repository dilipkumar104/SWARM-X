#!/usr/bin/env python3
"""
robot1_hw_launch.py — SWARM-X Pi-Side Hardware Launch File

Launches ALL hardware-interfacing nodes on the Raspberry Pi 4 (2GB)
under the /robot1/ namespace:

  1. motor_driver      — L298N GPIO PWM motor control
  2. rplidar_node      — RPLidar A1 laser scanner driver
  3. ultrasonic_node   — HC-SR04 front obstacle detection + emergency stop
  4. thermal_sensor    — MLX90614 IR thermal survivor detection

All topics automatically get the /robot1/ prefix:
  /robot1/cmd_vel, /robot1/scan, /robot1/ultrasonic_front,
  /robot1/heat_sensor, /robot1/survivor_alert

Usage:
  ros2 launch swarmx_hw robot1_hw_launch.py

  # Override LiDAR port:
  ros2 launch swarmx_hw robot1_hw_launch.py lidar_port:=/dev/rplidar

  # Disable ultrasonic emergency stop:
  ros2 launch swarmx_hw robot1_hw_launch.py enable_estop:=false
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace


def generate_launch_description():
    # ── Launch arguments (overridable from CLI) ───────────────────────
    lidar_port_arg = DeclareLaunchArgument(
        'lidar_port',
        default_value='/dev/ttyUSB0',
        description='Serial port for RPLidar A1'
    )

    enable_estop_arg = DeclareLaunchArgument(
        'enable_estop',
        default_value='true',
        description='Enable ultrasonic emergency stop'
    )

    # ── All nodes grouped under /robot1/ namespace ────────────────────
    robot1_group = GroupAction([
        PushRosNamespace('robot1'),

        # ── 1. Motor Driver ───────────────────────────────────────────
        Node(
            package='swarmx_hw',
            executable='motor_driver',
            name='motor_driver',
            output='screen',
            parameters=[{
                'in1_pin': 17,
                'in2_pin': 18,
                'in3_pin': 27,
                'in4_pin': 22,
                'ena_pin': 12,
                'enb_pin': 13,
                'max_linear_speed': 0.5,
                'max_angular_speed': 1.0,
                'pwm_frequency': 100,
            }],
            # Remap so it uses the namespaced topic
            remappings=[
                ('cmd_vel', 'cmd_vel'),
            ],
        ),

        # ── 2. RPLidar A1 Driver ─────────────────────────────────────
        #
        # Uses the rplidar_ros package (ros-humble-rplidar-ros).
        # The LaserScan is published to /robot1/scan.
        #
        # Frame ID must match your URDF / tf tree for SLAM to work.
        Node(
            package='rplidar_ros',
            executable='rplidar_node',
            name='rplidar_node',
            output='screen',
            parameters=[{
                'serial_port': LaunchConfiguration('lidar_port'),
                'serial_baudrate': 115200,
                'frame_id': 'robot1/laser_frame',
                'angle_compensate': True,
                'scan_mode': 'Standard',
                # Invert scan if LiDAR is mounted upside-down:
                # 'inverted': True,
            }],
            remappings=[
                ('scan', 'scan'),
            ],
        ),

        # ── 3. Ultrasonic Sensor (HC-SR04) ────────────────────────────
        Node(
            package='swarmx_hw',
            executable='ultrasonic_node',
            name='ultrasonic_node',
            output='screen',
            parameters=[{
                'trig_pin': 23,
                'echo_pin': 24,
                'poll_rate_hz': 10.0,
                'safety_threshold_m': 0.20,
                'enable_emergency_stop': LaunchConfiguration('enable_estop'),
            }],
            remappings=[
                ('ultrasonic_front', 'ultrasonic_front'),
                ('cmd_vel', 'cmd_vel'),
            ],
        ),

        # ── 4. Thermal Sensor (MLX90614) ─────────────────────────────
        Node(
            package='swarmx_hw',
            executable='thermal_sensor',
            name='thermal_sensor',
            output='screen',
            parameters=[{
                'poll_rate_hz': 2.0,
                'survivor_threshold_c': 30.0,
                'i2c_bus': 1,
                'i2c_address': 0x5A,
            }],
            remappings=[
                ('heat_sensor', 'heat_sensor'),
                ('survivor_alert', 'survivor_alert'),
            ],
        ),
    ])

    return LaunchDescription([
        # ── Startup banner ────────────────────────────────────────────
        LogInfo(msg='━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'),
        LogInfo(msg='  🤖 SWARM-X Robot 1 — Hardware Launch'),
        LogInfo(msg='  Namespace : /robot1/'),
        LogInfo(msg='  Nodes     : motor_driver, rplidar, ultrasonic, thermal'),
        LogInfo(msg='  Platform  : Raspberry Pi 4 (2GB)'),
        LogInfo(msg='━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'),

        lidar_port_arg,
        enable_estop_arg,
        robot1_group,
    ])
