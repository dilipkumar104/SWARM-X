#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
chatter_publisher.py — ROS2 Publisher Node

This node publishes the string "Hello Swarm-X" to the /chatter topic
every 1 second using std_msgs/msg/String.

Usage (after building & sourcing):
    ros2 run my_robot chatter_publisher
"""

import rclpy                        # ROS2 Python client library
from rclpy.node import Node         # Base class for all ROS2 nodes
from std_msgs.msg import String     # Standard string message type


class ChatterPublisher(Node):
    """
    A minimal ROS2 publisher node.

    - Node name : chatter_publisher
    - Topic     : /chatter
    - Msg type  : std_msgs/msg/String
    - Frequency : 1 Hz (every 1 second)
    """

    def __init__(self):
        # Initialize the node with the name 'chatter_publisher'
        super().__init__('chatter_publisher')

        # Create a publisher
        #   - Message type : String
        #   - Topic name   : /chatter
        #   - QoS depth    : 10 (buffer up to 10 messages)
        self.publisher_ = self.create_publisher(String, 'chatter', 10)

        # Create a timer that fires every 1.0 second
        timer_period = 1.0  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)

        # Keep a message counter for logging
        self.count = 0

        # Startup log
        self.get_logger().info(
            'ChatterPublisher node started — publishing to /chatter every 1s'
        )

    def timer_callback(self):
        """Called every 1 second by the timer. Builds and publishes a message."""

        # Build the message
        msg = String()
        msg.data = 'Hello Swarm-X'

        # Publish it
        self.publisher_.publish(msg)

        # Increment counter and log
        self.count += 1
        self.get_logger().info(
            f'[{self.count}] Publishing: "{msg.data}"'
        )


def main(args=None):
    """
    Entry point for the chatter_publisher node.

    Flow:
        1. rclpy.init()      — Initialize the ROS2 communication layer
        2. Create the node   — Instantiate ChatterPublisher
        3. rclpy.spin()      — Keep the node alive, processing callbacks
        4. Cleanup            — Destroy node and shut down rclpy
    """

    # Step 1: Initialize ROS2
    rclpy.init(args=args)

    # Step 2: Create our publisher node
    node = ChatterPublisher()

    try:
        # Step 3: Spin (blocks here, handling timer callbacks)
        rclpy.spin(node)
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        node.get_logger().info('Keyboard interrupt — shutting down.')
    finally:
        # Step 4: Cleanup
        node.destroy_node()
        rclpy.shutdown()


# Allow running directly with: python3 chatter_publisher.py
if __name__ == '__main__':
    main()
