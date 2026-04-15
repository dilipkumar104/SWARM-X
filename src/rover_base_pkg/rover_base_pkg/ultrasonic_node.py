#!/usr/bin/env python3
"""
ultrasonic_node.py

Reads ultrasonic distance data from ESP32 via UART serial.
Parses the "DIST:XX" protocol and publishes to /ultrasonic topic.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
import serial
import serial.tools.list_ports


# ── Serial Configuration ──────────────────────────────────────────────
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 115200
SERIAL_TIMEOUT = 1.0  # seconds


class UltrasonicNode(Node):
    """ROS2 node that reads ultrasonic distance from ESP32 and publishes it."""

    def __init__(self):
        super().__init__('ultrasonic_node')

        # ── Parameters (overridable at launch) ────────────────────────
        self.declare_parameter('serial_port', SERIAL_PORT)
        self.declare_parameter('baud_rate', BAUD_RATE)

        port = self.get_parameter('serial_port').get_parameter_value().string_value
        baud = self.get_parameter('baud_rate').get_parameter_value().integer_value

        # ── Publisher ─────────────────────────────────────────────────
        self.publisher_ = self.create_publisher(Float32, '/ultrasonic', 10)

        # ── Serial port setup ────────────────────────────────────────
        try:
            self.ser = serial.Serial(port, baud, timeout=SERIAL_TIMEOUT)
            self.get_logger().info(f'Serial opened on {port} @ {baud} baud')
        except serial.SerialException as e:
            self.get_logger().error(f'Failed to open serial port {port}: {e}')
            self.ser = None

        # ── Timer: read serial every 100 ms ──────────────────────────
        self.timer = self.create_timer(0.1, self.timer_callback)

    def timer_callback(self):
        """Read a line from serial, parse DIST:XX, and publish."""
        if self.ser is None or not self.ser.is_open:
            return

        try:
            # Read all available lines, keep the latest
            raw = ''
            while self.ser.in_waiting > 0:
                raw = self.ser.readline().decode('utf-8', errors='ignore').strip()

            if not raw:
                return

            # Parse protocol: "DIST:XX"
            if raw.startswith('DIST:'):
                value_str = raw[5:]  # everything after "DIST:"
                try:
                    distance = float(value_str)
                    msg = Float32()
                    msg.data = distance
                    self.publisher_.publish(msg)
                    self.get_logger().debug(f'Published distance: {distance} cm')
                except ValueError:
                    self.get_logger().warn(f'Invalid distance value: "{value_str}"')
            else:
                self.get_logger().debug(f'Ignored non-DIST line: "{raw}"')

        except serial.SerialException as e:
            self.get_logger().error(f'Serial read error: {e}')
        except Exception as e:
            self.get_logger().error(f'Unexpected error: {e}')

    def destroy_node(self):
        """Clean up serial port on shutdown."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.get_logger().info('Serial port closed')
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = UltrasonicNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
