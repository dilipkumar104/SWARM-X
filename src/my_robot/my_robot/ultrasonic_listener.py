#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
ultrasonic_listener.py — ROS2 Ultrasonic Sensor Listener Node

Subscribes to ultrasonic/range (sensor_msgs/msg/Range) published by an
ESP32 running micro-ROS or the ultrasonic_simulator node, and provides:

  • Connection detection   — logs when ESP32 comes online / goes offline
  • Sensor health          — validates readings and flags out-of-range data
  • Proximity alerts       — DANGER / WARNING / CLEAR based on distance
  • Status republishing    — publishes /ultrasonic/status (String) downstream

Usage (after building & sourcing):
    ros2 run my_robot ultrasonic_listener
"""

import rclpy                                # ROS2 Python client library
from rclpy.node import Node                 # Base class for ROS2 nodes
from rclpy.qos import (                     # Quality-of-Service profiles
    QoSProfile,
    QoSReliabilityPolicy,
    QoSHistoryPolicy,
)
from sensor_msgs.msg import Range           # Standard range message
from std_msgs.msg import String             # For status republishing
import math                                 # For inf / NaN checks


# ── QoS profile tuned for micro-ROS over serial ────────────────────────
MICRO_ROS_QOS = QoSProfile(
    reliability=QoSReliabilityPolicy.BEST_EFFORT,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=10,
)


class UltrasonicListener(Node):
    """
    ROS2 subscriber node for ultrasonic range data from an ESP32.

    Topics:
        Subscribes : ultrasonic/range   (sensor_msgs/msg/Range)  [relative]
        Publishes  : ultrasonic/status  (std_msgs/msg/String)    [relative]

    Behaviour:
        1. Detects when the ESP32 first connects (first message received).
        2. Monitors for connection loss (no message for >3 seconds).
        3. Validates each reading against min_range / max_range.
        4. Classifies distance into DANGER / WARNING / CLEAR zones.
        5. Re-publishes a human-readable status string.
    """

    # ── Proximity thresholds (metres) ──────────────────────────────────
    DANGER_THRESHOLD  = 0.10   # < 10 cm
    WARNING_THRESHOLD = 0.30   # < 30 cm

    # ── Connection watchdog ────────────────────────────────────────────
    TIMEOUT_SEC = 3.0          # seconds without a message → "disconnected"

    def __init__(self):
        super().__init__('ultrasonic_listener')

        # ── State ──────────────────────────────────────────────────────
        self._connected = False          # Has ESP32 ever sent a message?
        self._message_count = 0          # Total messages received
        self._last_msg_time = None       # Timestamp of last message

        # ── Subscriber: /ultrasonic/range ──────────────────────────────
        self.range_sub = self.create_subscription(
            Range,
            'ultrasonic/range',
            self._range_callback,
            MICRO_ROS_QOS,
        )

        # ── Publisher: /ultrasonic/status ──────────────────────────────
        self.status_pub = self.create_publisher(String, 'ultrasonic/status', 10)

        # ── Watchdog timer — checks connectivity every 1 s ────────────
        self._watchdog_timer = self.create_timer(1.0, self._watchdog_callback)

        # ── Startup banner ─────────────────────────────────────────────
        self.get_logger().info('━' * 60)
        self.get_logger().info('  🤖 SWARM-X Ultrasonic Listener')
        self.get_logger().info('  Waiting for data on ultrasonic/range ...')
        self.get_logger().info('━' * 60)

    # ──────────────────────────────────────────────────────────────────
    #  CALLBACKS
    # ──────────────────────────────────────────────────────────────────

    def _range_callback(self, msg: Range):
        """Process every incoming Range message from the ESP32."""

        now = self.get_clock().now()
        self._last_msg_time = now
        self._message_count += 1

        # ── First-ever message → ESP32 just connected ─────────────────
        if not self._connected:
            self._connected = True
            self.get_logger().info('━' * 60)
            self.get_logger().info('  ✅ ESP32 CONNECTED — receiving sensor data')
            self.get_logger().info(f'  Frame ID       : {msg.header.frame_id}')
            self.get_logger().info(f'  Radiation type : '
                                   f'{"Ultrasound" if msg.radiation_type == Range.ULTRASOUND else "IR"}')
            self.get_logger().info(f'  FOV            : {math.degrees(msg.field_of_view):.1f}°')
            self.get_logger().info(f'  Min range      : {msg.min_range:.2f} m')
            self.get_logger().info(f'  Max range      : {msg.max_range:.2f} m')
            self.get_logger().info('━' * 60)

        # ── Validate reading ──────────────────────────────────────────
        distance = msg.range
        if math.isinf(distance) or math.isnan(distance):
            label = '❌ INVALID'
            detail = 'Sensor returned inf/NaN — object out of measurable range'
            self.get_logger().warn(f'[{self._message_count}] {label}: {detail}')
            self._publish_status(label, distance)
            return

        if distance < msg.min_range or distance > msg.max_range:
            label = '⚠️  OUT-OF-RANGE'
            detail = (f'{distance * 100:.1f} cm  '
                      f'(valid: {msg.min_range * 100:.0f}–{msg.max_range * 100:.0f} cm)')
            self.get_logger().warn(f'[{self._message_count}] {label}: {detail}')
            self._publish_status(label, distance)
            return

        # ── Classify distance ─────────────────────────────────────────
        if distance < self.DANGER_THRESHOLD:
            label = '🔴 DANGER'
            detail = f'{distance * 100:.1f} cm — Object VERY close!'
        elif distance < self.WARNING_THRESHOLD:
            label = '🟡 WARNING'
            detail = f'{distance * 100:.1f} cm — Object nearby'
        else:
            label = '🟢 CLEAR'
            detail = f'{distance * 100:.1f} cm'

        self.get_logger().info(f'[{self._message_count}] {label}: {detail}')
        self._publish_status(label, distance)

    def _watchdog_callback(self):
        """Periodically check for connection loss."""

        if self._last_msg_time is None:
            # Still waiting for first message — no-op
            return

        elapsed = (self.get_clock().now() - self._last_msg_time).nanoseconds / 1e9

        if self._connected and elapsed > self.TIMEOUT_SEC:
            self._connected = False
            self.get_logger().error('━' * 60)
            self.get_logger().error(
                f'  ❌ ESP32 DISCONNECTED — no data for {elapsed:.1f}s'
            )
            self.get_logger().error('  Check USB cable / micro-ROS agent')
            self.get_logger().error('━' * 60)

            # Publish disconnect status
            status_msg = String()
            status_msg.data = 'DISCONNECTED'
            self.status_pub.publish(status_msg)

    # ──────────────────────────────────────────────────────────────────
    #  HELPERS
    # ──────────────────────────────────────────────────────────────────

    def _publish_status(self, label: str, distance: float):
        """Publish a human-readable status string on /ultrasonic/status."""
        status_msg = String()
        status_msg.data = f'{label} | {distance * 100:.1f} cm'
        self.status_pub.publish(status_msg)


def main(args=None):
    """
    Entry point for the ultrasonic_listener node.

    Flow:
        1. rclpy.init()      — Initialize the ROS2 communication layer
        2. Create the node   — Instantiate UltrasonicListener
        3. rclpy.spin()      — Keep the node alive, processing callbacks
        4. Cleanup           — Destroy node and shut down rclpy
    """

    rclpy.init(args=args)
    node = UltrasonicListener()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Keyboard interrupt — shutting down.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


# Allow running directly with: python3 ultrasonic_listener.py
if __name__ == '__main__':
    main()
