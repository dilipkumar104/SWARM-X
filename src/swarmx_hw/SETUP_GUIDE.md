# 🛠️ SWARM-X Setup Guide — Pi ↔ Laptop Distributed Architecture

> **This guide covers everything you need to get Robot 1 mapping a room autonomously.**  
> Pi handles hardware. Laptop handles SLAM. Both talk via FastDDS Discovery Server.

---

## 📋 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    NETWORK (5 GHz Hotspot)                          │
│                    ROS_DOMAIN_ID = 30                                │
│                                                                     │
│  ┌──────────────────────────┐    ┌───────────────────────────────┐  │
│  │  RASPBERRY PI 4 (2GB)    │    │  LAPTOP (Ubuntu 22.04)        │  │
│  │  Ubuntu Server 22.04     │    │  ROS 2 Humble Desktop         │  │
│  │                          │    │                               │  │
│  │  swarmx_hw package:      │    │  Heavy computation:           │  │
│  │  ├─ motor_driver         │    │  ├─ slam_toolbox              │  │
│  │  ├─ rplidar_node         │───▶│  ├─ Nav2                     │  │
│  │  ├─ ultrasonic_node      │    │  ├─ RViz2                     │  │
│  │  └─ thermal_sensor       │    │  └─ Foxglove                  │  │
│  │                          │    │                               │  │
│  │  Role: SUPER CLIENT      │    │  Role: DISCOVERY SERVER       │  │
│  └──────────────────────────┘    └───────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1️⃣ RPLidar A1 Installation

### On BOTH Pi and Laptop:

```bash
# ── Option A: Install from apt (recommended) ─────────────────────
sudo apt update
sudo apt install ros-humble-rplidar-ros -y
```

```bash
# ── Option B: Build from source (if apt version has issues) ──────
cd ~/SWARM-X
mkdir -p lidar_ws/src && cd lidar_ws/src
git clone -b humble https://github.com/Slamtec/rplidar_ros.git
cd ~/SWARM-X/lidar_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select rplidar_ros
source install/setup.bash
```

### Verify installation:

```bash
ros2 pkg list | grep rplidar
# Expected output: rplidar_ros
```

---

## 2️⃣ udev Rules & Permissions (Pi Only)

### Create a persistent symlink so the LiDAR always appears as `/dev/rplidar`:

```bash
# ── Step 1: Find the LiDAR's vendor/product IDs ──────────────────
# Plug in the RPLidar via USB, then:
lsusb | grep -i "cp210\|silicon\|cygnal"
# Example output: Bus 001 Device 004: ID 10c4:ea60 Silicon Labs CP210x

# ── Step 2: Create udev rule ─────────────────────────────────────
sudo tee /etc/udev/rules.d/99-rplidar.rules << 'EOF'
# RPLidar A1 — Silicon Labs CP210x USB-to-UART
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", \
  SYMLINK+="rplidar", MODE="0666"
EOF

# ── Step 3: Reload udev and trigger ──────────────────────────────
sudo udevadm control --reload-rules
sudo udevadm trigger

# ── Step 4: Verify ───────────────────────────────────────────────
ls -la /dev/rplidar
# Should show: /dev/rplidar -> ttyUSB0

# ── Step 5: Add user to dialout group (one-time) ─────────────────
sudo usermod -aG dialout $USER
# IMPORTANT: Log out and back in for this to take effect!
newgrp dialout   # Or just reboot
```

### Now launch with the persistent symlink:

```bash
ros2 launch swarmx_hw robot1_hw_launch.py lidar_port:=/dev/rplidar
```

---

## 3️⃣ Quick LiDAR Test (Pi Only)

Before setting up the full network, test the LiDAR locally on the Pi:

```bash
source /opt/ros/humble/setup.bash

# Test with default port:
ros2 launch rplidar_ros rplidar_a1_launch.py serial_port:=/dev/rplidar

# In another SSH session:
ros2 topic echo /scan --once
# Should print LaserScan data with ranges array
```

> ⚠️ **POWER WARNING:** If the LiDAR motor doesn't spin or the Pi crashes:
> - The Pi 4 USB ports can only supply ~600 mA per port
> - The RPLidar A1 motor draws ~500 mA at startup
> - If motors are also drawing power, there's not enough current
> 
> **Fix: Use a powered USB hub** between the Pi and the LiDAR.
> Any hub rated for 2A+ will work (e.g. ₹500-800 Amazon hub).
> Connect: `Pi USB → Powered Hub → RPLidar USB cable`

---

## 4️⃣ Clock Synchronization (CRITICAL for SLAM)

**SLAM requires synchronized clocks between Pi and Laptop.** If clocks drift by more than ~100ms, tf transforms will fail and the map won't build.

### Install chrony on BOTH devices:

```bash
sudo apt install chrony -y
```

### Option A: Both sync to internet NTP (simplest)

If both devices have internet access via the hotspot:

```bash
# On BOTH devices — this is the default config, just verify:
sudo systemctl enable chrony
sudo systemctl start chrony

# Check sync status:
chronyc tracking
# Look for "Leap status: Normal" and "System time: 0.000XXXX seconds"
```

### Option B: Laptop as NTP server (no internet on hotspot)

If the hotspot has no internet, make the laptop the time source:

**On Laptop (NTP server):**
```bash
sudo tee -a /etc/chrony/chrony.conf << 'EOF'

# Allow Pi to sync from this laptop
allow 192.168.0.0/16
allow 10.0.0.0/8

# Serve time even when not synced to external source
local stratum 10
EOF

sudo systemctl restart chrony
```

**On Pi (NTP client):**
```bash
# Replace <LAPTOP_IP> with your laptop's IP on the hotspot
sudo tee -a /etc/chrony/chrony.conf << 'EOF'

# Sync time from laptop
server <LAPTOP_IP> iburst prefer
EOF

sudo systemctl restart chrony

# Verify sync:
chronyc sources
# Should show ^* next to your laptop's IP (selected source)
```

### Quick one-time force-sync (if chrony isn't ready yet):

```bash
# On the Pi:
sudo date --set="$(ssh user@<LAPTOP_IP> date)"
```

---

## 5️⃣ FastDDS Discovery Server Setup

This eliminates DDS multicast traffic, which saves ~50 MB RAM on the Pi.

### Step 1: Find IP addresses

```bash
# On BOTH devices (connected to the same hotspot):
hostname -I
# Example: Laptop = 192.168.43.100, Pi = 192.168.43.101
```

### Step 2: Update config files with your IPs

Edit `config/fastdds_discovery_server.xml` and `config/fastdds_discovery_super_client.xml`:
- Replace `192.168.1.100` with your **Laptop's actual IP**.

### Step 3: Start Discovery Server (LAPTOP)

```bash
# ── Terminal 1 on Laptop: Start the Discovery Server ─────────────
export ROS_DOMAIN_ID=30
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp

# Start the server (replace IP with yours)
fastdds discovery -i 0 -l <LAPTOP_IP> -p 11811

# Expected output:
# ### Server is running ###
#   Participant Type: SERVER
#   Server ID:        0
#   Server GUID:      44.53.00.5f.45.50.52.4f.53.49.4d.41
#   Server Addresses: UDPv4:[<LAPTOP_IP>]:11811
```

### Step 4: Configure Pi environment

```bash
# ── Add to ~/.bashrc on the Pi ───────────────────────────────────
cat >> ~/.bashrc << 'EOF'

# ── SWARM-X ROS2 Environment ─────────────────────────────────────
source /opt/ros/humble/setup.bash
source ~/SWARM-X/install/setup.bash

export ROS_DOMAIN_ID=30
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DISCOVERY_SERVER="<LAPTOP_IP>:11811"
export FASTRTPS_DEFAULT_PROFILES_FILE=~/SWARM-X/src/swarmx_hw/config/fastdds_discovery_super_client.xml
EOF

source ~/.bashrc
```

### Step 5: Configure Laptop environment

```bash
# ── Add to ~/.bashrc on the Laptop ──────────────────────────────
cat >> ~/.bashrc << 'EOF'

# ── SWARM-X ROS2 Environment ─────────────────────────────────────
source /opt/ros/humble/setup.bash
source ~/SWARM-X/install/setup.bash

export ROS_DOMAIN_ID=30
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DISCOVERY_SERVER="<LAPTOP_IP>:11811"
export FASTRTPS_DEFAULT_PROFILES_FILE=~/SWARM-X/src/swarmx_hw/config/fastdds_discovery_server.xml
EOF

source ~/.bashrc
```

### Step 6: Verify cross-device communication

```bash
# On Pi — publish a test message:
ros2 topic pub /test std_msgs/msg/String "{data: 'hello from Pi'}" --once

# On Laptop — should see it:
ros2 topic echo /test --once
# Expected: data: hello from Pi
```

---

## 6️⃣ Build & Launch (Pi)

```bash
# SSH into the Pi
ssh swarmx@<PI_IP>

# Build the package
cd ~/SWARM-X
colcon build --packages-select swarmx_hw
source install/setup.bash

# Launch all hardware nodes
ros2 launch swarmx_hw robot1_hw_launch.py lidar_port:=/dev/rplidar
```

### Expected output:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🤖 SWARM-X Robot 1 — Hardware Launch
  Namespace : /robot1/
  Nodes     : motor_driver, rplidar, ultrasonic, thermal
  Platform  : Raspberry Pi 4 (2GB)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🏎️  SWARM-X Motor Driver Node READY
  📡 SWARM-X Ultrasonic Node READY
  🌡️  SWARM-X Thermal Sensor Node READY
  [rplidar_node] RPLidar running, firmware version: ...
```

---

## 7️⃣ SLAM on Laptop

### Install required packages:

```bash
sudo apt install ros-humble-slam-toolbox \
                 ros-humble-nav2-bringup \
                 ros-humble-navigation2 \
                 ros-humble-explore-lite -y
```

### Launch SLAM (while Pi hardware nodes are running):

```bash
# ── Terminal 1: SLAM ─────────────────────────────────────────────
ros2 launch slam_toolbox online_async_launch.py \
  slam_params_file:=~/SWARM-X/src/swarmx_hw/config/slam_params.yaml \
  use_sim_time:=false

# ── Terminal 2: RViz2 ────────────────────────────────────────────
rviz2
# In RViz2:
#   - Set Fixed Frame to "map"
#   - Add → By topic → /robot1/scan → LaserScan
#   - Add → By topic → /map → Map
#   - You should see the LiDAR dots and map building

# ── Terminal 3: Teleop (drive the robot from laptop) ─────────────
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args -r cmd_vel:=/robot1/cmd_vel

# ── Drive slowly around the room ─────────────────────────────────
# Watch the map build in RViz2!
```

### Save the map:

```bash
ros2 run nav2_map_server map_saver_cli -f ~/lab_map
# Creates: ~/lab_map.pgm and ~/lab_map.yaml
```

---

## 8️⃣ Autonomous Navigation (Day 6+)

After you have a saved map:

```bash
# ── Launch Nav2 with your map ────────────────────────────────────
ros2 launch nav2_bringup bringup_launch.py \
  map:=~/lab_map.yaml \
  use_sim_time:=false \
  params_file:=~/SWARM-X/src/swarmx_hw/config/slam_params.yaml

# In RViz2:
#   - Click "2D Pose Estimate" → click on map where robot is → drag for heading
#   - Click "2D Nav Goal" → click destination → robot drives there!
```

### Full autonomous exploration:

```bash
# Launch explore_lite (robot explores by itself):
ros2 launch explore_lite explore.launch.py
# No keyboard needed — robot maps the room autonomously!
```

---

## 9️⃣ Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| LiDAR doesn't spin | Insufficient USB power | Use a **powered USB hub** |
| `/scan` topic shows no data | Wrong serial port | Check `ls /dev/ttyUSB*`, verify udev rule |
| Topics not visible across devices | DDS not configured | Verify `ROS_DISCOVERY_SERVER` env var on both |
| SLAM map is blank | Clock drift | Run `chronyc tracking` on both, force-sync |
| Motors don't move | GPIO permissions | Run with `sudo` or add user to `gpio` group |
| Ultrasonic reads -1 | Wiring issue | Check voltage divider on ECHO pin |
| `RPi.GPIO not available` | Not on a Pi | Normal on laptop — nodes run in sim mode |
| Map is noisy/jittery | Driving too fast | Drive slower during mapping |
| Robot veers to one side | PWM mismatch | Adjust `max_linear_speed` parameter |
| Pi runs out of RAM | Too many DDS participants | Verify FastDDS Discovery Server is running |

---

## 🔑 Quick Reference Commands

```bash
# ══════════════════════════════════════════════════════════════════
#  PI (SSH session)
# ══════════════════════════════════════════════════════════════════

# Launch all hardware nodes:
ros2 launch swarmx_hw robot1_hw_launch.py lidar_port:=/dev/rplidar

# Check topics:
ros2 topic list | grep robot1

# Monitor LiDAR data:
ros2 topic hz /robot1/scan

# Monitor ultrasonic:
ros2 topic echo /robot1/ultrasonic_front


# ══════════════════════════════════════════════════════════════════
#  LAPTOP
# ══════════════════════════════════════════════════════════════════

# Start Discovery Server (FIRST!):
fastdds discovery -i 0 -l <LAPTOP_IP> -p 11811

# Launch SLAM:
ros2 launch slam_toolbox online_async_launch.py \
  slam_params_file:=~/SWARM-X/src/swarmx_hw/config/slam_params.yaml

# Teleop:
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args -r cmd_vel:=/robot1/cmd_vel

# Save map:
ros2 run nav2_map_server map_saver_cli -f ~/lab_map

# View in RViz2:
rviz2
```

---

> Built with ❤️ for **SWARM-X** | ROS 2 Humble | Ubuntu 22.04 | April 2025
