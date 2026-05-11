#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
obstacle_avoider.py — "Vacuum Cleaner" Lidar + Ultrasonic Obstacle Avoidance

State machine:

    ┌──────────────────────────────────────────────────────────────┐
    │ FORWARD  ─(obstacle in front OR ultrasonic DANGER)─► STOPPING│
    │ STOPPING ─(zeroed)─────────────────────────────────► ROTATING │
    │ ROTATING ─(90° done AND path clear)────────────────► FORWARD  │
    └──────────────────────────────────────────────────────────────┘

Subscribes:
    /scan               (sensor_msgs/LaserScan)   — Lidar
    /ultrasonic/status  (std_msgs/String)          — HC-SR04 fusion

Publishes:
    /cmd_vel  (geometry_msgs/Twist)

All thresholds are ROS 2 parameters — override at launch time.
"""

import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from std_msgs.msg import String


# ─────────────────────────────────────────────────────────────────────────────
class State:
    FORWARD  = 'FORWARD'
    STOPPING = 'STOPPING'
    ROTATING = 'ROTATING'


class ObstacleAvoider(Node):
    """
    Vacuum-cleaner obstacle avoidance fusing Lidar (LaserScan) and the
    HC-SR04 ultrasonic sensor (/ultrasonic/status).
    """

    def __init__(self):
        super().__init__('obstacle_avoider')

        # ── Parameters ────────────────────────────────────────────────────
        self.declare_parameter('obstacle_distance',   0.5)    # Lidar stop [m]
        self.declare_parameter('critical_distance',   0.15)   # abort-rotation [m]
        self.declare_parameter('forward_speed',       0.2)    # cruise [m/s]
        self.declare_parameter('rotate_speed',        0.5)    # yaw [rad/s]
        self.declare_parameter('rotate_angle_deg',    90.0)   # rotation target [deg]
        self.declare_parameter('front_arc_deg',       60.0)   # ±half-angle [deg]
        self.declare_parameter('publish_hz',          10.0)

        self._obstacle_dist  = self.get_parameter('obstacle_distance').value
        self._critical_dist  = self.get_parameter('critical_distance').value
        self._fwd_speed      = self.get_parameter('forward_speed').value
        self._rot_speed      = self.get_parameter('rotate_speed').value
        self._rot_angle      = math.radians(
            self.get_parameter('rotate_angle_deg').value)
        self._front_arc      = math.radians(
            self.get_parameter('front_arc_deg').value)
        hz                   = self.get_parameter('publish_hz').value

        # ── State machine ─────────────────────────────────────────────────
        self._state              = State.FORWARD
        self._rotate_start: float | None = None
        self._rotate_duration    = self._rot_angle / abs(self._rot_speed)

        # ── Sensor data (latched) ─────────────────────────────────────────
        self._lidar_obstacle     = False   # any lidar beam < obstacle_dist in front arc
        self._lidar_critical     = False   # any lidar beam < critical_dist (any direction)
        self._ultrasonic_danger  = False   # HC-SR04 DANGER zone

        # ── Publisher ─────────────────────────────────────────────────────
        self._pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # ── Subscribers ───────────────────────────────────────────────────
        self._scan_sub = self.create_subscription(
            LaserScan,
            '/scan',
            self._scan_callback,
            rclpy.qos.qos_profile_sensor_data,
        )

        self._ultrasonic_sub = self.create_subscription(
            String,
            '/ultrasonic/status',
            self._ultrasonic_callback,
            10,
        )

        # ── Control loop ─────────────────────────────────────────────────
        self._timer = self.create_timer(1.0 / hz, self._control_loop)

        self.get_logger().info('━' * 60)
        self.get_logger().info('  🛡  Obstacle Avoider v2 — Node Started')
        self.get_logger().info(
            f'  Lidar stop      : {self._obstacle_dist} m  '
            f'(front ±{math.degrees(self._front_arc):.0f}°)')
        self.get_logger().info(
            f'  Critical abort  : {self._critical_dist} m')
        self.get_logger().info(
            f'  Rotation target : {math.degrees(self._rot_angle):.0f}°'
            f'  ({self._rotate_duration:.2f} s)')
        self.get_logger().info(
            '  Fusing: /scan + /ultrasonic/status')
        self.get_logger().info('━' * 60)

    # ── /scan callback ────────────────────────────────────────────────────────
    def _scan_callback(self, msg: LaserScan):
        """Update lidar flags from the latest LaserScan."""
        angle_min = msg.angle_min
        angle_inc = msg.angle_increment
        half      = self._front_arc

        front_obstacle = False
        critical       = False

        for i, r in enumerate(msg.ranges):
            if math.isnan(r) or math.isinf(r):
                continue

            angle = math.atan2(
                math.sin(angle_min + i * angle_inc),
                math.cos(angle_min + i * angle_inc),
            )

            # Critical: any beam any direction
            if r < self._critical_dist:
                critical = True

            # Front arc check
            if abs(angle) <= half and r < self._obstacle_dist:
                front_obstacle = True

        self._lidar_obstacle = front_obstacle
        self._lidar_critical = critical

    # ── /ultrasonic/status callback ───────────────────────────────────────────
    def _ultrasonic_callback(self, msg: String):
        """Fuse HC-SR04 status into obstacle detection."""
        self._ultrasonic_danger = 'DANGER' in msg.data

    # ── Control loop ──────────────────────────────────────────────────────────
    def _control_loop(self):
        """State-machine tick."""
        twist = Twist()
        now   = self.get_clock().now().nanoseconds * 1e-9

        # Combined stop condition: Lidar OR Ultrasonic
        must_stop = self._lidar_obstacle or self._ultrasonic_danger

        if self._state == State.FORWARD:
            if must_stop:
                src = []
                if self._lidar_obstacle:
                    src.append('Lidar')
                if self._ultrasonic_danger:
                    src.append('Ultrasonic')
                self.get_logger().info(
                    f'🚨 Obstacle [{", ".join(src)}] — STOPPING')
                self._state = State.STOPPING

            else:
                twist.linear.x = self._fwd_speed

        elif self._state == State.STOPPING:
            # Zero velocity for one cycle, then begin rotation
            self.get_logger().info('🔄 Starting 90° rotation')
            self._rotate_start = now
            self._state = State.ROTATING

        elif self._state == State.ROTATING:
            elapsed = now - self._rotate_start

            # Safety: abort rotation if something is critically close
            if self._lidar_critical:
                self.get_logger().warn(
                    '⚠  Critical obstacle during rotation — pausing turn')
                # Stay in ROTATING but don't spin; wait for clearance
            elif elapsed < self._rotate_duration:
                twist.angular.z = self._rot_speed
            else:
                self.get_logger().info(
                    '✅ Rotation complete — resuming FORWARD')
                self._state = State.FORWARD

        self._pub.publish(twist)

    def destroy_node(self):
        self._pub.publish(Twist())   # Safe stop before shutdown
        super().destroy_node()


# ─────────────────────────────────────────────────────────────────────────────
def main(args=None):
    rclpy.init(args=args)
    node = ObstacleAvoider()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down obstacle avoider.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
