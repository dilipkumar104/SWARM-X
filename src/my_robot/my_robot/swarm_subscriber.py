#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
swarm_subscriber.py — ROS2 Subscriber Node for Swarm Status

This node subscribes to the swarm_status topic and prints every
message it receives to the terminal. It uses std_msgs/msg/String.
Uses relative topic names so ROS2 namespaces (e.g. /robot1/) work automatically.

What this node does:
    1. Creates a ROS2 node named 'swarm_subscriber'
    2. Subscribes to the /swarm_status topic
    3. Every time a message arrives, it calls a "callback" function
    4. The callback prints the message content to the terminal

Usage (after building & sourcing):
    ros2 run my_robot swarm_subscriber
"""

# ── Imports ──────────────────────────────────────────────────────────
# rclpy   → The ROS2 Python client library
# Node    → Base class for all ROS2 nodes
# String  → Standard message type (same as what the publisher uses)
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class SwarmSubscriber(Node):
    """
    A ROS2 subscriber node that listens for swarm robot status messages.

    Details:
        - Node name : swarm_subscriber
        - Topic     : swarm_status  (relative — respects namespace)
        - Msg type  : std_msgs/msg/String
    """

    def __init__(self):
        # ── Step 1: Initialize the parent Node class ─────────────────
        # 'swarm_subscriber' is the name this node will have in the
        # ROS2 graph. You can see it with: ros2 node list
        super().__init__('swarm_subscriber')

        # ── Step 2: Create a subscription ────────────────────────────
        # Arguments:
        #   String                    → message type to expect
        #   '/swarm_status'           → topic name to listen on
        #   self.listener_callback    → function to call when a message arrives
        #   10                        → QoS queue depth
        #
        # KEY CONCEPT: Unlike a publisher that sends messages on a timer,
        # a subscriber waits passively. ROS2 calls listener_callback
        # automatically whenever a new message arrives on the topic.
        self.subscription = self.create_subscription(
            String,
            'swarm_status',
            self.listener_callback,
            10,
        )

        # Prevent "unused variable" warning (good practice)
        self.subscription  # noqa: B018

        # ── Counter for received messages ────────────────────────────
        self.count = 0

        # ── Startup log ──────────────────────────────────────────────
        self.get_logger().info(
            '👂 SwarmSubscriber started — listening on swarm_status'
        )

    def listener_callback(self, msg: String):
        """
        Called automatically every time a message arrives on /swarm_status.

        Parameters:
            msg (String): The incoming message. Access the text with msg.data
        """

        self.count += 1
        self.get_logger().info(
            f'[{self.count}] Received: "{msg.data}"'
        )


def main(args=None):
    """
    Entry point for the swarm_subscriber node.

    This function is called by ROS2 when you run:
        ros2 run my_robot swarm_subscriber

    Flow:
        1. rclpy.init()        → Start the ROS2 communication system
        2. SwarmSubscriber()   → Create our subscriber node
        3. rclpy.spin()        → Keep the node alive (blocks here,
                                  waiting for messages on /swarm_status)
        4. Cleanup              → When Ctrl+C is pressed, clean up and exit
    """

    # Step 1: Initialize ROS2
    rclpy.init(args=args)

    # Step 2: Create the subscriber node
    node = SwarmSubscriber()

    try:
        # Step 3: Spin — this keeps the node running forever,
        # calling listener_callback whenever a message arrives
        rclpy.spin(node)
    except KeyboardInterrupt:
        # Graceful shutdown when you press Ctrl+C
        node.get_logger().info('Keyboard interrupt — shutting down.')
    finally:
        # Step 4: Cleanup — destroy the node and shut down ROS2
        node.destroy_node()
        rclpy.shutdown()


# This allows you to run the file directly with: python3 swarm_subscriber.py
# (But normally you use: ros2 run my_robot swarm_subscriber)
if __name__ == '__main__':
    main()
