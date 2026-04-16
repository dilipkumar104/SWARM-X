#!/usr/bin/env python3
"""
thermal_sensor.py — SWARM-X MLX90614 Infrared Thermal Sensor Node

Reads object and ambient temperature from an MLX90614 I²C sensor
on the Raspberry Pi 4. Publishes to /robot1/heat_sensor and triggers
survivor alerts when object temperature exceeds threshold.

I²C wiring (MLX90614 → Raspberry Pi 4):
  VCC → 3.3V (the MLX90614 is a 3.3V device)
  GND → GND
  SDA → GPIO 2 (I²C1 SDA)
  SCL → GPIO 3 (I²C1 SCL)

Prerequisites:
  sudo raspi-config → Interface Options → I2C → Enable
  pip3 install smbus2

Optimised for Pi 4 (2GB):
  - 2 Hz polling (thermal changes are slow)
  - Minimal memory footprint
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Temperature
from std_msgs.msg import String

# ── Attempt smbus2 import ─────────────────────────────────────────────
try:
    import smbus2
    SMBUS_AVAILABLE = True
except ImportError:
    SMBUS_AVAILABLE = False

# ── MLX90614 I²C Constants ───────────────────────────────────────────
MLX90614_ADDR = 0x5A       # Default I²C address
MLX90614_TOBJ1 = 0x07      # Object temperature register 1
MLX90614_TAMB = 0x06       # Ambient temperature register
I2C_BUS = 1                # Raspberry Pi I²C bus 1

# ── Defaults ──────────────────────────────────────────────────────────
DEFAULT_POLL_RATE = 2.0    # Hz
DEFAULT_SURVIVOR_THRESHOLD = 30.0  # °C — human body heat detection


class ThermalSensorNode(Node):
    """MLX90614 infrared thermal sensor with survivor alert logic."""

    def __init__(self):
        super().__init__('thermal_sensor')

        # ── Parameters ────────────────────────────────────────────────
        self.declare_parameter('poll_rate_hz', DEFAULT_POLL_RATE)
        self.declare_parameter('survivor_threshold_c', DEFAULT_SURVIVOR_THRESHOLD)
        self.declare_parameter('i2c_bus', I2C_BUS)
        self.declare_parameter('i2c_address', MLX90614_ADDR)

        poll_rate = self.get_parameter('poll_rate_hz').value
        self.threshold = self.get_parameter('survivor_threshold_c').value
        bus_num = self.get_parameter('i2c_bus').value
        self.i2c_addr = self.get_parameter('i2c_address').value

        # ── I²C bus setup ─────────────────────────────────────────────
        self.bus = None
        if SMBUS_AVAILABLE:
            try:
                self.bus = smbus2.SMBus(bus_num)
                self.get_logger().info(
                    f'MLX90614 connected on I²C bus {bus_num}, '
                    f'address 0x{self.i2c_addr:02X}'
                )
            except Exception as e:
                self.get_logger().error(
                    f'Failed to open I²C bus {bus_num}: {e}'
                )
        else:
            self.get_logger().warn(
                'smbus2 not installed — thermal sensor in SIMULATION mode. '
                'Install with: pip3 install smbus2'
            )
            self._sim_temp = 22.0
            self._sim_direction = 1

        # ── Publishers ────────────────────────────────────────────────
        qos = QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.temp_pub = self.create_publisher(
            Temperature, 'heat_sensor', qos
        )
        self.alert_pub = self.create_publisher(
            String, 'survivor_alert', 10
        )

        # ── Timer ─────────────────────────────────────────────────────
        self.create_timer(1.0 / poll_rate, self._poll_sensor)

        self._alert_active = False
        self._reading_count = 0

        self.get_logger().info(
            '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            '  🌡️  SWARM-X Thermal Sensor Node READY\n'
            '  Publishing : heat_sensor (Temperature)\n'
            '  Alert topic: survivor_alert (String)\n'
            '  Threshold  : %.1f °C\n'
            '  Poll rate  : %.1f Hz\n'
            '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
            % (self.threshold, poll_rate)
        )

    def _read_temp_c(self, register: int) -> float:
        """
        Read temperature from MLX90614 register.
        Returns temperature in Celsius.
        """
        if self.bus is None:
            # Simulation mode
            self._sim_temp += 0.5 * self._sim_direction
            if self._sim_temp >= 40.0:
                self._sim_direction = -1
            elif self._sim_temp <= 18.0:
                self._sim_direction = 1
            return self._sim_temp

        try:
            # MLX90614 uses SMBus word read (2 bytes, little-endian)
            raw = self.bus.read_word_data(self.i2c_addr, register)
            # Convert: temp_C = raw * 0.02 - 273.15
            temp_c = raw * 0.02 - 273.15
            return temp_c
        except Exception as e:
            self.get_logger().error(f'I²C read error (reg 0x{register:02X}): {e}')
            return -999.0  # Error sentinel

    def _poll_sensor(self):
        """Timer callback: read temperatures, publish, check for survivors."""
        obj_temp = self._read_temp_c(MLX90614_TOBJ1)
        amb_temp = self._read_temp_c(MLX90614_TAMB)
        self._reading_count += 1

        if obj_temp < -270.0:
            # Read error — skip this cycle
            return

        # ── Publish Temperature message ───────────────────────────
        msg = Temperature()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'thermal_sensor_link'
        msg.temperature = obj_temp
        msg.variance = 0.5   # MLX90614 accuracy: ±0.5°C
        self.temp_pub.publish(msg)

        # ── Log every 4th reading (every 2 seconds at 2 Hz) ──────
        if self._reading_count % 4 == 0:
            self.get_logger().info(
                f'[{self._reading_count}] Object: {obj_temp:.1f}°C  '
                f'Ambient: {amb_temp:.1f}°C'
            )

        # ── Survivor alert logic ──────────────────────────────────
        if obj_temp >= self.threshold:
            if not self._alert_active:
                self.get_logger().warn(
                    f'🔥 HEAT SIGNATURE DETECTED — {obj_temp:.1f}°C '
                    f'(threshold: {self.threshold:.1f}°C) — '
                    f'Possible survivor!'
                )
                self._alert_active = True

            alert_msg = String()
            alert_msg.data = (
                f'SURVIVOR_ALERT: object_temp={obj_temp:.1f}C, '
                f'ambient={amb_temp:.1f}C, '
                f'timestamp={self.get_clock().now().to_msg().sec}'
            )
            self.alert_pub.publish(alert_msg)
        else:
            if self._alert_active:
                self.get_logger().info(
                    f'Heat signature cleared — {obj_temp:.1f}°C '
                    f'(below {self.threshold:.1f}°C)'
                )
                self._alert_active = False

    def destroy_node(self):
        if self.bus is not None:
            try:
                self.bus.close()
                self.get_logger().info('I²C bus closed.')
            except Exception:
                pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ThermalSensorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
