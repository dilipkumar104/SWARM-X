#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Docker entrypoint for the SWARM-X Pi container.
# Sources both the system ROS 2 overlay and the local workspace overlay before
# handing control to whatever CMD was passed (default: robot.launch.py).
# ─────────────────────────────────────────────────────────────────────────────
set -e

# Source ROS 2 Humble base
source /opt/ros/humble/setup.bash

# Source the built workspace overlay (if it exists)
if [ -f /ros2_ws/install/setup.bash ]; then
    source /ros2_ws/install/setup.bash
fi

# Set shared domain so the laptop and Pi discover each other
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-42}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🤖 SWARM-X Pi Container"
echo "  ROS_DOMAIN_ID  = ${ROS_DOMAIN_ID}"
echo "  ROS_DISTRO     = ${ROS_DISTRO}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exec "$@"
