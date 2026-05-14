#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
ir_sensor_node.py — MLX90614 IR Thermal Sensor Node

Reads ambient and object temperature from an MLX90614 sensor over I2C
and publishes them on:

    /ir/temperature   (sensor_msgs/Temperature) — object temperature [°C]
    /ir/ambient       (sensor_msgs/Temperature) — ambient temperature [°C]

Wiring (Raspberry Pi):
    MLX90614 VCC  -> 3.3 V  (Pin 1)
    MLX90614 GND  -> GND    (Pin 6)
    MLX90614 SDA  -> GPIO 2 (Pin 3, I2C1 SDA)
    MLX90614 SCL  -> GPIO 3 (Pin 5, I2C1 SCL)

    NOTE: Enable I2C on the Pi with:  sudo raspi-config -> Interface Options -> I2C -> Enable
    Install library:  pip install smbus2 adafruit-circuitpython-mlx90614

Parameters (override at launch time):
    i2c_bus          (int,   default=1)      — I2C bus number
    i2c_address      (int,   default=0x5A)   — MLX90614 default address
    publish_hz       (float, default=5.0)    — publish rate [Hz]
    frame_id         (str,   default='ir_link') — sensor frame
    warn_temp_c      (float, default=40.0)   — log warning above this object temp
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Temperature

# ── Try to import the MLX90614 driver; fall back to a simulator on non-Pi ──
try:
    import board
    import busio
    import adafruit_mlx90614
    _HW_AVAILABLE = True
except (ImportError, NotImplementedError, ValueError):
    _HW_AVAILABLE = False


class _MockMLX:
    """Simulates the MLX90614 for development on non-Pi machines."""
    ambient_temperature = 25.0
    object_temperature  = 27.0


class IRSensorNode(Node):
    """
    ROS 2 node for the MLX90614 IR thermal sensor.

    Publishes object and ambient temperatures at a configurable rate.
    Logs a warning when the object temperature exceeds warn_temp_c.
    """

    def __init__(self):
        super().__init__('ir_sensor_node')

        # ── Parameters ────────────────────────────────────────────────────────
        self.declare_parameter('i2c_bus',     1)
        self.declare_parameter('i2c_address', 0x5A)
        self.declare_parameter('publish_hz',  5.0)
        self.declare_parameter('frame_id',    'ir_link')
        self.declare_parameter('warn_temp_c', 40.0)

        self._frame_id   = self.get_parameter('frame_id').value
        self._warn_temp  = self.get_parameter('warn_temp_c').value
        hz               = self.get_parameter('publish_hz').value

        # ── Initialise I2C sensor ─────────────────────────────────────────────
        self._sensor = self._init_sensor()

        # ── Publishers ───────────────────────────────────────────────────────
        self._pub_obj = self.create_publisher(Temperature, '/ir/temperature', 10)
        self._pub_amb = self.create_publisher(Temperature, '/ir/ambient',     10)

        # ── Timer — poll at publish_hz (default 5 Hz to keep Pi load low) ───
        self.create_timer(1.0 / hz, self._publish_temperatures)

        self.get_logger().info(
            f'IR Sensor (MLX90614) started | hw={_HW_AVAILABLE} | '
            f'{hz:.1f} Hz | frame={self._frame_id} | warn>{self._warn_temp}C')

    # ── Sensor initialisation ─────────────────────────────────────────────────

    def _init_sensor(self):
        if not _HW_AVAILABLE:
            self.get_logger().warn(
                'MLX90614 hardware not found — using simulated values')
            return _MockMLX()

        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            addr = self.get_parameter('i2c_address').value
            sensor = adafruit_mlx90614.MLX90614(i2c, address=addr)
            self.get_logger().info(
                f'MLX90614 connected on I2C bus '
                f'{self.get_parameter("i2c_bus").value} '
                f'addr=0x{addr:02X}')
            return sensor
        except Exception as e:
            self.get_logger().error(
                f'Failed to init MLX90614: {e} — falling back to simulator')
            return _MockMLX()

    # ── Timer callback ────────────────────────────────────────────────────────

    def _publish_temperatures(self):
        """Read sensor and publish both temperatures. Called at publish_hz."""
        try:
            obj_temp = float(self._sensor.object_temperature)
            amb_temp = float(self._sensor.ambient_temperature)
        except Exception as e:
            self.get_logger().error(
                f'MLX90614 read error: {e}', throttle_duration_sec=5.0)
            return

        stamp = self.get_clock().now().to_msg()

        # Object temperature message
        obj_msg = Temperature()
        obj_msg.header.stamp    = stamp
        obj_msg.header.frame_id = self._frame_id
        obj_msg.temperature     = obj_temp
        obj_msg.variance        = 0.0       # variance unknown
        self._pub_obj.publish(obj_msg)

        # Ambient temperature message
        amb_msg = Temperature()
        amb_msg.header.stamp    = stamp
        amb_msg.header.frame_id = self._frame_id
        amb_msg.temperature     = amb_temp
        amb_msg.variance        = 0.0
        self._pub_amb.publish(amb_msg)

        # Only log warnings (not every reading) to avoid stdout flooding
        if obj_temp >= self._warn_temp:
            self.get_logger().warn(
                f'IR thermal alert: object={obj_temp:.1f}C ambient={amb_temp:.1f}C',
                throttle_duration_sec=2.0)


def main(args=None):
    rclpy.init(args=args)
    node = IRSensorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
