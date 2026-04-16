#!/usr/bin/env python3
"""
ultrasonic_node.py — SWARM-X HC-SR04 Ultrasonic Sensor Node

Reads distance from an HC-SR04 ultrasonic sensor connected directly
to Raspberry Pi GPIO. Publishes sensor_msgs/Range to /robot1/ultrasonic_front.

EMERGENCY STOP: If measured distance < safety_threshold (default 20 cm),
publishes a zero-velocity Twist to cmd_vel to override motor commands.

Wiring (HC-SR04 → Raspberry Pi 4 GPIO BCM):
  VCC  → 5V
  GND  → Pi GND
  TRIG → GPIO 23 (3.3V output is enough to trigger HC-SR04)
  ECHO → GPIO 24 (⚠ USE VOLTAGE DIVIDER: 5V → 3.3V)

Voltage divider for ECHO:
  ECHO pin ──┤1kΩ├──┬── GPIO 24
                     │
                   ┤2kΩ├
                     │
                    GND

Optimised for Pi 4 (2GB):
  - 10 Hz polling via ROS timer
  - No threads, no locks
  - BEST_EFFORT QoS
"""

import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Range
from geometry_msgs.msg import Twist

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False

# ── Defaults ──────────────────────────────────────────────────────────
DEFAULT_TRIG_PIN = 23
DEFAULT_ECHO_PIN = 24
DEFAULT_POLL_RATE = 10.0          # Hz
SPEED_OF_SOUND_CM = 34300.0       # cm/s at ~20°C
MAX_RANGE_CM = 400.0              # HC-SR04 max range
MIN_RANGE_CM = 2.0                # HC-SR04 min range
ECHO_TIMEOUT_S = 0.03            # 30 ms ≈ ~5 m round-trip @ 343 m/s
DEFAULT_SAFETY_THRESHOLD = 0.20   # metres — emergency stop distance


class UltrasonicNode(Node):
    """HC-SR04 ultrasonic sensor with emergency stop logic."""

    def __init__(self):
        super().__init__('ultrasonic_node')

        # ── Parameters ────────────────────────────────────────────────
        self.declare_parameter('trig_pin', DEFAULT_TRIG_PIN)
        self.declare_parameter('echo_pin', DEFAULT_ECHO_PIN)
        self.declare_parameter('poll_rate_hz', DEFAULT_POLL_RATE)
        self.declare_parameter('safety_threshold_m', DEFAULT_SAFETY_THRESHOLD)
        self.declare_parameter('enable_emergency_stop', True)

        self.trig = self.get_parameter('trig_pin').value
        self.echo = self.get_parameter('echo_pin').value
        poll_rate = self.get_parameter('poll_rate_hz').value
        self.safety_threshold = self.get_parameter('safety_threshold_m').value
        self.estop_enabled = self.get_parameter('enable_emergency_stop').value

        # ── GPIO setup ────────────────────────────────────────────────
        if GPIO_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.trig, GPIO.OUT)
            GPIO.setup(self.echo, GPIO.IN)
            GPIO.output(self.trig, GPIO.LOW)
            # Let sensor settle
            time.sleep(0.1)
            self.get_logger().info(
                f'HC-SR04 ready — TRIG=GPIO{self.trig}, ECHO=GPIO{self.echo}'
            )
        else:
            self.get_logger().warn(
                'RPi.GPIO not available — ultrasonic in SIMULATION mode'
            )
            self._sim_distance = MIN_RANGE_CM
            self._sim_direction = 1  # sweep up

        # ── Publisher: Range ──────────────────────────────────────────
        qos = QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.range_pub = self.create_publisher(Range, 'ultrasonic_front', qos)

        # ── Publisher: Emergency stop (cmd_vel override) ──────────────
        if self.estop_enabled:
            self.cmd_vel_pub = self.create_publisher(Twist, 'cmd_vel', 10)

        # ── Timer ─────────────────────────────────────────────────────
        self.create_timer(1.0 / poll_rate, self._poll_sensor)

        self._estop_active = False
        self._reading_count = 0

        self.get_logger().info(
            '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            '  📡 SWARM-X Ultrasonic Node READY\n'
            '  Publishing : ultrasonic_front (Range)\n'
            '  Poll rate  : %.1f Hz\n'
            '  E-Stop     : %s (threshold: %.0f cm)\n'
            '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
            % (poll_rate,
               'ENABLED' if self.estop_enabled else 'DISABLED',
               self.safety_threshold * 100)
        )

    def _measure_distance_cm(self) -> float:
        """
        Trigger HC-SR04 and measure echo pulse width.
        Returns distance in cm, or -1.0 on timeout.
        """
        if not GPIO_AVAILABLE:
            # Simulation: sweep from 2 → 400 → 2
            self._sim_distance += 5.0 * self._sim_direction
            if self._sim_distance >= MAX_RANGE_CM:
                self._sim_direction = -1
            elif self._sim_distance <= MIN_RANGE_CM:
                self._sim_direction = 1
            return self._sim_distance

        # ── Send 10µs trigger pulse ───────────────────────────────
        GPIO.output(self.trig, GPIO.HIGH)
        time.sleep(0.00001)  # 10 µs
        GPIO.output(self.trig, GPIO.LOW)

        # ── Wait for echo HIGH (start of echo pulse) ─────────────
        timeout_start = time.monotonic()
        while GPIO.input(self.echo) == GPIO.LOW:
            pulse_start = time.monotonic()
            if pulse_start - timeout_start > ECHO_TIMEOUT_S:
                return -1.0  # Timeout — no object in range

        # ── Wait for echo LOW (end of echo pulse) ────────────────
        while GPIO.input(self.echo) == GPIO.HIGH:
            pulse_end = time.monotonic()
            if pulse_end - pulse_start > ECHO_TIMEOUT_S:
                return -1.0  # Timeout — object too far

        # ── Calculate distance ────────────────────────────────────
        pulse_duration = pulse_end - pulse_start
        distance = (pulse_duration * SPEED_OF_SOUND_CM) / 2.0
        return distance

    def _poll_sensor(self):
        """Timer callback: measure, publish, and check e-stop."""
        distance_cm = self._measure_distance_cm()
        self._reading_count += 1

        # ── Build Range message ───────────────────────────────────
        msg = Range()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'ultrasonic_front_link'
        msg.radiation_type = Range.ULTRASOUND
        msg.field_of_view = 0.26  # ~15° half-angle for HC-SR04
        msg.min_range = MIN_RANGE_CM / 100.0   # Convert to metres
        msg.max_range = MAX_RANGE_CM / 100.0

        if distance_cm < 0:
            # Timeout — no valid reading
            msg.range = msg.max_range
        else:
            msg.range = distance_cm / 100.0  # cm → m

        self.range_pub.publish(msg)

        # ── Log every 10th reading to avoid flooding ──────────────
        if self._reading_count % 10 == 0:
            if distance_cm < 0:
                self.get_logger().debug('No echo (out of range)')
            else:
                zone = '🔴 DANGER' if distance_cm < 20 else (
                    '🟡 WARNING' if distance_cm < 40 else '🟢 CLEAR')
                self.get_logger().info(
                    f'[{self._reading_count}] {zone}: {distance_cm:.1f} cm'
                )

        # ── Emergency stop logic ──────────────────────────────────
        if self.estop_enabled and distance_cm > 0:
            distance_m = distance_cm / 100.0
            if distance_m < self.safety_threshold:
                if not self._estop_active:
                    self.get_logger().warn(
                        f'⛔ EMERGENCY STOP — obstacle at {distance_cm:.0f} cm '
                        f'(threshold: {self.safety_threshold * 100:.0f} cm)'
                    )
                    self._estop_active = True
                # Publish zero velocity
                stop_msg = Twist()  # All fields default to 0.0
                self.cmd_vel_pub.publish(stop_msg)
            else:
                if self._estop_active:
                    self.get_logger().info(
                        f'✅ Path clear — obstacle cleared '
                        f'({distance_cm:.0f} cm > {self.safety_threshold * 100:.0f} cm)'
                    )
                    self._estop_active = False

    def destroy_node(self):
        if GPIO_AVAILABLE:
            GPIO.cleanup([self.trig, self.echo])
            self.get_logger().info('Ultrasonic GPIO cleaned up.')
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
