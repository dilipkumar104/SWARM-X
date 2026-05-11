#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
simple_obstacle_avoider.py — Simple (V1) Obstacle Avoider

LEGACY node — kept for reference only.
Use obstacle_avoider (V2) for production; it has state-machine rotation
and ultrasonic fusion.

This V1 node:
  - Checks all 360° of Lidar (not just front arc)
  - Stops when ANY beam < threshold (15 cm)
  - Does NOT rotate — just stops and waits for path to clear
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist


class SimpleObstacleAvoider(Node):
    """V1 simple stop-only avoider (no rotation, full 360° check)."""

    def __init__(self):
        super().__init__('simple_obstacle_avoider')

        self.declare_parameter('obstacle_threshold', 0.15)
        self.declare_parameter('forward_speed', 0.22)

        self.threshold = self.get_parameter('obstacle_threshold').value
        self.forward_speed = self.get_parameter('forward_speed').value

        self.scan_sub = self.create_subscription(
            LaserScan, 'scan', self._scan_callback, 10)
        self.cmd_pub = self.create_publisher(Twist, 'cmd_vel', 10)

        self._obstacle_detected = False
        self._scan_count = 0

        self.get_logger().info('━' * 60)
        self.get_logger().info('  ⚠  Simple Obstacle Avoider V1 (LEGACY)')
        self.get_logger().info('  Use obstacle_avoider (V2) for production!')
        self.get_logger().info(f'  Threshold: {self.threshold * 100:.0f} cm')
        self.get_logger().info('━' * 60)

    def _scan_callback(self, msg: LaserScan):
        self._scan_count += 1
        obstacle_found = False
        closest = float('inf')

        for dist in msg.ranges:
            if dist < msg.range_min or dist > msg.range_max:
                continue
            if dist < closest:
                closest = dist
            if dist <= self.threshold:
                obstacle_found = True
                break

        cmd = Twist()
        if obstacle_found:
            cmd.linear.x = 0.0
            if not self._obstacle_detected:
                self.get_logger().warn(
                    f'🔴 OBSTACLE at {closest * 100:.1f} cm — STOPPING!')
                self._obstacle_detected = True
        else:
            cmd.linear.x = self.forward_speed
            if self._obstacle_detected:
                self.get_logger().info(
                    f'🟢 Path clear ({closest * 100:.1f} cm) — moving')
                self._obstacle_detected = False

        self.cmd_pub.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    node = SimpleObstacleAvoider()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        stop = Twist()
        node.cmd_pub.publish(stop)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
