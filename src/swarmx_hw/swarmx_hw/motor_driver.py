#!/usr/bin/env python3
"""
motor_driver.py — SWARM-X L298N Motor Driver Node

Subscribes to /robot1/cmd_vel (geometry_msgs/Twist) and converts
velocity commands into PWM signals via RPi.GPIO for an L298N
dual H-bridge motor driver.

Differential drive model:
  left_speed  = linear.x - angular.z
  right_speed = linear.x + angular.z

Pinout (L298N → Raspberry Pi 4 GPIO BCM):
  IN1 = GPIO 17   (Left motors direction A)
  IN2 = GPIO 18   (Left motors direction B)
  IN3 = GPIO 27   (Right motors direction A)
  IN4 = GPIO 22   (Right motors direction B)
  ENA = GPIO 12   (Left motors PWM speed)
  ENB = GPIO 13   (Right motors PWM speed)
  GND = Pi GND    (Common ground)

Optimised for Raspberry Pi 4 (2GB RAM):
  - Single callback, no queues
  - BEST_EFFORT QoS to reduce DDS overhead
  - 100 Hz software PWM (safe for L298N)
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from geometry_msgs.msg import Twist

# ── Attempt GPIO import (fails gracefully on non-Pi systems) ──────────
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False


# ── Default Pin Assignments (BCM numbering) ───────────────────────────
DEFAULT_IN1 = 17   # Left motor direction A
DEFAULT_IN2 = 18   # Left motor direction B
DEFAULT_IN3 = 27   # Right motor direction A
DEFAULT_IN4 = 22   # Right motor direction B
DEFAULT_ENA = 12   # Left motor PWM (speed)
DEFAULT_ENB = 13   # Right motor PWM (speed)

# ── Motor Constants ───────────────────────────────────────────────────
PWM_FREQ = 100          # Hz — safe for L298N
MAX_PWM = 100           # Duty cycle cap (0–100)
MIN_PWM = 25            # Below this, motors stall — clamp to zero
CMD_VEL_TIMEOUT = 0.5   # Seconds — stop if no cmd_vel received


class MotorDriverNode(Node):
    """Converts /cmd_vel Twist messages into L298N GPIO PWM signals."""

    def __init__(self):
        super().__init__('motor_driver')

        # ── Declare parameters (overridable from launch file) ─────────
        self.declare_parameter('in1_pin', DEFAULT_IN1)
        self.declare_parameter('in2_pin', DEFAULT_IN2)
        self.declare_parameter('in3_pin', DEFAULT_IN3)
        self.declare_parameter('in4_pin', DEFAULT_IN4)
        self.declare_parameter('ena_pin', DEFAULT_ENA)
        self.declare_parameter('enb_pin', DEFAULT_ENB)
        self.declare_parameter('max_linear_speed', 1.0)
        self.declare_parameter('max_angular_speed', 1.0)
        self.declare_parameter('pwm_frequency', PWM_FREQ)

        self.in1 = self.get_parameter('in1_pin').value
        self.in2 = self.get_parameter('in2_pin').value
        self.in3 = self.get_parameter('in3_pin').value
        self.in4 = self.get_parameter('in4_pin').value
        self.ena = self.get_parameter('ena_pin').value
        self.enb = self.get_parameter('enb_pin').value
        self.max_linear = self.get_parameter('max_linear_speed').value
        self.max_angular = self.get_parameter('max_angular_speed').value
        pwm_freq = self.get_parameter('pwm_frequency').value

        # ── Setup GPIO ────────────────────────────────────────────────
        if GPIO_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            # Direction pins
            for pin in [self.in1, self.in2, self.in3, self.in4]:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)

            # PWM speed pins
            GPIO.setup(self.ena, GPIO.OUT)
            GPIO.setup(self.enb, GPIO.OUT)
            self.pwm_left = GPIO.PWM(self.ena, pwm_freq)
            self.pwm_right = GPIO.PWM(self.enb, pwm_freq)
            self.pwm_left.start(0)
            self.pwm_right.start(0)

            self.get_logger().info(
                f'GPIO initialised — IN1={self.in1} IN2={self.in2} '
                f'IN3={self.in3} IN4={self.in4} '
                f'ENA={self.ena} ENB={self.enb} @ {pwm_freq}Hz'
            )
        else:
            self.pwm_left = None
            self.pwm_right = None
            self.get_logger().warn(
                'RPi.GPIO not available — running in SIMULATION mode '
                '(no motor output)'
            )

        # ── Subscriber — use BEST_EFFORT to reduce DDS overhead ──────
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.subscription = self.create_subscription(
            Twist, 'cmd_vel', self._cmd_vel_cb, qos
        )

        # ── Watchdog timer — stop motors if cmd_vel goes silent ───────
        self._last_cmd_time = self.get_clock().now()
        self.create_timer(0.1, self._watchdog_cb)

        self.get_logger().info(
            '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            '  🏎️  SWARM-X Motor Driver Node READY\n'
            '  Listening on: cmd_vel (Twist)\n'
            '  Max linear : %.2f m/s\n'
            '  Max angular: %.2f rad/s\n'
            '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
            % (self.max_linear, self.max_angular)
        )

    # ── Twist → differential drive ────────────────────────────────────
    def _cmd_vel_cb(self, msg: Twist):
        """Convert cmd_vel to left/right motor PWM."""
        self._last_cmd_time = self.get_clock().now()

        # Normalise to [-1.0, 1.0]
        lin = max(-1.0, min(1.0, msg.linear.x / self.max_linear))
        ang = max(-1.0, min(1.0, msg.angular.z / self.max_angular))

        # Differential drive mixing
        left = lin - ang
        right = lin + ang

        # Clamp to [-1.0, 1.0]
        left = max(-1.0, min(1.0, left))
        right = max(-1.0, min(1.0, right))

        self._set_motors(left, right)

    def _set_motors(self, left: float, right: float):
        """
        Set motor directions and PWM duty cycle.
        left/right: -1.0 (full reverse) to +1.0 (full forward)
        """
        if not GPIO_AVAILABLE:
            self.get_logger().debug(
                f'[SIM] L={left:+.2f} R={right:+.2f}'
            )
            return

        # ── Left motor ────────────────────────────────────────────
        duty_l = abs(left) * MAX_PWM
        if duty_l < MIN_PWM:
            duty_l = 0.0
        if left > 0:
            GPIO.output(self.in1, GPIO.HIGH)
            GPIO.output(self.in2, GPIO.LOW)
        elif left < 0:
            GPIO.output(self.in1, GPIO.LOW)
            GPIO.output(self.in2, GPIO.HIGH)
        else:
            GPIO.output(self.in1, GPIO.LOW)
            GPIO.output(self.in2, GPIO.LOW)
        self.pwm_left.ChangeDutyCycle(duty_l)

        # ── Right motor ───────────────────────────────────────────
        duty_r = abs(right) * MAX_PWM
        if duty_r < MIN_PWM:
            duty_r = 0.0
        if right > 0:
            GPIO.output(self.in3, GPIO.HIGH)
            GPIO.output(self.in4, GPIO.LOW)
        elif right < 0:
            GPIO.output(self.in3, GPIO.LOW)
            GPIO.output(self.in4, GPIO.HIGH)
        else:
            GPIO.output(self.in3, GPIO.LOW)
            GPIO.output(self.in4, GPIO.LOW)
        self.pwm_right.ChangeDutyCycle(duty_r)

    # ── Watchdog — stop if no commands received ───────────────────────
    def _watchdog_cb(self):
        elapsed = (self.get_clock().now() - self._last_cmd_time).nanoseconds / 1e9
        if elapsed > CMD_VEL_TIMEOUT:
            self._set_motors(0.0, 0.0)

    # ── Clean shutdown ────────────────────────────────────────────────
    def destroy_node(self):
        self.get_logger().info('Shutting down — stopping motors...')
        if GPIO_AVAILABLE:
            self._set_motors(0.0, 0.0)
            self.pwm_left.stop()
            self.pwm_right.stop()
            GPIO.cleanup()
            self.get_logger().info('GPIO cleaned up.')
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MotorDriverNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
