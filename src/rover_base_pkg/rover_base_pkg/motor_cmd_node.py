#!/usr/bin/env python3
"""
motor_cmd_node.py

Subscribes to /cmd_vel (geometry_msgs/Twist) and converts velocity commands
into single-character motor commands sent to ESP32 via UART serial.

Command mapping:
  F → Forward   (linear.x > 0)
  B → Backward  (linear.x < 0)
  L → Left      (angular.z > 0)
  R → Right     (angular.z < 0)
  S → Stop      (all zero)
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import serial


# ── Serial Configuration ──────────────────────────────────────────────
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 115200
SERIAL_TIMEOUT = 1.0

# Minimum threshold to avoid jitter from near-zero values
LINEAR_THRESHOLD = 0.05
ANGULAR_THRESHOLD = 0.05


class MotorCmdNode(Node):
    """ROS2 node that converts /cmd_vel into serial motor commands for ESP32."""

    def __init__(self):
        super().__init__('motor_cmd_node')

        # ── Parameters (overridable at launch) ────────────────────────
        self.declare_parameter('serial_port', SERIAL_PORT)
        self.declare_parameter('baud_rate', BAUD_RATE)

        port = self.get_parameter('serial_port').get_parameter_value().string_value
        baud = self.get_parameter('baud_rate').get_parameter_value().integer_value

        # ── Subscriber ───────────────────────────────────────────────
        self.subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10
        )

        # ── Serial port setup ────────────────────────────────────────
        try:
            self.ser = serial.Serial(port, baud, timeout=SERIAL_TIMEOUT)
            self.get_logger().info(f'Serial opened on {port} @ {baud} baud')
        except serial.SerialException as e:
            self.get_logger().error(f'Failed to open serial port {port}: {e}')
            self.ser = None

        # Track last command to avoid flooding the serial bus
        self.last_command = ''

    def cmd_vel_callback(self, msg: Twist):
        """Convert Twist message to a single-character motor command."""
        linear_x = msg.linear.x
        angular_z = msg.angular.z

        # ── Determine command ─────────────────────────────────────────
        if abs(linear_x) < LINEAR_THRESHOLD and abs(angular_z) < ANGULAR_THRESHOLD:
            command = 'S'  # Stop
        elif abs(angular_z) >= ANGULAR_THRESHOLD:
            # Turning takes priority over forward/backward
            command = 'L' if angular_z > 0 else 'R'
        else:
            command = 'F' if linear_x > 0 else 'B'

        # ── Send only if command changed (avoid serial flooding) ──────
        if command != self.last_command:
            self.send_command(command)
            self.last_command = command

    def send_command(self, command: str):
        """Send a single-character command to ESP32 via serial."""
        if self.ser is None or not self.ser.is_open:
            self.get_logger().warn('Serial port not available, cannot send command')
            return

        try:
            self.ser.write(command.encode('utf-8'))
            self.ser.flush()
            self.get_logger().info(f'Sent motor command: {command}')
        except serial.SerialException as e:
            self.get_logger().error(f'Serial write error: {e}')

    def destroy_node(self):
        """Send STOP and close serial on shutdown."""
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(b'S')  # Stop motors before shutting down
                self.ser.flush()
            except serial.SerialException:
                pass
            self.ser.close()
            self.get_logger().info('Serial port closed (motors stopped)')
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MotorCmdNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
