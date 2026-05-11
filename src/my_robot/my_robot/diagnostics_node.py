#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
diagnostics_node.py — Robot Health Monitor

Monitors topic heartbeats and publishes a /diagnostics summary.

Watches:
    /scan              — Lidar alive?
    /cmd_vel           — Commands flowing?
    /odom              — Odometry alive?
    /ultrasonic/status — HC-SR04 alive?

Publishes:
    /robot_diagnostics  (std_msgs/String)  — JSON-like health string every 2 s
"""

import json
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

TIMEOUT = 3.0   # seconds — topic considered dead after this


class DiagnosticsNode(Node):

    def __init__(self):
        super().__init__('diagnostics_node')

        now = self.get_clock().now()
        self._last = {
            'lidar':       now,
            'cmd_vel':     now,
            'odom':        now,
            'ultrasonic':  now,
        }

        # Subscribers — just update timestamps
        self.create_subscription(LaserScan, '/scan',
            lambda m: self._touch('lidar'),
            rclpy.qos.qos_profile_sensor_data)
        self.create_subscription(Twist, '/cmd_vel',
            lambda m: self._touch('cmd_vel'), 10)
        self.create_subscription(Odometry, '/odom',
            lambda m: self._touch('odom'), 10)
        self.create_subscription(String, '/ultrasonic/status',
            lambda m: self._touch('ultrasonic'), 10)

        # Publisher
        self._pub = self.create_publisher(String, '/robot_diagnostics', 10)

        # Report timer: every 2 s
        self.create_timer(2.0, self._report)

        self.get_logger().info('🩺 Diagnostics Node — Monitoring robot health')

    def _touch(self, key: str):
        self._last[key] = self.get_clock().now()

    def _report(self):
        now = self.get_clock().now()
        status = {}
        all_ok = True

        for key, last_t in self._last.items():
            elapsed = (now - last_t).nanoseconds * 1e-9
            ok = elapsed < TIMEOUT
            status[key] = 'OK' if ok else f'DEAD ({elapsed:.1f}s)'
            if not ok:
                all_ok = False

        status['overall'] = 'HEALTHY' if all_ok else 'DEGRADED'

        msg = String()
        msg.data = json.dumps(status)
        self._pub.publish(msg)

        level = self.get_logger().info if all_ok else self.get_logger().warn
        level(f'[Diagnostics] {status}')


def main(args=None):
    rclpy.init(args=args)
    node = DiagnosticsNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
