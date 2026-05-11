# ─────────────────────────────────────────────────────────────────────────────
# SWARM-X  |  Raspberry Pi 4 (ARM64) — ROS 2 Humble
# Includes: GPIO (RPi.GPIO / gpiozero), rplidar_ros, geometry_msgs
#
# Build on the Pi itself or cross-compile with Docker BuildKit + QEMU.
# ─────────────────────────────────────────────────────────────────────────────
FROM arm64v8/ros:humble-ros-base

LABEL maintainer="dilip <dilip@todo.todo>"
LABEL description="SWARM-X Pi controller — motors + lidar"

# ── 1. System packages ────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Python ecosystem
    python3-pip \
    python3-dev \
    # GPIO
    python3-gpiozero \
    python3-rpi.gpio \
    # Lidar (rplidar serial adapter)
    python3-serial \
    # ROS 2 navigation / sensor messages
    ros-humble-sensor-msgs \
    ros-humble-geometry-msgs \
    ros-humble-nav-msgs \
    # rplidar ROS driver
    ros-humble-rplidar-ros \
    # Useful extras
    udev \
    usbutils \
    && rm -rf /var/lib/apt/lists/*

# ── 2. Python dependencies ────────────────────────────────────────────────────
RUN pip3 install --no-cache-dir \
    setuptools \
    RPi.GPIO \
    gpiozero

# ── 3. FastDDS shared-memory limits (prevents OOM crashes on 2 GB Pi) ─────────
# Increase the default SHM segment size to 64 MB
RUN mkdir -p /etc/fastrtps && \
    echo '<?xml version="1.0" encoding="UTF-8"?>\n\
<profiles xmlns="http://www.eprosima.com/XMLSchemas/fastRTPS_Profiles">\n\
  <transport_descriptors>\n\
    <transport_descriptor>\n\
      <transport_id>shm_transport</transport_id>\n\
      <type>SHM</type>\n\
      <segment_size>67108864</segment_size>\n\
    </transport_descriptor>\n\
  </transport_descriptors>\n\
</profiles>' > /etc/fastrtps/fastdds.xml

ENV FASTRTPS_DEFAULT_PROFILES_FILE=/etc/fastrtps/fastdds.xml

# ── 4. Copy the ROS 2 workspace source ───────────────────────────────────────
WORKDIR /ros2_ws
COPY ros2_ws/src ./src

# ── 5. Build the workspace ────────────────────────────────────────────────────
SHELL ["/bin/bash", "-c"]
RUN source /opt/ros/humble/setup.bash && \
    colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

# ── 6. Entrypoint — source overlays, then run whatever CMD is given ───────────
COPY docker/pi/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

CMD ["ros2", "launch", "my_robot", "robot.launch.py"]
