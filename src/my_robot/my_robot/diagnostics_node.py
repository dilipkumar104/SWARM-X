#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
diagnostics_node.py — Robot Health Monitor

Watches topic heartbeats and publishes a robot_diagnostics summary.

Monitors:
    scan              — LiDAR alive?
    cmd_vel           — Commands flowing?
    odom              — Odometry alive?
    ultrasonic/status — HC-SR04 alive?
    ir/temperature    — MLX90614 IR sensor alive?

Publishes:
    robot_diagnostics  (std_msgs/String) — JSON health string every 5 s

Logging: only when overall status changes (HEALTHY <-> DEGRADED),
         not every cycle, to avoid I/O overhead on the Pi.
"""

import json
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import LaserScan, Temperature
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

TIMEOUT       = 3.0   # seconds — topic considered dead after this
REPORT_PERIOD_S = 5.0   # seconds between each diagnostic report


class DiagnosticsNode(Node):

    def __init__(self):
        super().__init__('diagnostics_node')

        now = self.get_clock().now()
        self._last = {
            'lidar':       now,
            'cmd_vel':     now,
            'odom':        now,
            'ultrasonic':  now,
            'ir_sensor':   now,
        }
        self._prev_overall = None   # suppress repeated identical logs

        # Subscribers — only update timestamps, zero processing overhead
        self.create_subscription(LaserScan, 'scan',
            lambda m: self._touch('lidar'),
            rclpy.qos.qos_profile_sensor_data)
        self.create_subscription(Twist, 'cmd_vel',
            lambda m: self._touch('cmd_vel'), 10)
        self.create_subscription(Odometry, 'odom',
            lambda m: self._touch('odom'), 10)
        self.create_subscription(String, 'ultrasonic/status',
            lambda m: self._touch('ultrasonic'), 10)
        self.create_subscription(Temperature, 'ir/temperature',
            lambda m: self._touch('ir_sensor'), 10)

        self._pub = self.create_publisher(String, 'robot_diagnostics', 10)

        # Report every REPORT_PERIOD_S seconds (5 s is plenty, reduces I/O)
        self.create_timer(REPORT_PERIOD_S, self._report)

        self.get_logger().info('Diagnostics Node started — monitoring 5 topics')

    def _touch(self, key: str):
        self._last[key] = self.get_clock().now()

    def _report(self):
        now    = self.get_clock().now()
        status = {}
        all_ok = True

        for key, last_t in self._last.items():
            elapsed = (now - last_t).nanoseconds * 1e-9
            ok = elapsed < TIMEOUT
            status[key] = 'OK' if ok else f'DEAD ({elapsed:.0f}s)'
            if not ok:
                all_ok = False

        overall = 'HEALTHY' if all_ok else 'DEGRADED'
        status['overall'] = overall

        msg = String()
        msg.data = json.dumps(status)
        self._pub.publish(msg)

        # Only log when the health status actually changes
        if overall != self._prev_overall:
            if all_ok:
                self.get_logger().info(f'[Diagnostics] {overall}: {status}')
            else:
                dead = [k for k, v in status.items() if 'DEAD' in str(v)]
                self.get_logger().warn(
                    f'[Diagnostics] {overall} — dead topics: {dead}')
            self._prev_overall = overall


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
