#!/usr/bin/env python3
"""
rover_launch.py

Launch file to start both rover base nodes:
  - ultrasonic_node : reads distance from ESP32 and publishes to /ultrasonic
  - motor_cmd_node  : subscribes to /cmd_vel and sends commands to ESP32
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        # ── Ultrasonic Sensor Node ────────────────────────────────────
        Node(
            package='rover_base_pkg',
            executable='ultrasonic_node',
            name='ultrasonic_node',
            output='screen',
            parameters=[{
                'serial_port': '/dev/ttyUSB0',
                'baud_rate': 115200,
            }],
        ),

        # ── Motor Command Node ───────────────────────────────────────
        Node(
            package='rover_base_pkg',
            executable='motor_cmd_node',
            name='motor_cmd_node',
            output='screen',
            parameters=[{
                'serial_port': '/dev/ttyUSB0',
                'baud_rate': 115200,
            }],
        ),
    ])
