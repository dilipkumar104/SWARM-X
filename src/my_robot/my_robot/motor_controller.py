#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
motor_controller.py — L298N Dual H-Bridge Motor Controller

Subscribes to  /cmd_vel  (geometry_msgs/Twist) and drives four DC motors
arranged in a differential-drive layout:

    LEFT  motors : EnA  ENA_PIN  |  In1  IN1_PIN  |  In2  IN2_PIN
    RIGHT motors : EnB  ENB_PIN  |  In3  IN3_PIN  |  In4  IN4_PIN

Wiring (BCM numbering — change the constants below to match your setup):

    Pi GPIO 12  →  L298N EnA   (PWM-capable — hardware PWM on GPIO 12)
    Pi GPIO 23  →  L298N In1
    Pi GPIO 24  →  L298N In2
    Pi GPIO 13  →  L298N EnB   (PWM-capable — hardware PWM on GPIO 13)
    Pi GPIO 27  →  L298N In3
    Pi GPIO 22  →  L298N In4
    Pi GND      →  L298N GND   ← CRITICAL: shared ground

Safety — Heartbeat:
    If no /cmd_vel message arrives within HEARTBEAT_TIMEOUT seconds the
    node immediately stops all motors (all pins → LOW).

Velocity mapping:
    linear.x  → forward / backward speed  (range  −1.0 … +1.0 m/s)
    angular.z → yaw rate                  (range  −1.0 … +1.0 rad/s)

    left_speed  = linear.x − angular.z * TRACK_WIDTH / 2
    right_speed = linear.x + angular.z * TRACK_WIDTH / 2

    Each side is then clamped to [−MAX_SPEED, +MAX_SPEED] and mapped to
    a PWM duty cycle in [0, 100].
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

# ── Try to import GPIO; fall back to a mock for testing on a non-Pi machine ──
try:
    import RPi.GPIO as GPIO
    _GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    _GPIO_AVAILABLE = False

    class _MockGPIO:  # noqa: D101 — internal stub
        BCM = OUT = IN = HIGH = LOW = 0
        BOARD = 0

        class PWM:  # noqa: D101
            def __init__(self, pin, freq):
                self._pin = pin

            def start(self, dc):
                pass

            def ChangeDutyCycle(self, dc):
                pass

            def stop(self):
                pass

        def setmode(self, _):
            pass

        def setwarnings(self, _):
            pass

        def setup(self, pins, mode):
            pass

        def output(self, pins, state):
            pass

        def cleanup(self):
            pass

    GPIO = _MockGPIO()


# ─────────────────────────────────────────────────────────────────────────────
# Wiring constants (BCM pin numbers) — edit these to match YOUR wiring
# ─────────────────────────────────────────────────────────────────────────────
ENA_PIN = 12   # Left  motors — Enable / PWM speed
IN1_PIN = 23   # Left  motors — Direction bit A
IN2_PIN = 24   # Left  motors — Direction bit B
ENB_PIN = 13   # Right motors — Enable / PWM speed
IN3_PIN = 27   # Right motors — Direction bit A
IN4_PIN = 22   # Right motors — Direction bit B

PWM_FREQUENCY   = 1000    # Hz — carrier frequency for PWM
MAX_SPEED       = 1.0     # m/s — clamp linear.x and result speeds to this
TRACK_WIDTH     = 0.20    # metres — distance between left and right wheels
HEARTBEAT_TIMEOUT = 0.5   # seconds — stop if no cmd_vel received in this time


class MotorController(Node):
    """ROS 2 node that drives four DC motors via an L298N H-bridge."""

    def __init__(self):
        super().__init__('motor_controller')

        # ── Declare + read parameters ──────────────────────────────────────
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

        self._ena = self.get_parameter('ena_pin').value
        self._in1 = self.get_parameter('in1_pin').value
        self._in2 = self.get_parameter('in2_pin').value
        self._enb = self.get_parameter('enb_pin').value
        self._in3 = self.get_parameter('in3_pin').value
        self._in4 = self.get_parameter('in4_pin').value
        self._pwm_freq   = self.get_parameter('pwm_frequency').value
        self._max_speed  = self.get_parameter('max_speed').value
        self._track_half = self.get_parameter('track_width').value / 2.0
        self._hb_timeout = self.get_parameter('heartbeat_timeout').value

        # ── Initialise GPIO ────────────────────────────────────────────────
        self._init_gpio()

        # ── ROS 2 subscriber ───────────────────────────────────────────────
        self._sub = self.create_subscription(
            Twist,
            '/cmd_vel',
            self._cmd_vel_callback,
            10,
        )

        # ── Heartbeat watchdog timer ───────────────────────────────────────
        self._last_msg_time = self.get_clock().now()
        self._watchdog = self.create_timer(
            self._hb_timeout / 2.0,   # check at 2× the timeout rate
            self._heartbeat_check,
        )

        self.get_logger().info('━' * 60)
        self.get_logger().info('  🚗 Motor Controller — Node Started')
        self.get_logger().info(f'  GPIO available : {_GPIO_AVAILABLE}')
        self.get_logger().info(f'  Pins  ENA={self._ena} IN1={self._in1}'
                               f' IN2={self._in2}')
        self.get_logger().info(f'        ENB={self._enb} IN3={self._in3}'
                               f' IN4={self._in4}')
        self.get_logger().info(f'  Heartbeat timeout : {self._hb_timeout} s')
        self.get_logger().info('━' * 60)

    # ── GPIO Setup ────────────────────────────────────────────────────────────
    def _init_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        direction_pins = [
            self._in1, self._in2,
            self._in3, self._in4,
        ]
        GPIO.setup(direction_pins, GPIO.OUT)
        GPIO.output(direction_pins, GPIO.LOW)

        GPIO.setup(self._ena, GPIO.OUT)
        GPIO.setup(self._enb, GPIO.OUT)

        self._pwm_left  = GPIO.PWM(self._ena, self._pwm_freq)
        self._pwm_right = GPIO.PWM(self._enb, self._pwm_freq)
        self._pwm_left.start(0)
        self._pwm_right.start(0)

    # ── /cmd_vel callback ─────────────────────────────────────────────────────
    def _cmd_vel_callback(self, msg: Twist):
        """Convert Twist → differential wheel speeds → GPIO PWM."""
        self._last_msg_time = self.get_clock().now()

        linear  = msg.linear.x
        angular = msg.angular.z

        left_speed  = linear - angular * self._track_half
        right_speed = linear + angular * self._track_half

        self._drive(left_speed, right_speed)

    # ── Drive helper ──────────────────────────────────────────────────────────
    def _drive(self, left: float, right: float):
        """
        Apply signed speeds (m/s) to the motors.

        Positive = forward, Negative = backward.
        Magnitude is clamped to [0, MAX_SPEED] and then scaled to [0, 100]%
        for the PWM duty cycle.
        """
        left_dc  = self._speed_to_duty(left)
        right_dc = self._speed_to_duty(right)

        # ── Left motors ──────────────────────────────────────────────────
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

        # ── Right motors ─────────────────────────────────────────────────
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
        """Map a signed speed in m/s to a PWM duty cycle in [0, 100]."""
        clamped = max(-self._max_speed, min(self._max_speed, speed))
        return (abs(clamped) / self._max_speed) * 100.0

    # ── Heartbeat watchdog ────────────────────────────────────────────────────
    def _heartbeat_check(self):
        """Stop the robot if no /cmd_vel was received recently."""
        elapsed = (
            self.get_clock().now() - self._last_msg_time
        ).nanoseconds * 1e-9

        if elapsed > self._hb_timeout:
            self.get_logger().warn(
                f'⚠  No /cmd_vel for {elapsed:.2f} s — STOPPING motors',
                throttle_duration_sec=2.0,
            )
            self._stop_all()

    def _stop_all(self):
        """Immediately set all pins LOW (safe stop)."""
        GPIO.output(
            [self._in1, self._in2, self._in3, self._in4],
            GPIO.LOW,
        )
        self._pwm_left.ChangeDutyCycle(0)
        self._pwm_right.ChangeDutyCycle(0)

    # ── Cleanup ───────────────────────────────────────────────────────────────
    def destroy_node(self):
        self._stop_all()
        self._pwm_left.stop()
        self._pwm_right.stop()
        GPIO.cleanup()
        self.get_logger().info('Motor controller shut down cleanly.')
        super().destroy_node()


# ─────────────────────────────────────────────────────────────────────────────
def main(args=None):
    """Entry point — called by ros2 run my_robot motor_controller."""
    rclpy.init(args=args)
    node = MotorController()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('KeyboardInterrupt — shutting down.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
