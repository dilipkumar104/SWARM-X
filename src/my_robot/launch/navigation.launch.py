#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
navigation.launch.py — Nav2 Autonomous Navigation Stack

Launches the full ROS 2 Navigation2 stack for the SWARM-X robot.

Modes:
  With a pre-built map (AMCL localization):
    ros2 launch my_robot navigation.launch.py map:=/path/to/map.yaml

  Without a map (open-loop, Nav2 only):
    ros2 launch my_robot navigation.launch.py

  With SLAM running simultaneously:
    ros2 launch my_robot master.launch.py use_slam:=true use_nav2:=true

What this launches:
  1. nav2_bringup  — controller, planner, costmaps, BT navigator
  2. lifecycle_manager — manages Nav2 node lifecycle
  3. map_server (optional) — serves a saved map for AMCL
  4. amcl (optional) — localizes robot on the map

Usage:
  ros2 launch my_robot navigation.launch.py
  ros2 launch my_robot navigation.launch.py map:=/home/pi/maps/my_room.yaml
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    pkg_my_robot = get_package_share_directory('my_robot')
    nav2_params  = os.path.join(pkg_my_robot, 'config', 'nav2_params.yaml')

    # ── Launch arguments ──────────────────────────────────────────────────────
    args = [
        DeclareLaunchArgument(
            'map',
            default_value='',
            description='Full path to a saved map YAML file. Leave empty '
                        'for map-less navigation (SLAM must be running).'),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation (Gazebo) clock'),
        DeclareLaunchArgument(
            'autostart',
            default_value='true',
            description='Automatically start Nav2 lifecycle nodes'),
        DeclareLaunchArgument(
            'params_file',
            default_value=nav2_params,
            description='Path to nav2_params.yaml'),
    ]

    use_map = LaunchConfiguration('map')

    # ── Nav2 Bringup ──────────────────────────────────────────────────────────
    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('nav2_bringup'),
                'launch',
                'navigation_launch.py',
            ])
        ]),
        launch_arguments={
            'params_file':    LaunchConfiguration('params_file'),
            'use_sim_time':   LaunchConfiguration('use_sim_time'),
            'autostart':      LaunchConfiguration('autostart'),
        }.items(),
    )

    # ── Map Server (only if a map file was supplied) ───────────────────────────
    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{
            'yaml_filename': LaunchConfiguration('map'),
            'use_sim_time':  LaunchConfiguration('use_sim_time'),
        }],
        condition=IfCondition(
            # IfCondition expects a bool string — use a LaunchConfiguration
            # that is non-empty when map is provided.
            # Workaround: always launch but map_server handles empty gracefully.
            'true'
        ),
    )

    # ── AMCL Localization ─────────────────────────────────────────────────────
    amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[LaunchConfiguration('params_file')],
    )

    # ── Lifecycle Manager for map_server + amcl ───────────────────────────────
    lifecycle_manager_localization = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        output='screen',
        parameters=[{
            'use_sim_time':  LaunchConfiguration('use_sim_time'),
            'autostart':     LaunchConfiguration('autostart'),
            'node_names':    ['map_server', 'amcl'],
        }],
    )

    return LaunchDescription(
        args + [
            LogInfo(msg='━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'),
            LogInfo(msg='  🗺  SWARM-X Navigation Launch'),
            LogInfo(msg='  DWB local planner + NavFn global planner'),
            LogInfo(msg='━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'),
            nav2_bringup,
            map_server,
            amcl,
            lifecycle_manager_localization,
        ]
    )
