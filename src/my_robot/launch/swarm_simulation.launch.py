#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
swarm_simulation.launch.py — Two-Robot Swarm Simulation (Dholu & Bholu)

Launches a complete two-robot simulation network:

  /dholu/
    ├── swarm_publisher        → publishes to /dholu/swarm_status
    ├── ultrasonic_simulator   → publishes to /dholu/ultrasonic/range
    └── ultrasonic_listener    → subscribes to /dholu/ultrasonic/range

  /bholu/
    ├── swarm_publisher        → publishes to /bholu/swarm_status
    ├── ultrasonic_simulator   → publishes to /bholu/ultrasonic/range
    └── ultrasonic_listener    → subscribes to /bholu/ultrasonic/range

  (root)
    └── swarm_monitor          → subscribes to /dholu/swarm_status AND /bholu/swarm_status

Usage:
    ros2 launch my_robot swarm_simulation.launch.py

Verify:
    ros2 topic list
    ros2 node list
"""

from launch import LaunchDescription
from launch.actions import GroupAction, LogInfo, TimerAction
from launch_ros.actions import Node, PushROSNamespace


def generate_launch_description():
    """Build the two-robot simulation launch description."""

    # ══════════════════════════════════════════════════════════════
    #  ROBOT DEFINITIONS
    # ══════════════════════════════════════════════════════════════
    robots = [
        {'namespace': 'dholu', 'robot_name': 'Dholu'},
        {'namespace': 'bholu', 'robot_name': 'Bholu'},
    ]

    launch_actions = [
        LogInfo(msg='━' * 60),
        LogInfo(msg='  🤖 SWARM-X Two-Robot Simulation'),
        LogInfo(msg='  Robots: Dholu & Bholu'),
        LogInfo(msg='━' * 60),
    ]

    # ── Create a node group for each robot ────────────────────────
    for robot in robots:
        ns = robot['namespace']
        name = robot['robot_name']

        group = GroupAction([
            # Push namespace — all nodes inside get /dholu/ or /bholu/ prefix
            PushROSNamespace(ns),

            # Swarm status publisher
            Node(
                package='my_robot',
                executable='swarm_publisher',
                name='swarm_publisher',
                output='screen',
                parameters=[{'robot_name': name}],
            ),

            # Ultrasonic simulator (fake sensor data)
            Node(
                package='my_robot',
                executable='ultrasonic_simulator',
                name='ultrasonic_simulator',
                output='screen',
            ),

            # Ultrasonic listener (processes sensor data)
            Node(
                package='my_robot',
                executable='ultrasonic_listener',
                name='ultrasonic_listener',
                output='screen',
            ),
        ])

        launch_actions.append(
            LogInfo(msg=f'  🚀 Launching {name} in /{ns}/ namespace...')
        )
        launch_actions.append(group)

    # ── Central swarm monitor (subscribes to BOTH robots) ─────────
    # We launch two subscriber instances, one per robot namespace,
    # so each picks up its respective /dholu/swarm_status or /bholu/swarm_status
    for robot in robots:
        ns = robot['namespace']
        monitor = GroupAction([
            PushROSNamespace(ns),
            Node(
                package='my_robot',
                executable='swarm_subscriber',
                name='swarm_monitor',
                output='screen',
            ),
        ])
        launch_actions.append(monitor)

    launch_actions.append(
        LogInfo(msg='  ✅ All robots launched! Use `ros2 topic list` to verify.')
    )

    return LaunchDescription(launch_actions)
