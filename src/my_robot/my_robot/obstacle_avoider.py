#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
obstacle_avoider.py — "Vacuum Cleaner" Lidar Obstacle Avoidance

State machine (runs as a ROS 2 node):

    ┌──────────────────────────────────────────────────────┐
    │  FORWARD  ──(obstacle < 0.5 m in front)──► STOPPING  │
    │  STOPPING ──(velocity zeroed)──────────► ROTATING    │
    │  ROTATING ──(90° complete)──────────────► FORWARD     │
    └──────────────────────────────────────────────────────┘

Subscribes to:
    /scan  (sensor_msgs/LaserScan)

Publishes to:
    /cmd_vel  (geometry_msgs/Twist)

Parameters (set via ros2 run ... --ros-args -p name:=value):
    obstacle_distance   (float, default 0.5)  — stop trigger distance [m]
    forward_speed       (float, default 0.2)  — cruise linear speed [m/s]
    rotate_speed        (float, default 0.5)  — yaw rate during rotation [rad/s]
    rotate_angle_deg    (float, default 90.0) — rotation target [degrees]
    front_arc_deg       (float, default 60.0) — ±half-angle of "front" arc
    publish_hz          (float, default 10.0) — cmd_vel publish rate [Hz]
"""

import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist


# ─────────────────────────────────────────────────────────────────────────────
# States
# ─────────────────────────────────────────────────────────────────────────────
class State:
    FORWARD  = 'FORWARD'
    STOPPING = 'STOPPING'
    ROTATING = 'ROTATING'


class ObstacleAvoider(Node):
    """
    Vacuum-cleaner obstacle avoidance: move forward until something is
    detected in front, stop, rotate 90°, then move forward again.
    """

    def __init__(self):
        super().__init__('obstacle_avoider')

        # ── Parameters ────────────────────────────────────────────────────
        self.declare_parameter('obstacle_distance', 0.5)
        self.declare_parameter('forward_speed',     0.2)
        self.declare_parameter('rotate_speed',      0.5)
        self.declare_parameter('rotate_angle_deg',  90.0)
        self.declare_parameter('front_arc_deg',     60.0)
        self.declare_parameter('publish_hz',        10.0)

        self._obstacle_dist = self.get_parameter('obstacle_distance').value
        self._fwd_speed     = self.get_parameter('forward_speed').value
        self._rot_speed     = self.get_parameter('rotate_speed').value
        self._rot_angle     = math.radians(
            self.get_parameter('rotate_angle_deg').value
        )
        self._front_arc     = math.radians(
            self.get_parameter('front_arc_deg').value
        )
        hz = self.get_parameter('publish_hz').value

        # ── State machine ─────────────────────────────────────────────────
        self._state        = State.FORWARD
        self._rotate_start: float | None = None   # wall-clock (seconds)
        self._rotate_duration = self._rot_angle / abs(self._rot_speed)

        # ── Latched scan data ─────────────────────────────────────────────
        self._obstacle_ahead = False

        # ── Publisher: /cmd_vel ───────────────────────────────────────────
        self._pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # ── Subscriber: /scan ─────────────────────────────────────────────
        self._sub = self.create_subscription(
            LaserScan,
            '/scan',
            self._scan_callback,
            rclpy.qos.qos_profile_sensor_data,
        )

        # ── Control loop timer ────────────────────────────────────────────
        self._timer = self.create_timer(1.0 / hz, self._control_loop)

        self.get_logger().info('━' * 60)
        self.get_logger().info('  🛡  Obstacle Avoider — Node Started')
        self.get_logger().info(
            f'  Obstacle threshold : {self._obstacle_dist} m'
        )
        self.get_logger().info(
            f'  Front arc (half)   : {math.degrees(self._front_arc):.0f}°'
        )
        self.get_logger().info(
            f'  Rotation target    : {math.degrees(self._rot_angle):.0f}°'
            f'  ({self._rotate_duration:.2f} s)'
        )
        self.get_logger().info('━' * 60)

    # ── LaserScan callback ────────────────────────────────────────────────────
    def _scan_callback(self, msg: LaserScan):
        """
        Check whether any range reading in the front arc is below the
        obstacle threshold.  Angles are measured from the sensor's zero:
            0 rad → straight ahead (for most lidars)
            Positive → CCW (left),  Negative → CW (right)
        """
        angle_min = msg.angle_min
        angle_inc = msg.angle_increment

        half = self._front_arc
        obstacle_found = False

        for i, r in enumerate(msg.ranges):
            angle = angle_min + i * angle_inc

            # Normalise to (−π, π]
            angle = math.atan2(math.sin(angle), math.cos(angle))

            if abs(angle) > half:
                continue          # outside the front arc

            if math.isnan(r) or math.isinf(r):
                continue          # bad reading

            if r < self._obstacle_dist:
                obstacle_found = True
                break

        self._obstacle_ahead = obstacle_found

    # ── Control loop ──────────────────────────────────────────────────────────
    def _control_loop(self):
        """State-machine tick — called at publish_hz."""
        twist = Twist()
        now   = self.get_clock().now().nanoseconds * 1e-9

        # ── FORWARD ───────────────────────────────────────────────────────
        if self._state == State.FORWARD:
            if self._obstacle_ahead:
                self.get_logger().info(
                    '🚨 Obstacle detected — STOPPING'
                )
                self._state = State.STOPPING
            else:
                twist.linear.x = self._fwd_speed

        # ── STOPPING (publish zero for one cycle to ensure motors stop) ───
        elif self._state == State.STOPPING:
            # twist is already zeroed; transition immediately
            self.get_logger().info('🔄 Starting 90° rotation')
            self._rotate_start = now
            self._state = State.ROTATING

        # ── ROTATING ─────────────────────────────────────────────────────
        elif self._state == State.ROTATING:
            elapsed = now - self._rotate_start
            if elapsed < self._rotate_duration:
                twist.angular.z = self._rot_speed
            else:
                self.get_logger().info('✅ Rotation complete — resuming FORWARD')
                self._state = State.FORWARD

        self._pub.publish(twist)


# ─────────────────────────────────────────────────────────────────────────────
def main(args=None):
    """Entry point — called by ros2 run my_robot obstacle_avoider."""
    rclpy.init(args=args)
    node = ObstacleAvoider()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down obstacle avoider.')
    finally:
        # Publish a zero Twist before exiting so the robot stops
        stop = Twist()
        node._pub.publish(stop)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
