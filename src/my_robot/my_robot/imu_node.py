#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
imu_node.py — MPU6050 IMU Node

Reads roll, pitch, yaw from an MPU6050 via I2C and publishes:
    /imu/data   (sensor_msgs/Imu)    — full quaternion + angular velocity + linear accel
    /imu/euler  (std_msgs/String)    — JSON {roll, pitch, yaw} in degrees (easy to read)

Hardware wiring (MPU6050 → Raspberry Pi):
    VCC  → 3.3V (pin 1)
    GND  → GND  (pin 6)
    SDA  → GPIO 2 (pin 3)  — shared I2C bus with AMG8833 (both are 0x68 / 0x69)
    SCL  → GPIO 3 (pin 5)
    AD0  → GND  → I2C address 0x68  (if AMG8833 also on bus, set AD0 HIGH → 0x69)

Without hardware: runs in simulator mode (sinusoidal tilt).
"""

import json
import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from std_msgs.msg import String
from geometry_msgs.msg import Vector3

PUBLISH_HZ = 20.0   # Hz — IMU should run fast for smooth motion data

try:
    import smbus2
    _I2C_AVAILABLE = True
except ImportError:
    _I2C_AVAILABLE = False

# MPU6050 register map
MPU6050_ADDR    = 0x68
PWR_MGMT_1      = 0x6B
ACCEL_XOUT_H    = 0x3B
GYRO_XOUT_H     = 0x43
ACCEL_SCALE     = 16384.0  # ±2g
GYRO_SCALE      = 131.0    # ±250°/s


class ImuNode(Node):
    """MPU6050 IMU node with complementary filter for roll/pitch/yaw."""

    def __init__(self):
        super().__init__('imu_node')

        self.declare_parameter('publish_hz',  PUBLISH_HZ)
        self.declare_parameter('i2c_address', MPU6050_ADDR)
        self.declare_parameter('i2c_bus',     1)
        self.declare_parameter('simulate',    not _I2C_AVAILABLE)
        self.declare_parameter('alpha',       0.98)    # complementary filter weight

        hz           = self.get_parameter('publish_hz').value
        addr         = self.get_parameter('i2c_address').value
        bus_num      = self.get_parameter('i2c_bus').value
        self._sim    = self.get_parameter('simulate').value
        self._alpha  = self.get_parameter('alpha').value

        # Complementary filter state
        self._roll  = 0.0
        self._pitch = 0.0
        self._yaw   = 0.0
        self._sim_t = 0.0

        # Hardware
        self._bus = None
        if not self._sim:
            try:
                self._bus = smbus2.SMBus(bus_num)
                self._bus.write_byte_data(addr, PWR_MGMT_1, 0)  # wake up
                self._addr = addr
                self.get_logger().info(
                    f'MPU6050 initialised at I2C {bus_num}:0x{addr:02X}')
            except Exception as exc:
                self.get_logger().warn(
                    f'MPU6050 init failed ({exc}) — falling back to simulator')
                self._sim = True

        if self._sim:
            self.get_logger().info('ImuNode — SIMULATOR mode (no hardware needed)')

        # Publishers
        self._imu_pub   = self.create_publisher(Imu,    'imu/data',  10)
        self._euler_pub = self.create_publisher(String, 'imu/euler', 10)

        self._timer = self.create_timer(1.0 / hz, self._publish)
        self.get_logger().info(
            f'ImuNode ready | hz={hz} | topics=imu/data, imu/euler')

    # ── Publish ──────────────────────────────────────────────────────────────

    def _publish(self):
        roll, pitch, yaw, ax, ay, az, gx, gy, gz = self._read()

        now = self.get_clock().now().to_msg()

        # Euler-angle JSON (easy for dashboard)
        e_msg = String()
        e_msg.data = json.dumps({
            'roll_deg':  round(roll,  2),
            'pitch_deg': round(pitch, 2),
            'yaw_deg':   round(yaw,   2),
            'simulated': self._sim,
        })
        self._euler_pub.publish(e_msg)

        # Full IMU message
        imu = Imu()
        imu.header.stamp    = now
        imu.header.frame_id = 'imu_frame'

        # Convert Euler → quaternion (yaw=0 assumption; full AHRS not needed here)
        cr, sr = math.cos(math.radians(roll)  / 2), math.sin(math.radians(roll)  / 2)
        cp, sp = math.cos(math.radians(pitch) / 2), math.sin(math.radians(pitch) / 2)
        cy, sy = math.cos(math.radians(yaw)   / 2), math.sin(math.radians(yaw)   / 2)
        imu.orientation.w = cr * cp * cy + sr * sp * sy
        imu.orientation.x = sr * cp * cy - cr * sp * sy
        imu.orientation.y = cr * sp * cy + sr * cp * sy
        imu.orientation.z = cr * cp * sy - sr * sp * cy
        imu.orientation_covariance[0]  = 0.01
        imu.orientation_covariance[4]  = 0.01
        imu.orientation_covariance[8]  = 0.01

        imu.angular_velocity.x = math.radians(gx)
        imu.angular_velocity.y = math.radians(gy)
        imu.angular_velocity.z = math.radians(gz)
        imu.angular_velocity_covariance[0] = 0.001
        imu.angular_velocity_covariance[4] = 0.001
        imu.angular_velocity_covariance[8] = 0.001

        imu.linear_acceleration.x = ax * 9.81
        imu.linear_acceleration.y = ay * 9.81
        imu.linear_acceleration.z = az * 9.81
        imu.linear_acceleration_covariance[0] = 0.01
        imu.linear_acceleration_covariance[4] = 0.01
        imu.linear_acceleration_covariance[8] = 0.01

        self._imu_pub.publish(imu)

    # ── Sensor read ──────────────────────────────────────────────────────────

    def _read(self):
        if self._sim or self._bus is None:
            return self._simulate()
        return self._read_hardware()

    def _read_hardware(self):
        def raw_word(reg):
            high = self._bus.read_byte_data(self._addr, reg)
            low  = self._bus.read_byte_data(self._addr, reg + 1)
            val  = (high << 8) | low
            return val - 65536 if val >= 0x8000 else val

        ax = raw_word(ACCEL_XOUT_H)     / ACCEL_SCALE
        ay = raw_word(ACCEL_XOUT_H + 2) / ACCEL_SCALE
        az = raw_word(ACCEL_XOUT_H + 4) / ACCEL_SCALE
        gx = raw_word(GYRO_XOUT_H)      / GYRO_SCALE
        gy = raw_word(GYRO_XOUT_H + 2)  / GYRO_SCALE
        gz = raw_word(GYRO_XOUT_H + 4)  / GYRO_SCALE

        # Complementary filter
        dt = 1.0 / self.get_parameter('publish_hz').value
        accel_roll  = math.degrees(math.atan2(ay, az))
        accel_pitch = math.degrees(math.atan2(-ax, math.sqrt(ay**2 + az**2)))
        self._roll  = self._alpha * (self._roll  + gx * dt) + (1 - self._alpha) * accel_roll
        self._pitch = self._alpha * (self._pitch + gy * dt) + (1 - self._alpha) * accel_pitch
        self._yaw  += gz * dt
        return self._roll, self._pitch, self._yaw, ax, ay, az, gx, gy, gz

    def _simulate(self):
        import random
        self._sim_t += 0.05
        roll  = 3.0 * math.sin(self._sim_t * 0.7) + random.uniform(-0.2, 0.2)
        pitch = 2.0 * math.cos(self._sim_t * 0.5) + random.uniform(-0.2, 0.2)
        yaw   = self._yaw + 0.05 * math.sin(self._sim_t * 0.1)
        self._yaw = yaw
        ax = math.sin(math.radians(pitch))
        ay = -math.sin(math.radians(roll))
        az = math.cos(math.radians(roll)) * math.cos(math.radians(pitch))
        gx = gy = gz = random.uniform(-0.5, 0.5)
        return roll, pitch, yaw, ax, ay, az, gx, gy, gz


def main(args=None):
    rclpy.init(args=args)
    node = ImuNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
