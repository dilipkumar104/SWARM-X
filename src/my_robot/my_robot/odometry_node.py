#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
odometry_node.py — Dead-Reckoning Wheel Odometry

Integrates /cmd_vel (Twist) over time to produce a position estimate.
Broadcasts TF: odom -> base_link
Publishes:    /odom (nav_msgs/Odometry)
"""

import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster


class OdometryNode(Node):
    """Dead-reckoning odometry from /cmd_vel integration."""

    def __init__(self):
        super().__init__('odometry_node')

        self.declare_parameter('publish_hz', 20.0)
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_link')

        self._odom_frame = self.get_parameter('odom_frame').value
        self._base_frame = self.get_parameter('base_frame').value
        hz = self.get_parameter('publish_hz').value

        self._x = 0.0
        self._y = 0.0
        self._theta = 0.0
        self._vx = 0.0
        self._wz = 0.0
        self._last_time = self.get_clock().now()

        self._tf_broadcaster = TransformBroadcaster(self)
        self._odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self._cmd_sub = self.create_subscription(
            Twist, '/cmd_vel', self._cmd_vel_callback, 10)
        self._timer = self.create_timer(1.0 / hz, self._update)

        self.get_logger().info('━' * 60)
        self.get_logger().info('  🧭 Odometry Node — Dead-Reckoning Started')
        self.get_logger().info(
            f'  Frames: {self._odom_frame} → {self._base_frame}  |  {hz} Hz')
        self.get_logger().info('━' * 60)

    def _cmd_vel_callback(self, msg: Twist):
        self._vx = msg.linear.x
        self._wz = msg.angular.z

    def _update(self):
        now = self.get_clock().now()
        dt = (now - self._last_time).nanoseconds * 1e-9
        self._last_time = now
        if dt <= 0.0:
            return

        self._x += self._vx * math.cos(self._theta) * dt
        self._y += self._vx * math.sin(self._theta) * dt
        self._theta += self._wz * dt
        self._theta = math.atan2(math.sin(self._theta), math.cos(self._theta))

        qz = math.sin(self._theta / 2.0)
        qw = math.cos(self._theta / 2.0)
        stamp = now.to_msg()

        # TF: odom -> base_link
        tf = TransformStamped()
        tf.header.stamp = stamp
        tf.header.frame_id = self._odom_frame
        tf.child_frame_id = self._base_frame
        tf.transform.translation.x = self._x
        tf.transform.translation.y = self._y
        tf.transform.rotation.z = qz
        tf.transform.rotation.w = qw
        self._tf_broadcaster.sendTransform(tf)

        # /odom
        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = self._odom_frame
        odom.child_frame_id = self._base_frame
        odom.pose.pose.position.x = self._x
        odom.pose.pose.position.y = self._y
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        odom.twist.twist.linear.x = self._vx
        odom.twist.twist.angular.z = self._wz
        odom.pose.covariance[0] = 0.01
        odom.pose.covariance[7] = 0.01
        odom.pose.covariance[35] = 0.02
        self._odom_pub.publish(odom)


def main(args=None):
    rclpy.init(args=args)
    node = OdometryNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
