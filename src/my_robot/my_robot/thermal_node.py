#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
thermal_node.py — AMG8833 8×8 Thermal Camera

Reads the AMG8833 via I2C and publishes:
    /thermal/temperature  (sensor_msgs/Temperature)  — peak pixel °C
    /thermal/status       (std_msgs/String)           — JSON: all 64 pixels + peak + target_detected

Target detection: any pixel ≥ HUMAN_TEMP_C (default 34°C) flags a thermal target.

Hardware:
    AMG8833 → Raspberry Pi I2C
    VCC  → 3.3V (pin 1)
    GND  → GND  (pin 6)
    SDA  → GPIO 2 (pin 3)
    SCL  → GPIO 3 (pin 5)
    INT  → not connected (polling mode)

Without hardware: runs in simulator mode (triangle-wave sweep).
"""

import json
import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Temperature
from std_msgs.msg import String

HUMAN_TEMP_C  = 34.0   # °C threshold to flag a living/thermal target
AMBIENT_C     = 27.0   # fallback ambient in simulator mode
PUBLISH_HZ    = 5.0    # AMG8833 max frame rate is 10 Hz; 5 Hz is safe

try:
    import busio
    import board
    import adafruit_amg88xx
    _HW_AVAILABLE = True
except Exception:
    _HW_AVAILABLE = False


class ThermalNode(Node):
    """Reads AMG8833 and publishes thermal data to /thermal/*."""

    def __init__(self):
        super().__init__('thermal_node')

        self.declare_parameter('publish_hz',        PUBLISH_HZ)
        self.declare_parameter('human_temp_c',      HUMAN_TEMP_C)
        self.declare_parameter('simulate',          not _HW_AVAILABLE)

        hz              = self.get_parameter('publish_hz').value
        self._threshold = self.get_parameter('human_temp_c').value
        self._simulate  = self.get_parameter('simulate').value

        # Publishers
        self._temp_pub   = self.create_publisher(Temperature, 'thermal/temperature', 10)
        self._status_pub = self.create_publisher(String,      'thermal/status',      10)

        # Hardware init
        self._sensor = None
        if not self._simulate:
            try:
                i2c = busio.I2C(board.SCL, board.SDA)
                self._sensor = adafruit_amg88xx.AMG88XX(i2c)
                self.get_logger().info('AMG8833 initialised — hardware mode')
            except Exception as exc:
                self.get_logger().warn(
                    f'AMG8833 init failed ({exc}) — falling back to simulator')
                self._simulate = True

        if self._simulate:
            self.get_logger().info(
                'ThermalNode — SIMULATOR mode (no hardware needed)')

        self._sim_t   = 0.0          # simulation phase
        self._timer   = self.create_timer(1.0 / hz, self._publish)

        self.get_logger().info(
            f'ThermalNode ready | topic=thermal/temperature | hz={hz} | '
            f'threshold={self._threshold}°C')

    # ── Publish ──────────────────────────────────────────────────────────────

    def _publish(self):
        pixels = self._read_pixels()
        peak   = max(max(row) for row in pixels)
        flat   = [p for row in pixels for p in row]

        target = peak >= self._threshold

        # sensor_msgs/Temperature for the peak reading
        t_msg = Temperature()
        t_msg.header.stamp    = self.get_clock().now().to_msg()
        t_msg.header.frame_id = 'thermal_frame'
        t_msg.temperature     = peak
        t_msg.variance        = 0.0
        self._temp_pub.publish(t_msg)

        # JSON status with full pixel grid
        s_msg = String()
        s_msg.data = json.dumps({
            'peak_temp_c':       round(peak, 1),
            'target_detected':   target,
            'threshold_c':       self._threshold,
            'pixels':            [round(v, 1) for v in flat],
            'simulated':         self._simulate,
        })
        self._status_pub.publish(s_msg)

        if target:
            self.get_logger().info(
                f'🔥 Thermal target detected — peak {peak:.1f}°C ≥ {self._threshold}°C',
                throttle_duration_sec=2.0)

    # ── Sensor read ──────────────────────────────────────────────────────────

    def _read_pixels(self) -> list:
        if not self._simulate and self._sensor is not None:
            return self._sensor.pixels          # list[8][8] of floats
        return self._simulate_pixels()

    def _simulate_pixels(self) -> list:
        """Generate a realistic 8×8 thermal scene with a warm hot-spot."""
        import random
        self._sim_t += 0.05
        # Background: ~27°C with ±1 noise
        grid = [[AMBIENT_C + random.uniform(-1, 1) for _ in range(8)]
                for _ in range(8)]
        # Simulated warm body: oscillates between ambient and 39°C
        hot = AMBIENT_C + (39 - AMBIENT_C) * (0.5 + 0.5 * math.sin(self._sim_t))
        grid[3][3] = hot
        grid[3][4] = hot - random.uniform(0, 1.5)
        grid[4][3] = hot - random.uniform(0, 1.5)
        grid[4][4] = hot - random.uniform(0, 2.0)
        return grid


def main(args=None):
    rclpy.init(args=args)
    node = ThermalNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
