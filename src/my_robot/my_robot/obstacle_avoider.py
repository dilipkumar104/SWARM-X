#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
obstacle_avoider.py — Lidar + Ultrasonic + IR Thermal Obstacle Avoidance

State machine:
    FORWARD  -> (obstacle) -> STOPPING -> ROTATING -> FORWARD

Subscribes:
    /scan              (sensor_msgs/LaserScan)  — LiDAR
    /ultrasonic/status (std_msgs/String)        — HC-SR04 fusion
    /ir/temperature    (sensor_msgs/Temperature)— MLX90614 IR thermal

Publishes:
    /cmd_vel  (geometry_msgs/Twist)
"""

import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan, Temperature
from geometry_msgs.msg import Twist
from std_msgs.msg import String


class State:
    FORWARD  = 'FORWARD'
    STOPPING = 'STOPPING'
    ROTATING = 'ROTATING'


class ObstacleAvoider(Node):
    """Obstacle avoidance fusing LiDAR, ultrasonic and IR thermal data."""

    def __init__(self):
        super().__init__('obstacle_avoider')

        # Parameters
        self.declare_parameter('obstacle_distance',   0.5)
        self.declare_parameter('critical_distance',   0.15)
        self.declare_parameter('forward_speed',       0.2)
        self.declare_parameter('rotate_speed',        0.5)
        self.declare_parameter('rotate_angle_deg',    90.0)
        self.declare_parameter('front_arc_deg',       60.0)
        self.declare_parameter('publish_hz',          10.0)
        # IR threshold: if an object is warmer than ambient by this many °C,
        # treat it as a living obstacle (person, animal, hot surface)
        self.declare_parameter('ir_temp_threshold_c', 30.0)

        self._obstacle_dist  = self.get_parameter('obstacle_distance').value
        self._critical_dist  = self.get_parameter('critical_distance').value
        self._fwd_speed      = self.get_parameter('forward_speed').value
        self._rot_speed      = self.get_parameter('rotate_speed').value
        self._rot_angle      = math.radians(
            self.get_parameter('rotate_angle_deg').value)
        self._front_arc      = math.radians(
            self.get_parameter('front_arc_deg').value)
        hz                   = self.get_parameter('publish_hz').value
        self._ir_threshold   = self.get_parameter('ir_temp_threshold_c').value

        # State machine
        self._state            = State.FORWARD
        self._rotate_start     = None
        self._rotate_duration  = self._rot_angle / abs(self._rot_speed)

        # Sensor flags (latched, updated in callbacks)
        self._lidar_obstacle   = False
        self._lidar_critical   = False
        self._ultrasonic_danger = False
        self._ir_obstacle      = False   # thermal object detected

        # Publisher
        self._pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # Subscribers
        self.create_subscription(
            LaserScan, '/scan', self._scan_callback,
            rclpy.qos.qos_profile_sensor_data)
        self.create_subscription(
            String, '/ultrasonic/status', self._ultrasonic_callback, 10)
        self.create_subscription(
            Temperature, '/ir/temperature', self._ir_callback, 10)

        # Control loop timer
        self._timer = self.create_timer(1.0 / hz, self._control_loop)

        self.get_logger().info(
            f'Obstacle Avoider started | stop={self._obstacle_dist}m '
            f'front=+-{math.degrees(self._front_arc):.0f}deg '
            f'rotate={math.degrees(self._rot_angle):.0f}deg ({self._rotate_duration:.1f}s) '
            f'ir_thresh={self._ir_threshold}C')

    # ── Sensor callbacks ──────────────────────────────────────────────────────

    def _scan_callback(self, msg: LaserScan):
        """Update LiDAR obstacle flags — no logging here (runs at sensor rate)."""
        angle_min = msg.angle_min
        angle_inc = msg.angle_increment
        half      = self._front_arc
        front_obs = False
        critical  = False

        for i, r in enumerate(msg.ranges):
            if math.isnan(r) or math.isinf(r):
                continue
            angle = math.atan2(
                math.sin(angle_min + i * angle_inc),
                math.cos(angle_min + i * angle_inc))
            if r < self._critical_dist:
                critical = True
            if abs(angle) <= half and r < self._obstacle_dist:
                front_obs = True

        self._lidar_obstacle = front_obs
        self._lidar_critical = critical

    def _ultrasonic_callback(self, msg: String):
        """Update ultrasonic danger flag — no logging here."""
        self._ultrasonic_danger = 'DANGER' in msg.data

    def _ir_callback(self, msg: Temperature):
        """Flag if IR sensor detects a warm object (person / animal)."""
        self._ir_obstacle = msg.temperature >= self._ir_threshold

    # ── Control loop (runs at publish_hz) ────────────────────────────────────

    def _control_loop(self):
        twist = Twist()
        now   = self.get_clock().now().nanoseconds * 1e-9

        must_stop = self._lidar_obstacle or self._ultrasonic_danger or self._ir_obstacle

        if self._state == State.FORWARD:
            if must_stop:
                sources = []
                if self._lidar_obstacle:     sources.append('Lidar')
                if self._ultrasonic_danger:  sources.append('Ultrasonic')
                if self._ir_obstacle:        sources.append('IR-thermal')
                self.get_logger().info(
                    f'Obstacle [{", ".join(sources)}] -> STOPPING')
                self._state = State.STOPPING
            else:
                twist.linear.x = self._fwd_speed

        elif self._state == State.STOPPING:
            # One zero-velocity cycle, then begin rotation
            self.get_logger().info('Starting rotation')
            self._rotate_start = now
            self._state = State.ROTATING

        elif self._state == State.ROTATING:
            elapsed = now - self._rotate_start
            if self._lidar_critical:
                # Stay in ROTATING, pause spin, do NOT log every cycle
                self.get_logger().warn(
                    'Critical obstacle during rotation — holding',
                    throttle_duration_sec=1.0)
            elif elapsed < self._rotate_duration:
                twist.angular.z = self._rot_speed
            else:
                self.get_logger().info('Rotation complete -> FORWARD')
                self._state = State.FORWARD

        self._pub.publish(twist)

    def destroy_node(self):
        self._pub.publish(Twist())
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ObstacleAvoider()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
