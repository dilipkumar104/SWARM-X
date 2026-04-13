#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
obstacle_avoider.py — ROS2 Obstacle Avoidance Node (Brain Node)

This is the central "Brain" node for the SWARM-X robot. It listens to
laser scan data and decides whether the robot should move forward or stop.

Communication Architecture:
    ┌──────────────────────────────────────────────────────────────┐
    │                   obstacle_avoider (Brain)                   │
    │                                                              │
    │   LISTENER (Subscriber)         TALKER (Publisher)           │
    │   ┌──────────────────┐         ┌──────────────────┐         │
    │   │ /scan            │         │ /cmd_vel          │         │
    │   │ LaserScan        │ ─────►  │ Twist             │         │
    │   │ (sensor data in) │  logic  │ (motor cmds out)  │         │
    │   └──────────────────┘         └──────────────────┘         │
    └──────────────────────────────────────────────────────────────┘

Logic:
    - Normal state   → Move forward at 0.22 m/s
    - Obstacle < 15cm → STOP all movement

Usage (after building & sourcing):
    ros2 run my_robot_controller obstacle_avoider
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan       # LISTENER message type
from geometry_msgs.msg import Twist         # TALKER message type


class ObstacleAvoider(Node):
    """
    Central "Brain" node for obstacle avoidance.

    Roles:
        LISTENER (Subscriber) — Subscribes to /scan (LaserScan)
        TALKER   (Publisher)  — Publishes to /cmd_vel (Twist)

    Parameters:
        obstacle_threshold (float): Distance in metres below which
                                     the robot stops. Default: 0.15 (15 cm)
        forward_speed      (float): Linear velocity when path is clear.
                                     Default: 0.22 m/s
    """

    def __init__(self):
        super().__init__('obstacle_avoider')

        # ── Declare parameters ────────────────────────────────────
        self.declare_parameter('obstacle_threshold', 0.15)  # 15 cm
        self.declare_parameter('forward_speed', 0.22)       # m/s

        self.threshold = self.get_parameter('obstacle_threshold').value
        self.forward_speed = self.get_parameter('forward_speed').value

        # ══════════════════════════════════════════════════════════
        #  LISTENER — Subscriber to /scan (sensor_msgs/msg/LaserScan)
        #
        #  This is where the robot RECEIVES sensor information.
        #  Every time the lidar publishes a new scan, ROS2 calls
        #  self._scan_callback with that data.
        # ══════════════════════════════════════════════════════════
        self.scan_sub = self.create_subscription(
            LaserScan,              # Message type
            'scan',                 # Topic name (relative for namespace support)
            self._scan_callback,    # Callback function
            10,                     # QoS queue depth
        )

        # ══════════════════════════════════════════════════════════
        #  TALKER — Publisher to /cmd_vel (geometry_msgs/msg/Twist)
        #
        #  This is where the robot SENDS movement commands.
        #  The _scan_callback decides the velocity and publishes
        #  a Twist message through this publisher.
        # ══════════════════════════════════════════════════════════
        self.cmd_pub = self.create_publisher(
            Twist,                  # Message type
            'cmd_vel',              # Topic name (relative for namespace support)
            10,                     # QoS queue depth
        )

        # ── State tracking ────────────────────────────────────────
        self._obstacle_detected = False
        self._scan_count = 0

        # ── Startup banner ────────────────────────────────────────
        self.get_logger().info('━' * 60)
        self.get_logger().info('  🧠 SWARM-X Obstacle Avoider (Brain Node)')
        self.get_logger().info(f'  Threshold : {self.threshold * 100:.0f} cm')
        self.get_logger().info(f'  Speed     : {self.forward_speed} m/s')
        self.get_logger().info('  Listening : scan  (LaserScan)')
        self.get_logger().info('  Publishing: cmd_vel (Twist)')
        self.get_logger().info('━' * 60)

    # ──────────────────────────────────────────────────────────────
    #  LISTENER CALLBACK — called every time a LaserScan arrives
    # ──────────────────────────────────────────────────────────────

    def _scan_callback(self, msg: LaserScan):
        """
        Process an incoming laser scan and decide: move or stop.

        Algorithm:
            1. Iterate through every range reading in the scan.
            2. If ANY reading is between range_min and the threshold
               (0.15 m), an obstacle is too close → STOP.
            3. Otherwise → move forward at forward_speed.
        """

        self._scan_count += 1
        obstacle_found = False
        closest_distance = float('inf')

        # ── Check every laser beam in the scan ────────────────────
        for i, distance in enumerate(msg.ranges):
            # Skip invalid readings (inf, NaN, below sensor minimum)
            if distance < msg.range_min or distance > msg.range_max:
                continue

            # Track closest valid reading
            if distance < closest_distance:
                closest_distance = distance

            # ── OBSTACLE CHECK ────────────────────────────────────
            # If any beam detects an object within the threshold,
            # trigger the stop condition
            if distance <= self.threshold:
                obstacle_found = True
                break  # No need to check further

        # ── Build the Twist command ───────────────────────────────
        cmd = Twist()

        if obstacle_found:
            # ══════ OBSTACLE DETECTED — STOP ══════════════════════
            cmd.linear.x = 0.0      # No forward movement
            cmd.angular.z = 0.0     # No rotation

            if not self._obstacle_detected:
                # Log only on state change (not every scan)
                self.get_logger().warn(
                    f'🔴 OBSTACLE at {closest_distance * 100:.1f} cm — STOPPING!'
                )
                self._obstacle_detected = True

        else:
            # ══════ PATH CLEAR — MOVE FORWARD ═════════════════════
            cmd.linear.x = self.forward_speed   # Move forward
            cmd.angular.z = 0.0                 # Go straight

            if self._obstacle_detected:
                # Log only on state change
                self.get_logger().info(
                    f'🟢 Path clear (nearest: {closest_distance * 100:.1f} cm) — moving forward'
                )
                self._obstacle_detected = False

        # ── TALKER — publish the movement command ─────────────────
        self.cmd_pub.publish(cmd)

        # Periodic status log (every 50 scans ≈ every 5 seconds at 10 Hz)
        if self._scan_count % 50 == 0:
            state = 'STOPPED' if self._obstacle_detected else 'MOVING'
            self.get_logger().info(
                f'[scan #{self._scan_count}] State: {state} | '
                f'Nearest: {closest_distance * 100:.1f} cm'
            )


def main(args=None):
    """
    Entry point for the obstacle_avoider node.

    Flow:
        1. rclpy.init()           → Initialize ROS2
        2. ObstacleAvoider()      → Create the brain node
        3. rclpy.spin()           → Keep alive, processing scan callbacks
        4. Cleanup                → Destroy node and shut down
    """
    rclpy.init(args=args)
    node = ObstacleAvoider()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        # Send a final STOP command before shutting down
        stop_cmd = Twist()
        node.cmd_pub.publish(stop_cmd)
        node.get_logger().info('Keyboard interrupt — robot stopped, shutting down.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
