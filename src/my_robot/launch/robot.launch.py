#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
robot.launch.py — Core SWARM-X Robot Stack (Raspberry Pi)

Nodes started:
    1. motor_controller    — cmd_vel -> L298N GPIO PWM
    2. obstacle_avoider    — scan + ultrasonic/status + ir/temperature -> cmd_vel
    3. ultrasonic_listener — ESP32 micro-ROS -> ultrasonic/status
    4. ir_sensor_node      — MLX90614 I2C -> ir/temperature + ir/ambient
    5. odometry_node       — cmd_vel integration -> odom + TF

All parameters can be overridden from the command line, e.g.:
    ros2 launch my_robot robot.launch.py forward_speed:=0.15 ir_warn_temp:=38.0
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    # ── Declare overridable arguments ─────────────────────────────────────────
    args = [
        # Motor controller
        DeclareLaunchArgument('ena_pin',           default_value='12'),
        DeclareLaunchArgument('in1_pin',           default_value='23'),
        DeclareLaunchArgument('in2_pin',           default_value='24'),
        DeclareLaunchArgument('enb_pin',           default_value='13'),
        DeclareLaunchArgument('in3_pin',           default_value='27'),
        DeclareLaunchArgument('in4_pin',           default_value='22'),
        DeclareLaunchArgument('max_speed',         default_value='1.0'),
        DeclareLaunchArgument('track_width',       default_value='0.20'),
        DeclareLaunchArgument('heartbeat_timeout', default_value='0.5'),

        # Obstacle avoider
        DeclareLaunchArgument('obstacle_distance', default_value='0.5'),
        DeclareLaunchArgument('forward_speed',     default_value='0.2'),
        DeclareLaunchArgument('rotate_speed',      default_value='0.5'),
        DeclareLaunchArgument('rotate_angle_deg',  default_value='90.0'),
        DeclareLaunchArgument('front_arc_deg',     default_value='60.0'),

        # IR sensor (MLX90614)
        DeclareLaunchArgument('ir_publish_hz',     default_value='5.0',
                              description='MLX90614 publish rate [Hz] — keep low to save CPU'),
        DeclareLaunchArgument('ir_warn_temp',      default_value='40.0',
                              description='Object temp threshold for warning log [C]'),
        DeclareLaunchArgument('ir_i2c_bus',        default_value='1'),
        DeclareLaunchArgument('ir_i2c_address',    default_value='90',  # 0x5A = 90
                              description='MLX90614 I2C address (decimal, default 90 = 0x5A)'),
    ]

    # ── Motor Controller ───────────────────────────────────────────────────────
    motor_node = Node(
        package='my_robot',
        executable='motor_controller',
        name='motor_controller',
        output='screen',
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

    # ── Obstacle Avoider ──────────────────────────────────────────────────────
    avoider_node = Node(
        package='my_robot',
        executable='obstacle_avoider',
        name='obstacle_avoider',
        output='screen',
        parameters=[{
            'obstacle_distance': LaunchConfiguration('obstacle_distance'),
            'forward_speed':     LaunchConfiguration('forward_speed'),
            'rotate_speed':      LaunchConfiguration('rotate_speed'),
            'rotate_angle_deg':  LaunchConfiguration('rotate_angle_deg'),
            'front_arc_deg':     LaunchConfiguration('front_arc_deg'),
        }],
    )

    # ── Ultrasonic Listener ───────────────────────────────────────────────────
    ultrasonic_node = Node(
        package='my_robot',
        executable='ultrasonic_listener',
        name='ultrasonic_listener',
        output='screen',
    )

    # ── IR Thermal Sensor (MLX90614) ──────────────────────────────────────────
    ir_node = Node(
        package='my_robot',
        executable='ir_sensor_node',
        name='ir_sensor_node',
        output='screen',
        parameters=[{
            'publish_hz':   LaunchConfiguration('ir_publish_hz'),
            'warn_temp_c':  LaunchConfiguration('ir_warn_temp'),
            'i2c_bus':      LaunchConfiguration('ir_i2c_bus'),
            'i2c_address':  LaunchConfiguration('ir_i2c_address'),
        }],
    )

    # ── Odometry Node ─────────────────────────────────────────────────────────
    odom_node = Node(
        package='my_robot',
        executable='odometry_node',
        name='odometry_node',
        output='screen',
    )

    return LaunchDescription(
        args + [
            LogInfo(msg='SWARM-X robot.launch.py starting...'),
            motor_node,
            avoider_node,
            ultrasonic_node,
            ir_node,
            odom_node,
        ]
    )
