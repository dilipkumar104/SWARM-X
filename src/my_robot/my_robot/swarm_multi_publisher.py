#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
swarm_multi_publisher.py — Multi-Robot Publisher for Swarm Status

🌟 BONUS: This node simulates MULTIPLE robots publishing their status
to the /swarm_status topic. Each robot publishes a unique message like
"Robot 1 online", "Robot 2 online", etc.

How it works:
    - Uses a ROS2 parameter 'num_robots' (default: 3)
    - Each robot gets its own timer running at 1 Hz
    - All robots publish to the SAME topic: swarm_status (relative)
    - This shows how a real swarm system would work — many robots,
      one shared communication channel

Usage:
    # Run with default 2 robots
    ros2 run my_robot swarm_multi_publisher

    # Run with 5 robots (using ROS2 parameter override)
    ros2 run my_robot swarm_multi_publisher --ros-args -p num_robots:=5
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class SwarmMultiPublisher(Node):
    """
    Simulates multiple robots publishing status to /swarm_status.

    Parameters:
        num_robots (int): Number of robots to simulate (default: 3)
    """

    def __init__(self):
        super().__init__('swarm_multi_publisher')

        # ── Declare a parameter so users can change robot count ──────
        # You can override this at runtime with:
        #   --ros-args -p num_robots:=5
        self.declare_parameter('num_robots', 2)
        self.num_robots = self.get_parameter('num_robots').value

        # ── Create the publisher ─────────────────────────────────────
        self.publisher_ = self.create_publisher(String, 'swarm_status', 10)

        # ── Create one timer per robot ───────────────────────────────
        # Each robot gets a staggered one-shot that starts its repeating timer.
        # Stagger = (robot_id-1) / num_robots seconds apart.
        self.counters = {}
        self.timers = []          # repeating timers (kept alive)
        self._starter_timers = []  # one-shot starters (cancelled after use)

        for robot_id in range(1, self.num_robots + 1):
            self.counters[robot_id] = 0
            offset = (robot_id - 1) * (1.0 / self.num_robots)

            def _make_starter(rid=robot_id):
                def _start():
                    # Create the repeating 1 Hz timer for this robot
                    t = self.create_timer(
                        1.0,
                        lambda r=rid: self._publish_status(r),
                    )
                    self.timers.append(t)
                    # ── Cancel the one-shot starter to avoid memory leak ──
                    # Find and cancel ourselves by matching period ≈ offset
                    for s in self._starter_timers:
                        if not s.is_canceled():
                            s.cancel()
                            break
                return _start

            starter = self.create_timer(offset if offset > 0 else 0.001,
                                        _make_starter())
            self._starter_timers.append(starter)

        # ── Startup banner ───────────────────────────────────────────
        self.get_logger().info('━' * 55)
        self.get_logger().info('  🤖 SWARM-X Multi-Robot Publisher')
        self.get_logger().info(f'  Simulating {self.num_robots} robots on /swarm_status')
        self.get_logger().info('━' * 55)

    def _publish_status(self, robot_id: int):
        """Publish a status message for a specific robot."""

        msg = String()
        msg.data = f'Robot {robot_id} online'
        self.publisher_.publish(msg)

        self.counters[robot_id] += 1
        self.get_logger().info(
            f'[Robot {robot_id} | msg #{self.counters[robot_id]}] '
            f'Publishing: "{msg.data}"'
        )


def main(args=None):
    """Entry point for the swarm_multi_publisher node."""

    rclpy.init(args=args)
    node = SwarmMultiPublisher()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Keyboard interrupt — shutting down.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
