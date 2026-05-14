#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
motor_controller.py — L298N Dual H-Bridge Motor Controller

Subscribes to /cmd_vel (geometry_msgs/Twist) and drives four DC motors
in a differential-drive layout.

Wiring (BCM numbering):
    GPIO 12 -> EnA (left PWM)   GPIO 23 -> In1   GPIO 24 -> In2
    GPIO 13 -> EnB (right PWM)  GPIO 27 -> In3   GPIO 22 -> In4
    Pi GND  -> L298N GND  <-- shared ground is CRITICAL

Safety heartbeat: motors stop if no /cmd_vel received within HEARTBEAT_TIMEOUT s.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

try:
    import RPi.GPIO as GPIO
    _GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    _GPIO_AVAILABLE = False

    class _MockGPIO:
        BCM = OUT = IN = HIGH = LOW = BOARD = 0

        class PWM:
            def __init__(self, pin, freq): pass
            def start(self, dc): pass
            def ChangeDutyCycle(self, dc): pass
            def stop(self): pass

        def setmode(self, _): pass
        def setwarnings(self, _): pass
        def setup(self, pins, mode): pass
        def output(self, pins, state): pass
        def cleanup(self): pass

    GPIO = _MockGPIO()


# ── Wiring constants (BCM) — edit to match your wiring ──────────────────────
ENA_PIN  = 12
IN1_PIN  = 23
IN2_PIN  = 24
ENB_PIN  = 13
IN3_PIN  = 27
IN4_PIN  = 22

PWM_FREQUENCY     = 1000   # Hz
MAX_SPEED         = 1.0    # m/s
TRACK_WIDTH       = 0.20   # metres
HEARTBEAT_TIMEOUT = 0.5    # seconds


class MotorController(Node):
    """ROS 2 node that drives four DC motors via an L298N H-bridge."""

    def __init__(self):
        super().__init__('motor_controller')

        # Parameters
        self.declare_parameter('ena_pin',           ENA_PIN)
        self.declare_parameter('in1_pin',           IN1_PIN)
        self.declare_parameter('in2_pin',           IN2_PIN)
        self.declare_parameter('enb_pin',           ENB_PIN)
        self.declare_parameter('in3_pin',           IN3_PIN)
        self.declare_parameter('in4_pin',           IN4_PIN)
        self.declare_parameter('pwm_frequency',     PWM_FREQUENCY)
        self.declare_parameter('max_speed',         MAX_SPEED)
        self.declare_parameter('track_width',       TRACK_WIDTH)
        self.declare_parameter('heartbeat_timeout', HEARTBEAT_TIMEOUT)

        self._ena        = self.get_parameter('ena_pin').value
        self._in1        = self.get_parameter('in1_pin').value
        self._in2        = self.get_parameter('in2_pin').value
        self._enb        = self.get_parameter('enb_pin').value
        self._in3        = self.get_parameter('in3_pin').value
        self._in4        = self.get_parameter('in4_pin').value
        self._pwm_freq   = self.get_parameter('pwm_frequency').value
        self._max_speed  = self.get_parameter('max_speed').value
        self._track_half = self.get_parameter('track_width').value / 2.0
        self._hb_timeout = self.get_parameter('heartbeat_timeout').value

        self._init_gpio()

        self._sub = self.create_subscription(
            Twist, '/cmd_vel', self._cmd_vel_callback, 10)

        self._last_msg_time = self.get_clock().now()
        self._watchdog = self.create_timer(
            self._hb_timeout / 2.0, self._heartbeat_check)

        # Single startup log — no repeated banners
        self.get_logger().info(
            f'Motor Controller started | GPIO={_GPIO_AVAILABLE} | '
            f'ENA={self._ena} IN1={self._in1} IN2={self._in2} | '
            f'ENB={self._enb} IN3={self._in3} IN4={self._in4} | '
            f'timeout={self._hb_timeout}s')

    def _init_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        direction_pins = [self._in1, self._in2, self._in3, self._in4]
        GPIO.setup(direction_pins, GPIO.OUT)
        GPIO.output(direction_pins, GPIO.LOW)
        GPIO.setup(self._ena, GPIO.OUT)
        GPIO.setup(self._enb, GPIO.OUT)
        self._pwm_left  = GPIO.PWM(self._ena, self._pwm_freq)
        self._pwm_right = GPIO.PWM(self._enb, self._pwm_freq)
        self._pwm_left.start(0)
        self._pwm_right.start(0)

    def _cmd_vel_callback(self, msg: Twist):
        """Convert Twist -> differential wheel speeds -> GPIO PWM."""
        self._last_msg_time = self.get_clock().now()
        left  = msg.linear.x - msg.angular.z * self._track_half
        right = msg.linear.x + msg.angular.z * self._track_half
        self._drive(left, right)

    def _drive(self, left: float, right: float):
        left_dc  = self._speed_to_duty(left)
        right_dc = self._speed_to_duty(right)

        if left > 0:
            GPIO.output(self._in1, GPIO.HIGH)
            GPIO.output(self._in2, GPIO.LOW)
        elif left < 0:
            GPIO.output(self._in1, GPIO.LOW)
            GPIO.output(self._in2, GPIO.HIGH)
        else:
            GPIO.output(self._in1, GPIO.LOW)
            GPIO.output(self._in2, GPIO.LOW)
        self._pwm_left.ChangeDutyCycle(left_dc)

        if right > 0:
            GPIO.output(self._in3, GPIO.HIGH)
            GPIO.output(self._in4, GPIO.LOW)
        elif right < 0:
            GPIO.output(self._in3, GPIO.LOW)
            GPIO.output(self._in4, GPIO.HIGH)
        else:
            GPIO.output(self._in3, GPIO.LOW)
            GPIO.output(self._in4, GPIO.LOW)
        self._pwm_right.ChangeDutyCycle(right_dc)

    def _speed_to_duty(self, speed: float) -> float:
        clamped = max(-self._max_speed, min(self._max_speed, speed))
        return (abs(clamped) / self._max_speed) * 100.0

    def _heartbeat_check(self):
        elapsed = (self.get_clock().now() - self._last_msg_time).nanoseconds * 1e-9
        if elapsed > self._hb_timeout:
            # throttle_duration_sec avoids flooding the log on repeated timeouts
            self.get_logger().warn(
                f'No /cmd_vel for {elapsed:.1f}s — stopping motors',
                throttle_duration_sec=2.0)
            self._stop_all()

    def _stop_all(self):
        GPIO.output([self._in1, self._in2, self._in3, self._in4], GPIO.LOW)
        self._pwm_left.ChangeDutyCycle(0)
        self._pwm_right.ChangeDutyCycle(0)

    def destroy_node(self):
        self._stop_all()
        self._pwm_left.stop()
        self._pwm_right.stop()
        GPIO.cleanup()
        self.get_logger().info('Motor controller shut down cleanly.')
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MotorController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
