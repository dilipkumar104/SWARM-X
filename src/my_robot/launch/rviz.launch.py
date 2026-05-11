#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
rviz.launch.py — Launch RViz2 with the SWARM-X pre-configured layout

Displays:
  - Robot model (from URDF via robot_state_publisher)
  - TF frames tree
  - LaserScan (/scan)
  - Odometry (/odom)
  - OccupancyGrid map (/map) — appears when SLAM is running
  - Path (/plan) — appears when Nav2 is running

Usage:
    ros2 launch my_robot rviz.launch.py

From the master launch:
    ros2 launch my_robot master.launch.py use_rviz:=true
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    pkg = get_package_share_directory('my_robot')
    rviz_config = os.path.join(pkg, 'rviz', 'swarmx.rviz')

    return LaunchDescription([
        DeclareLaunchArgument(
            'rviz_config',
            default_value=rviz_config,
            description='Path to RViz2 config file'),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', LaunchConfiguration('rviz_config')],
            output='screen',
        ),
    ])
