#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
ultrasonic_simulator.py — Simulated Ultrasonic Sensor Publisher

Publishes fake sensor_msgs/msg/Range data to ultrasonic/range so you
can test the ultrasonic_listener node WITHOUT any ESP32 hardware.

The simulated distance sweeps from 2 cm → 400 cm → 2 cm in a triangle
wave pattern, triggering DANGER / WARNING / CLEAR zones in the listener.

Usage (after building & sourcing):
    ros2 run my_robot ultrasonic_simulator

    # Then in another terminal:
    ros2 run my_robot ultrasonic_listener
"""

import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Range


class UltrasonicSimulator(Node):
    """
    Publishes simulated Range messages to ultrasonic/range.

    The distance sweeps linearly between MIN_RANGE and MAX_RANGE in a
    triangle-wave pattern so the listener exercises all code paths
    (DANGER → WARNING → CLEAR and back).
    """

    # ── Sensor constants (same as HC-SR04) ─────────────────────────
    MIN_RANGE = 0.02    # 2 cm
    MAX_RANGE = 4.00    # 400 cm
    FOV_RAD = 0.2618    # ~15° half-angle
    PUBLISH_HZ = 10     # 10 Hz like the real ESP32 firmware
    SWEEP_SPEED = 0.05  # metres per tick (controls sweep pace)

    def __init__(self):
        super().__init__('ultrasonic_simulator')

        # ── Publisher: ultrasonic/range (relative topic) ───────────
        self.pub = self.create_publisher(
            Range, 'ultrasonic/range',
            rclpy.qos.qos_profile_sensor_data)

        # ── Timer at PUBLISH_HZ ────────────────────────────────────
        self.timer = self.create_timer(1.0 / self.PUBLISH_HZ, self._tick)

        # ── Sweep state ────────────────────────────────────────────
        self._distance = self.MIN_RANGE
        self._direction = 1  # 1 = increasing, -1 = decreasing
        self._count = 0

        # ── Startup banner ─────────────────────────────────────────
        self.get_logger().info('━' * 60)
        self.get_logger().info('  🧪 Ultrasonic SIMULATOR (no hardware needed)')
        self.get_logger().info(f'  Publishing to ultrasonic/range at {self.PUBLISH_HZ} Hz')
        self.get_logger().info(f'  Sweep: {self.MIN_RANGE * 100:.0f} cm ↔ {self.MAX_RANGE * 100:.0f} cm')
        self.get_logger().info('━' * 60)

    def _tick(self):
        """Called at PUBLISH_HZ. Publishes one simulated Range message."""

        msg = Range()

        # ── Header ─────────────────────────────────────────────────
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'ultrasonic_link'

        # ── Static sensor metadata ─────────────────────────────────
        msg.radiation_type = Range.ULTRASOUND
        msg.field_of_view = self.FOV_RAD
        msg.min_range = self.MIN_RANGE
        msg.max_range = self.MAX_RANGE

        # ── Simulated distance (triangle wave) ─────────────────────
        msg.range = self._distance
        self.pub.publish(msg)

        self._count += 1
        if self._count % self.PUBLISH_HZ == 0:  # Log once per second
            self.get_logger().info(
                f'[{self._count}] Simulated range: {self._distance * 100:.1f} cm'
            )

        # ── Advance sweep ──────────────────────────────────────────
        self._distance += self.SWEEP_SPEED * self._direction
        if self._distance >= self.MAX_RANGE:
            self._distance = self.MAX_RANGE
            self._direction = -1
        elif self._distance <= self.MIN_RANGE:
            self._distance = self.MIN_RANGE
            self._direction = 1


def main(args=None):
    """Entry point for the ultrasonic_simulator node."""
    rclpy.init(args=args)
    node = UltrasonicSimulator()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down ultrasonic simulator.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
