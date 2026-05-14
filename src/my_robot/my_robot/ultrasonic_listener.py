#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
ultrasonic_listener.py — ROS2 Ultrasonic Sensor Listener Node

Subscribes to ultrasonic/range (sensor_msgs/Range) from ESP32 micro-ROS.
Classifies distance into DANGER / WARNING / CLEAR and republishes as
/ultrasonic/status (std_msgs/String) for the obstacle avoider.

Logging only fires on zone changes or connection events — not every packet.
"""

import math
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import Range
from std_msgs.msg import String

MICRO_ROS_QOS = QoSProfile(
    reliability=QoSReliabilityPolicy.BEST_EFFORT,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=10,
)

DANGER_THRESHOLD  = 0.10   # < 10 cm
WARNING_THRESHOLD = 0.30   # < 30 cm
TIMEOUT_SEC       = 3.0    # seconds without message -> disconnected


class UltrasonicListener(Node):
    """Listener for HC-SR04 range data. Logs only on state changes."""

    def __init__(self):
        super().__init__('ultrasonic_listener')

        self._connected    = False
        self._last_msg_time = None
        self._prev_label   = None   # track last zone to suppress duplicate logs

        self.range_sub = self.create_subscription(
            Range, 'ultrasonic/range', self._range_callback, MICRO_ROS_QOS)
        self.status_pub = self.create_publisher(String, 'ultrasonic/status', 10)

        # Watchdog checks connectivity every 1 s — lightweight
        self.create_timer(1.0, self._watchdog_callback)

        self.get_logger().info('Ultrasonic Listener started — waiting for ultrasonic/range')

    def _range_callback(self, msg: Range):
        now = self.get_clock().now()
        self._last_msg_time = now

        if not self._connected:
            self._connected = True
            self.get_logger().info(
                f'ESP32 connected | frame={msg.header.frame_id} '
                f'range={msg.min_range:.2f}-{msg.max_range:.2f}m')

        distance = msg.range

        if math.isinf(distance) or math.isnan(distance):
            label = 'INVALID'
            if label != self._prev_label:
                self.get_logger().warn('Ultrasonic: invalid reading (inf/NaN)')
                self._prev_label = label
            self._publish_status(label, distance)
            return

        if distance < msg.min_range or distance > msg.max_range:
            label = 'OUT-OF-RANGE'
        elif distance < DANGER_THRESHOLD:
            label = 'DANGER'
        elif distance < WARNING_THRESHOLD:
            label = 'WARNING'
        else:
            label = 'CLEAR'

        # Only log when the zone changes — avoids flooding at 10+ Hz
        if label != self._prev_label:
            self.get_logger().info(
                f'Ultrasonic zone: {self._prev_label} -> {label} ({distance*100:.1f} cm)')
            self._prev_label = label

        self._publish_status(label, distance)

    def _watchdog_callback(self):
        if self._last_msg_time is None:
            return
        elapsed = (self.get_clock().now() - self._last_msg_time).nanoseconds / 1e9
        if self._connected and elapsed > TIMEOUT_SEC:
            self._connected = False
            self.get_logger().error(
                f'ESP32 disconnected — no data for {elapsed:.1f}s')
            msg = String()
            msg.data = 'DISCONNECTED'
            self.status_pub.publish(msg)

    def _publish_status(self, label: str, distance: float):
        msg = String()
        msg.data = f'{label} | {distance * 100:.1f} cm'
        self.status_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = UltrasonicListener()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
