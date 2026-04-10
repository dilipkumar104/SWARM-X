#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
swarm_publisher.py — ROS2 Publisher Node for Swarm Status

This node publishes robot status messages to the /swarm_status topic
every 1 second. It uses the standard std_msgs/msg/String message type.

What this node does:
    1. Creates a ROS2 node named 'swarm_publisher'
    2. Creates a publisher on the /swarm_status topic
    3. Sets up a timer that fires every 1 second
    4. Each time the timer fires, it publishes "Robot 1 online"

Usage (after building & sourcing):
    ros2 run my_robot swarm_publisher
"""

# ── Imports ──────────────────────────────────────────────────────────
# rclpy          → The ROS2 Python client library (like the "engine" of ROS2)
# Node           → Base class that every ROS2 node inherits from
# String         → A standard message type that holds a single string value
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class SwarmPublisher(Node):
    """
    A ROS2 publisher node that broadcasts swarm robot status.

    Details:
        - Node name : swarm_publisher
        - Topic     : /swarm_status
        - Msg type  : std_msgs/msg/String
        - Frequency : 1 Hz (every 1 second)
    """

    def __init__(self):
        # ── Step 1: Initialize the parent Node class ─────────────────
        # 'swarm_publisher' is the name this node will have in the ROS2
        # graph. You can see it when you run: ros2 node list
        super().__init__('swarm_publisher')

        # ── Step 2: Create a publisher ───────────────────────────────
        # Arguments:
        #   String           → message type (std_msgs/msg/String)
        #   '/swarm_status'  → topic name (any node can subscribe to this)
        #   10               → QoS queue depth (buffers up to 10 messages)
        self.publisher_ = self.create_publisher(String, '/swarm_status', 10)

        # ── Step 3: Create a repeating timer ─────────────────────────
        # The timer calls self.timer_callback every 1.0 seconds.
        # This is how we publish at a steady rate.
        timer_period = 1.0  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)

        # ── Step 4: Initialize a message counter ─────────────────────
        # We use this to number each published message in the log.
        self.count = 0

        # ── Startup log ──────────────────────────────────────────────
        self.get_logger().info(
            '🟢 SwarmPublisher started — publishing to /swarm_status every 1s'
        )

    def timer_callback(self):
        """
        Called automatically every 1 second by the timer.
        Builds a String message and publishes it to /swarm_status.
        """

        # Build the message object
        msg = String()
        msg.data = 'Robot 1 online'

        # Publish the message to /swarm_status
        self.publisher_.publish(msg)

        # Increment counter and print a log line
        self.count += 1
        self.get_logger().info(
            f'[{self.count}] Publishing: "{msg.data}"'
        )


def main(args=None):
    """
    Entry point for the swarm_publisher node.

    This function is called by ROS2 when you run:
        ros2 run my_robot swarm_publisher

    Flow:
        1. rclpy.init()       → Start the ROS2 communication system
        2. SwarmPublisher()   → Create our publisher node
        3. rclpy.spin()       → Keep the node alive (blocks here, calling
                                 timer_callback every 1 second)
        4. Cleanup             → When Ctrl+C is pressed, clean up and exit
    """

    # Step 1: Initialize ROS2
    rclpy.init(args=args)

    # Step 2: Create the publisher node
    node = SwarmPublisher()

    try:
        # Step 3: Spin — this keeps the node running forever,
        # calling timer_callback each second until you press Ctrl+C
        rclpy.spin(node)
    except KeyboardInterrupt:
        # Graceful shutdown when you press Ctrl+C
        node.get_logger().info('Keyboard interrupt — shutting down.')
    finally:
        # Step 4: Cleanup — destroy the node and shut down ROS2
        node.destroy_node()
        rclpy.shutdown()


# This allows you to run the file directly with: python3 swarm_publisher.py
# (But normally you use: ros2 run my_robot swarm_publisher)
if __name__ == '__main__':
    main()
