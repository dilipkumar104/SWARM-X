#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
system_monitor.py — CPU, RAM & Temperature Monitor

Publishes Raspberry Pi system health metrics for the dashboard:
    system/status  (std_msgs/String)  — JSON with cpu%, ram%, cpu_temp_c

This is a pure Python node (no hardware) — works on both Pi and laptop.
"""

import json
import math
import random
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

PUBLISH_HZ = 2.0   # 2 Hz — system stats don't need to be faster

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


class SystemMonitor(Node):
    """Publishes CPU load, RAM usage, and Pi CPU temperature."""

    def __init__(self):
        super().__init__('system_monitor')

        self.declare_parameter('publish_hz', PUBLISH_HZ)
        hz = self.get_parameter('publish_hz').value

        if not _PSUTIL:
            self.get_logger().warn(
                'psutil not installed — using simulated values. '
                'Install with: pip install psutil')

        self._pub   = self.create_publisher(String, 'system/status', 10)
        self._timer = self.create_timer(1.0 / hz, self._publish)
        self._sim_t = 0.0

        self.get_logger().info(
            f'SystemMonitor ready | hz={hz} | psutil={_PSUTIL}')

    def _publish(self):
        data = self._read()
        msg  = String()
        msg.data = json.dumps(data)
        self._pub.publish(msg)

    def _read(self) -> dict:
        if _PSUTIL:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            temp = self._get_pi_temp()
            return {
                'cpu_percent':  round(cpu,  1),
                'ram_percent':  round(ram,  1),
                'cpu_temp_c':   round(temp, 1),
                'simulated':    False,
            }
        # Fallback simulator
        self._sim_t += 0.1
        cpu = 30 + 20 * abs(math.sin(self._sim_t * 0.3)) + random.uniform(-3, 3)
        ram = 45 + 10 * math.sin(self._sim_t * 0.1) + random.uniform(-2, 2)
        temp = 52 + 8 * abs(math.sin(self._sim_t * 0.2)) + random.uniform(-1, 1)
        return {
            'cpu_percent': round(max(5, min(95, cpu)),  1),
            'ram_percent': round(max(20, min(90, ram)), 1),
            'cpu_temp_c':  round(max(40, min(85, temp)), 1),
            'simulated':   True,
        }

    def _get_pi_temp(self) -> float:
        """Read Raspberry Pi CPU temperature from sysfs (returns 0 on non-Pi)."""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                return int(f.read().strip()) / 1000.0
        except Exception:
            try:
                temps = psutil.sensors_temperatures()
                for key in ('cpu_thermal', 'coretemp', 'acpitz'):
                    if key in temps and temps[key]:
                        return temps[key][0].current
            except Exception:
                pass
        return 0.0


def main(args=None):
    rclpy.init(args=args)
    node = SystemMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
