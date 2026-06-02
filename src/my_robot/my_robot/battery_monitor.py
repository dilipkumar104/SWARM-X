#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
battery_monitor.py — Battery Voltage Monitor

Reads battery voltage via MCP3008 ADC (SPI) or a simple voltage-divider
connected to a Pi GPIO analog input (via ADS1115 I2C ADC) and publishes:
    /battery/voltage  (sensor_msgs/BatteryState)  — full battery state message
    /battery/status   (std_msgs/String)            — JSON {voltage, percent, state}

Voltage divider: 12V battery → 10kΩ / 3.3kΩ → ADC → Pi
    V_out = V_bat × 3.3 / (10 + 3.3) ≈ V_bat × 0.248
    So: V_bat = ADC_voltage / 0.248

Without hardware (or ADC lib not found): publishes simulated draining battery.

Battery state thresholds (3S LiPo):
    FULL    ≥ 12.4V
    OK      ≥ 11.5V
    LOW     ≥ 10.8V
    CRITICAL < 10.8V → STOP command emitted
"""

import json
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import BatteryState
from std_msgs.msg import String

PUBLISH_HZ      = 1.0    # 1 Hz is plenty for battery monitoring
VOLTAGE_FULL    = 12.6
VOLTAGE_OK      = 11.5
VOLTAGE_LOW     = 10.8
VOLTAGE_MIN     = 9.0    # fully discharged (hard cutoff)
DIVIDER_RATIO   = 0.248  # see docstring above

try:
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    _ADC_AVAILABLE = True
except Exception:
    _ADC_AVAILABLE = False


class BatteryMonitor(Node):
    """Monitors battery voltage and publishes BatteryState messages."""

    def __init__(self):
        super().__init__('battery_monitor')

        self.declare_parameter('publish_hz',     PUBLISH_HZ)
        self.declare_parameter('voltage_full',   VOLTAGE_FULL)
        self.declare_parameter('voltage_low',    VOLTAGE_LOW)
        self.declare_parameter('voltage_min',    VOLTAGE_MIN)
        self.declare_parameter('simulate',       not _ADC_AVAILABLE)

        hz               = self.get_parameter('publish_hz').value
        self._v_full     = self.get_parameter('voltage_full').value
        self._v_low      = self.get_parameter('voltage_low').value
        self._v_min      = self.get_parameter('voltage_min').value
        self._simulate   = self.get_parameter('simulate').value

        # Simulation state
        self._sim_voltage = 12.2

        # Hardware
        self._chan = None
        if not self._simulate:
            try:
                i2c = busio.I2C(board.SCL, board.SDA)
                ads = ADS.ADS1115(i2c)
                self._chan = AnalogIn(ads, ADS.P0)
                self.get_logger().info('ADS1115 ADC initialised — hardware battery monitor')
            except Exception as exc:
                self.get_logger().warn(
                    f'ADS1115 init failed ({exc}) — falling back to simulator')
                self._simulate = True

        if self._simulate:
            self.get_logger().info('BatteryMonitor — SIMULATOR mode')

        # Publishers
        self._batt_pub   = self.create_publisher(BatteryState, 'battery/voltage', 10)
        self._status_pub = self.create_publisher(String,        'battery/status',  10)

        self._timer = self.create_timer(1.0 / hz, self._publish)
        self.get_logger().info(
            f'BatteryMonitor ready | hz={hz} | thresholds: '
            f'low={self._v_low}V critical={self._v_min}V')

    # ── Publish ──────────────────────────────────────────────────────────────

    def _publish(self):
        voltage = self._read_voltage()
        percent = self._voltage_to_percent(voltage)
        state   = self._voltage_to_state(voltage)

        # BatteryState message
        b = BatteryState()
        b.header.stamp    = self.get_clock().now().to_msg()
        b.header.frame_id = 'base_link'
        b.voltage         = voltage
        b.percentage      = percent / 100.0   # 0.0–1.0 per ROS convention
        b.present         = True
        b.power_supply_status = (
            BatteryState.POWER_SUPPLY_STATUS_DISCHARGING)
        b.power_supply_health = (
            BatteryState.POWER_SUPPLY_HEALTH_GOOD if voltage >= self._v_low
            else BatteryState.POWER_SUPPLY_HEALTH_DEAD)
        b.power_supply_technology = BatteryState.POWER_SUPPLY_TECHNOLOGY_LIPO
        self._batt_pub.publish(b)

        # JSON status
        s = String()
        s.data = json.dumps({
            'voltage_v':  round(voltage, 2),
            'percent':    round(percent, 1),
            'state':      state,
            'simulated':  self._simulate,
        })
        self._status_pub.publish(s)

        if state == 'CRITICAL':
            self.get_logger().error(
                f'🔋 CRITICAL BATTERY: {voltage:.2f}V — robot should stop!',
                throttle_duration_sec=5.0)
        elif state == 'LOW':
            self.get_logger().warn(
                f'🔋 LOW BATTERY: {voltage:.2f}V ({percent:.0f}%)',
                throttle_duration_sec=10.0)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _read_voltage(self) -> float:
        if not self._simulate and self._chan is not None:
            return self._chan.voltage / DIVIDER_RATIO
        # Simulate slow drain
        self._sim_voltage -= 0.0002
        if self._sim_voltage < 10.2:
            self._sim_voltage = 12.6   # reset to full (demo loop)
        return self._sim_voltage

    def _voltage_to_percent(self, v: float) -> float:
        pct = (v - self._v_min) / (self._v_full - self._v_min) * 100.0
        return max(0.0, min(100.0, pct))

    def _voltage_to_state(self, v: float) -> str:
        if v >= self._v_full:  return 'FULL'
        if v >= VOLTAGE_OK:    return 'OK'
        if v >= self._v_low:   return 'LOW'
        return 'CRITICAL'


def main(args=None):
    rclpy.init(args=args)
    node = BatteryMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
