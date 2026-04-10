#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
esp32_ultrasonic.launch.py — Launch file for the ESP32 ultrasonic pipeline.

Starts:
    1. micro_ros_agent  (serial transport, /dev/ttyUSB0, 115200 baud)
    2. ultrasonic_listener node

Usage:
    ros2 launch my_robot esp32_ultrasonic.launch.py

Override serial port:
    ros2 launch my_robot esp32_ultrasonic.launch.py serial_port:=/dev/ttyACM0
"""

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    LogInfo,
    TimerAction,
)
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    # ── Launch arguments ──────────────────────────────────────
    serial_port_arg = DeclareLaunchArgument(
        'serial_port',
        default_value='/dev/ttyUSB0',
        description='Serial port for the ESP32 (e.g. /dev/ttyUSB0, /dev/ttyACM0)',
    )

    baud_rate_arg = DeclareLaunchArgument(
        'baud_rate',
        default_value='115200',
        description='Baud rate for serial communication',
    )

    serial_port = LaunchConfiguration('serial_port')
    baud_rate = LaunchConfiguration('baud_rate')

    # ── micro-ROS Agent (serial transport) ────────────────────
    micro_ros_agent = ExecuteProcess(
        cmd=[
            'ros2', 'run', 'micro_ros_agent', 'micro_ros_agent',
            'serial', '--dev', serial_port, '-b', baud_rate,
        ],
        name='micro_ros_agent',
        output='screen',
    )

    # ── Ultrasonic listener node (delay 2s for agent startup) ─
    ultrasonic_listener = TimerAction(
        period=2.0,
        actions=[
            Node(
                package='my_robot',
                executable='ultrasonic_listener',
                name='ultrasonic_listener',
                output='screen',
            ),
        ],
    )

    # ── Startup info ──────────────────────────────────────────
    startup_info = LogInfo(
        msg='🚀 SWARM-X ESP32 Ultrasonic Pipeline — starting...',
    )

    return LaunchDescription([
        serial_port_arg,
        baud_rate_arg,
        startup_info,
        micro_ros_agent,
        ultrasonic_listener,
    ])
