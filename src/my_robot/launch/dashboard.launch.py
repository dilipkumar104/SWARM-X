#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
dashboard.launch.py — SWARM-X Web Dashboard Launch

Starts all sensor nodes + rosbridge WebSocket server so the
browser dashboard at dashboard/index.html can receive live data.

Usage:
    ros2 launch my_robot dashboard.launch.py

    # With custom robot namespace:
    ros2 launch my_robot dashboard.launch.py robot_ns:=bholu

    # Simulation mode (no real hardware):
    ros2 launch my_robot dashboard.launch.py simulate:=true
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, GroupAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace


def generate_launch_description():

    # ── Arguments ─────────────────────────────────────────────────────────────
    robot_ns_arg = DeclareLaunchArgument(
        'robot_ns', default_value='dholu',
        description='ROS2 namespace for this robot (dholu or bholu)')

    simulate_arg = DeclareLaunchArgument(
        'simulate', default_value='true',
        description='Run sensor nodes in simulator mode (no real hardware)')

    ws_port_arg = DeclareLaunchArgument(
        'ws_port', default_value='9090',
        description='Rosbridge WebSocket port (dashboard connects here)')

    robot_ns  = LaunchConfiguration('robot_ns')
    simulate  = LaunchConfiguration('simulate')
    ws_port   = LaunchConfiguration('ws_port')

    # ── Sensor / logic nodes (namespaced under robot_ns) ─────────────────────
    sensor_nodes = GroupAction([
        PushRosNamespace(robot_ns),

        # Ultrasonic simulator (publishes ultrasonic/range for testing)
        Node(
            package='my_robot',
            executable='ultrasonic_simulator',
            name='ultrasonic_simulator',
            output='screen',
        ),

        # Ultrasonic listener
        Node(
            package='my_robot',
            executable='ultrasonic_listener',
            name='ultrasonic_listener',
            output='screen',
        ),

        # IR Sensor (MLX90614 or simulator)
        Node(
            package='my_robot',
            executable='ir_sensor_node',
            name='ir_sensor_node',
            output='screen',
        ),

        # IMU (MPU6050 or simulator)
        Node(
            package='my_robot',
            executable='imu_node',
            name='imu_node',
            output='screen',
            parameters=[{'simulate': simulate}],
        ),

        # Battery monitor (ADS1115 or simulator)
        Node(
            package='my_robot',
            executable='battery_monitor',
            name='battery_monitor',
            output='screen',
            parameters=[{'simulate': simulate}],
        ),

        # System monitor (CPU/RAM — always real, no hardware needed)
        Node(
            package='my_robot',
            executable='system_monitor',
            name='system_monitor',
            output='screen',
        ),



        # Obstacle avoider brain
        Node(
            package='my_robot',
            executable='obstacle_avoider',
            name='obstacle_avoider',
            output='screen',
        ),

        # Odometry
        Node(
            package='my_robot',
            executable='odometry_node',
            name='odometry_node',
            output='screen',
        ),

        # Diagnostics watchdog
        Node(
            package='my_robot',
            executable='diagnostics_node',
            name='diagnostics_node',
            output='screen',
        ),
    ])

    # ── Rosbridge WebSocket server (dashboard bridge) ─────────────────────────
    rosbridge_node = Node(
        package='rosbridge_server',
        executable='rosbridge_websocket',
        name='rosbridge_websocket',
        output='screen',
        parameters=[{
            'port': ws_port,
            'address': '0.0.0.0',    # accept from any host on the network
            'retry_startup_delay': 5.0,
        }],
    )

    return LaunchDescription([
        robot_ns_arg,
        simulate_arg,
        ws_port_arg,
        LogInfo(msg=[
            '\n',
            '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n',
            '  🤖 SWARM-X Dashboard Launch\n',
            '  Robot NS  : ', robot_ns, '\n',
            '  Simulate  : ', simulate, '\n',
            '  WS Port   : ', ws_port, '\n',
            '  Dashboard : open dashboard/index.html in browser\n',
            '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n',
        ]),
        sensor_nodes,
        rosbridge_node,
    ])
