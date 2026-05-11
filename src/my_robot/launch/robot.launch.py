#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
robot.launch.py — Launches the full SWARM-X robot stack on the Pi.

Nodes started:
    1. motor_controller   — subscribes /cmd_vel → drives L298N GPIO pins
    2. obstacle_avoider   — subscribes /scan → publishes /cmd_vel

All parameters can be overridden from the command line:

    ros2 launch my_robot robot.launch.py obstacle_distance:=0.3 forward_speed:=0.15
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, EmitEvent
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # ── Declare overridable arguments ─────────────────────────────────────────
    args = [
        # Motor controller
        DeclareLaunchArgument('ena_pin',           default_value='12',
                              description='BCM pin: L298N EnA (left PWM)'),
        DeclareLaunchArgument('in1_pin',           default_value='23',
                              description='BCM pin: L298N In1'),
        DeclareLaunchArgument('in2_pin',           default_value='24',
                              description='BCM pin: L298N In2'),
        DeclareLaunchArgument('enb_pin',           default_value='13',
                              description='BCM pin: L298N EnB (right PWM)'),
        DeclareLaunchArgument('in3_pin',           default_value='27',
                              description='BCM pin: L298N In3'),
        DeclareLaunchArgument('in4_pin',           default_value='22',
                              description='BCM pin: L298N In4'),
        DeclareLaunchArgument('max_speed',         default_value='1.0',
                              description='Max wheel speed [m/s]'),
        DeclareLaunchArgument('track_width',       default_value='0.20',
                              description='Wheel-to-wheel distance [m]'),
        DeclareLaunchArgument('heartbeat_timeout', default_value='0.5',
                              description='Motor stop timeout [s]'),

        # Obstacle avoider
        DeclareLaunchArgument('obstacle_distance', default_value='0.5',
                              description='Lidar stop threshold [m]'),
        DeclareLaunchArgument('forward_speed',     default_value='0.2',
                              description='Cruise speed [m/s]'),
        DeclareLaunchArgument('rotate_speed',      default_value='0.5',
                              description='Rotation speed [rad/s]'),
        DeclareLaunchArgument('rotate_angle_deg',  default_value='90.0',
                              description='Rotation angle [deg]'),
        DeclareLaunchArgument('front_arc_deg',     default_value='60.0',
                              description='Front danger arc half-angle [deg]'),
    ]

    # ── Motor Controller Node ─────────────────────────────────────────────────
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

    # ── Obstacle Avoider Node ─────────────────────────────────────────────────
    avoider_node = Node(
        package='my_robot',
        executable='obstacle_avoider',
        name='obstacle_avoider',
        output='screen',
        emulate_tty=True,
        parameters=[{
            'obstacle_distance': LaunchConfiguration('obstacle_distance'),
            'forward_speed':     LaunchConfiguration('forward_speed'),
            'rotate_speed':      LaunchConfiguration('rotate_speed'),
            'rotate_angle_deg':  LaunchConfiguration('rotate_angle_deg'),
            'front_arc_deg':     LaunchConfiguration('front_arc_deg'),
        }],
    )

    return LaunchDescription(
        args + [
            LogInfo(msg='━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'),
            LogInfo(msg='  🤖 SWARM-X robot.launch.py starting…'),
            LogInfo(msg='━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'),
            motor_node,
            avoider_node,
        ]
    )
