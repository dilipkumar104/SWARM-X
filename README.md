# 🤖 SWARM-X — ROS2 Humble Swarm Robotics Platform

A **ROS2 Humble** Python workspace for the **SWARM-X** robot swarm project, featuring a two-robot simulation network (**Dholu** & **Bholu**), ultrasonic sensor integration, and obstacle avoidance.

---

### What's inside:

| # | Package | Node | Topic | Status |
|---|---------|------|-------|--------|
| 1 | `my_robot` | **Swarm Publisher** | `swarm_status` | ✅ Working |
| 2 | `my_robot` | **Swarm Subscriber** | `swarm_status` | ✅ Working |
| 3 | `my_robot` | **Swarm Multi-Publisher** | `swarm_status` | ✅ Working |
| 4 | `my_robot` | **Chatter Publisher** | `/chatter` | ✅ Working |
| 5 | `my_robot` | **Ultrasonic Listener** | `ultrasonic/range` | ✅ Working |
| 6 | `my_robot` | **Ultrasonic Simulator** | `ultrasonic/range` | ✅ NEW |
| 7 | `my_robot` | **ESP32 Firmware** | micro-ROS over serial | ✅ Working |
| 8 | `my_robot_controller` | **Obstacle Avoider** | `scan` → `cmd_vel` | ✅ NEW |

> 💡 All topics use **relative names** so ROS2 namespaces work automatically in multi-robot setups.

---

## 📁 Project Structure

```
SWARM-X/
└── ros2_ws/                                ← ROS2 workspace root
    ├── .gitignore
    ├── README.md                           ← 📖 You are here
    └── src/
        ├── my_robot/                       ← ROS2 Python package (swarm nodes)
        │   ├── package.xml
        │   ├── setup.py
        │   ├── setup.cfg
        │   ├── resource/
        │   │   └── my_robot
        │   ├── my_robot/                   ← ★ Python source files
        │   │   ├── __init__.py
        │   │   ├── swarm_publisher.py          # Publisher  (swarm_status)
        │   │   ├── swarm_subscriber.py         # Subscriber (swarm_status)
        │   │   ├── swarm_multi_publisher.py    # Multi-robot publisher
        │   │   ├── chatter_publisher.py        # Publisher  (/chatter)
        │   │   ├── ultrasonic_listener.py      # Listener   (ultrasonic/range)
        │   │   └── ultrasonic_simulator.py     # ★ NEW — Fake sensor data
        │   ├── launch/
        │   │   ├── swarm_simulation.launch.py  # ★ NEW — Dholu & Bholu simulation
        │   │   └── esp32_ultrasonic.launch.py  # ESP32 pipeline launcher
        │   ├── esp32_firmware/
        │   │   ├── ultrasonic_publisher.ino    # ESP32 Arduino sketch
        │   │   └── README.md                   # ESP32 setup guide
        │   └── test/
        │       ├── test_copyright.py
        │       ├── test_flake8.py
        │       └── test_pep257.py
        │
        └── my_robot_controller/            ← ★ NEW package (brain node)
            ├── package.xml
            ├── setup.py
            ├── setup.cfg
            ├── resource/
            │   └── my_robot_controller
            └── my_robot_controller/
                ├── __init__.py
                └── obstacle_avoider.py     # ★ LaserScan → cmd_vel brain
```

---

# 📚 COMPLETE STEP-BY-STEP GUIDE (ROS2 Humble)

> This guide walks you through **everything** — from installing ROS2 Humble to running the two-robot swarm simulation. Every command is copy-paste ready.

---

## ✅ Prerequisites

| Requirement | How to check | How to install |
|-------------|--------------|----------------|
| **Ubuntu 22.04 (Jammy)** | `lsb_release -a` | [Install WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) or upgrade |
| **ROS2 Humble** | `ros2 --version` | See Step 1 below |
| **Python 3.10+** | `python3 --version` | Included with Ubuntu 22.04 |
| **colcon** (build tool) | `colcon --help` | `sudo apt install python3-colcon-common-extensions` |
| **Git** | `git --version` | `sudo apt install git` |

---

## Step 1 — Install ROS2 Humble (If Not Already Installed)

> Skip this step if `ros2 --version` already works.

```bash
# 1. Enable the Universe repository
sudo apt install software-properties-common
sudo add-apt-repository universe

# 2. Add the ROS2 GPG key
sudo apt update && sudo apt install curl -y
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg

# 3. Add the ROS2 repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
  http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# 4. Install ROS2 Humble (Desktop = full install with rviz, rqt, etc.)
sudo apt update
sudo apt install ros-dev-tools -y
sudo apt install ros-humble-desktop -y

# 5. Install colcon build tool
sudo apt install python3-colcon-common-extensions -y
```

---

## Step 2 — Source ROS2 Humble

**What this does:** Tells your terminal where ROS2 is installed.

```bash
  source /opt/ros/humble/setup.bash
```

> 🔁 **Make it permanent** (so you don't have to type it every time):
> ```bash
> echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
> source ~/.bashrc
> ```

---

## Step 3 — Clone & Build the Workspace

```bash
# Clone the repository
cd ~/
git clone https://github.com/dilipkumar104/SWARM-X.git
cd SWARM-X/ros2_ws

# Build BOTH packages
colcon build --packages-select my_robot my_robot_controller

# Source the workspace
source install/setup.bash
```

> 🔁 **Make sourcing permanent:**
> ```bash
> echo "source ~/SWARM-X/ros2_ws/install/setup.bash" >> ~/.bashrc
> source ~/.bashrc
> ```

**Expected build output:**
```
Starting >>> my_robot
Starting >>> my_robot_controller
Finished <<< my_robot [1.2s]
Finished <<< my_robot_controller [1.1s]

Summary: 2 packages finished [1.5s]
```

> ⚠️ **IMPORTANT:** You must source BOTH ROS2 AND your workspace in every terminal:
> ```bash
> source /opt/ros/humble/setup.bash
> source ~/SWARM-X/ros2_ws/install/setup.bash
> ```

---

## Step 4 — If Workspace Already Exists

If you already have the workspace and just need to update:

```bash
cd ~/SWARM-X/ros2_ws

# Clean old builds (if switching distros)
rm -rf build/ install/ log/

# Rebuild everything fresh for Humble
source /opt/ros/humble/setup.bash
colcon build --packages-select my_robot my_robot_controller
source install/setup.bash
```

---

# 🚀 RUNNING THE TWO-ROBOT SIMULATION (Dholu & Bholu)

This is the main feature — a complete two-robot swarm simulation that runs with a **single command**.

## What gets launched:

```
┌─────────────────────────────────────────────────────────────┐
│          SWARM-X Two-Robot Simulation Network                │
│                                                              │
│  /dholu/ namespace                /bholu/ namespace          │
│  ┌──────────────────────┐       ┌──────────────────────┐    │
│  │ swarm_publisher       │       │ swarm_publisher       │    │
│  │ → /dholu/swarm_status │       │ → /bholu/swarm_status │    │
│  │                       │       │                       │    │
│  │ ultrasonic_simulator  │       │ ultrasonic_simulator  │    │
│  │ → /dholu/ultra.../range│      │ → /bholu/ultra.../range│   │
│  │                       │       │                       │    │
│  │ ultrasonic_listener   │       │ ultrasonic_listener   │    │
│  │ ← /dholu/ultra.../range│      │ ← /bholu/ultra.../range│   │
│  └──────────────────────┘       └──────────────────────┘    │
│                                                              │
│  Central Monitors:                                           │
│    /dholu/swarm_monitor  ← listens to /dholu/swarm_status   │
│    /bholu/swarm_monitor  ← listens to /bholu/swarm_status   │
└─────────────────────────────────────────────────────────────┘
```

## Launch the simulation:

```bash
# Source (if not in .bashrc)
source /opt/ros/humble/setup.bash
source ~/SWARM-X/ros2_ws/install/setup.bash

# 🚀 Launch both robots with ONE command
ros2 launch my_robot swarm_simulation.launch.py
```

**Expected output:**
```
[INFO] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[INFO]   🤖 SWARM-X Two-Robot Simulation
[INFO]   Robots: Dholu & Bholu
[INFO] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[INFO]   🚀 Launching Dholu in /dholu/ namespace...
[INFO]   🚀 Launching Bholu in /bholu/ namespace...
[INFO] 🟢 SwarmPublisher started — Dholu publishing to swarm_status every 1s
[INFO] 🟢 SwarmPublisher started — Bholu publishing to swarm_status every 1s
[INFO] 🧪 Ultrasonic SIMULATOR (no hardware needed)
[INFO] 🤖 SWARM-X Ultrasonic Listener
...
```

## Verify the simulation (new terminal):

```bash
source /opt/ros/humble/setup.bash
source ~/SWARM-X/ros2_ws/install/setup.bash

# List all active nodes
ros2 node list
```

**Expected:**
```
/dholu/swarm_publisher
/dholu/ultrasonic_simulator
/dholu/ultrasonic_listener
/dholu/swarm_monitor
/bholu/swarm_publisher
/bholu/ultrasonic_simulator
/bholu/ultrasonic_listener
/bholu/swarm_monitor
```

```bash
# List all active topics
ros2 topic list
```

**Expected:**
```
/dholu/swarm_status
/dholu/ultrasonic/range
/dholu/ultrasonic/status
/bholu/swarm_status
/bholu/ultrasonic/range
/bholu/ultrasonic/status
```

```bash
# Echo a specific robot's status
ros2 topic echo /dholu/swarm_status

# Echo Bholu's ultrasonic data
ros2 topic echo /bholu/ultrasonic/range
```

---

# 🧪 TESTING THE ULTRASONIC SENSOR

## Option A — Without Hardware (Simulator)

You can test the full ultrasonic pipeline **without any ESP32 or sensor hardware**:

```bash
# Terminal 1: Start the ultrasonic simulator
ros2 run my_robot ultrasonic_simulator

# Terminal 2: Start the ultrasonic listener
ros2 run my_robot ultrasonic_listener
```

**Expected output (listener):**
```
[INFO] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[INFO]   🤖 SWARM-X Ultrasonic Listener
[INFO]   Waiting for data on ultrasonic/range ...
[INFO] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[INFO]   ✅ ESP32 CONNECTED — receiving sensor data
[INFO] [1] 🔴 DANGER: 2.0 cm — Object VERY close!
[INFO] [2] 🔴 DANGER: 7.0 cm — Object VERY close!
[INFO] [3] 🟡 WARNING: 12.0 cm — Object nearby
[INFO] [4] 🟡 WARNING: 17.0 cm — Object nearby
...
[INFO] [8] 🟢 CLEAR: 37.0 cm
[INFO] [9] 🟢 CLEAR: 42.0 cm
```

The simulator sweeps the distance from 2cm → 400cm → 2cm in a triangle wave, exercising all zones:
- 🔴 **DANGER** (< 10 cm)
- 🟡 **WARNING** (< 30 cm)
- 🟢 **CLEAR** (≥ 30 cm)

## Option B — With ESP32 Hardware

```bash
# Terminal 1: Start micro-ROS Agent
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 -b 115200

# Terminal 2: Run ultrasonic listener
ros2 run my_robot ultrasonic_listener

# Terminal 3 (optional): Echo raw data
ros2 topic echo /ultrasonic/range
```

> 📎 See the [ESP32 Firmware README](src/my_robot/esp32_firmware/README.md) for wiring and flashing instructions.

---

# 🧠 OBSTACLE AVOIDER (Brain Node)

The `obstacle_avoider` node is the central "brain" that subscribes to laser scan data and publishes velocity commands.

## Architecture:

```
┌──────────────────────────────────────────────────────────────┐
│                   obstacle_avoider (Brain)                    │
│                                                              │
│   LISTENER (Subscriber)         TALKER (Publisher)            │
│   ┌──────────────────┐         ┌──────────────────┐         │
│   │ /scan            │         │ /cmd_vel          │         │
│   │ LaserScan        │ ─────►  │ Twist             │         │
│   │ (sensor data in) │  logic  │ (motor cmds out)  │         │
│   └──────────────────┘         └──────────────────┘         │
└──────────────────────────────────────────────────────────────┘
```

## Logic:

| Condition | Action | Linear X | Angular Z |
|-----------|--------|----------|-----------|
| Path clear (all ranges > 15 cm) | Move forward | 0.22 m/s | 0.0 |
| Obstacle detected (any range ≤ 15 cm) | **STOP** | 0.0 | 0.0 |

## Build & Run:

```bash
# Build the controller package
cd ~/SWARM-X/ros2_ws
colcon build --packages-select my_robot_controller
source install/setup.bash

# Run the obstacle avoider
ros2 run my_robot_controller obstacle_avoider
```

**Expected output:**
```
[INFO] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[INFO]   🧠 SWARM-X Obstacle Avoider (Brain Node)
[INFO]   Threshold : 15 cm
[INFO]   Speed     : 0.22 m/s
[INFO]   Listening : scan  (LaserScan)
[INFO]   Publishing: cmd_vel (Twist)
[INFO] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Dependencies added:

**`package.xml`** — these lines are required:
```xml
<exec_depend>rclpy</exec_depend>
<exec_depend>sensor_msgs</exec_depend>
<exec_depend>geometry_msgs</exec_depend>
```

**`setup.py`** — entry point:
```python
'console_scripts': [
    'obstacle_avoider = my_robot_controller.obstacle_avoider:main',
],
```

## Custom parameters:

```bash
# Change threshold to 20 cm
ros2 run my_robot_controller obstacle_avoider --ros-args -p obstacle_threshold:=0.20

# Change forward speed to 0.5 m/s
ros2 run my_robot_controller obstacle_avoider --ros-args -p forward_speed:=0.5
```

---

# 🔌 RUNNING INDIVIDUAL NODES

## Swarm Publisher (Terminal 1)

```bash
source /opt/ros/humble/setup.bash
source ~/SWARM-X/ros2_ws/install/setup.bash

# Run with default name
ros2 run my_robot swarm_publisher

# Or specify a robot name
ros2 run my_robot swarm_publisher --ros-args -p robot_name:="Dholu"
```

## Swarm Subscriber (Terminal 2)

```bash
source /opt/ros/humble/setup.bash
source ~/SWARM-X/ros2_ws/install/setup.bash

ros2 run my_robot swarm_subscriber
```

**Expected:** Subscriber prints `Received: "Dholu online"` messages.

## Chatter Publisher

```bash
ros2 run my_robot chatter_publisher
```

## Multi-Robot Publisher (Simulates Multiple Robots)

```bash
# Default 2 robots
ros2 run my_robot swarm_multi_publisher

# Override to 5 robots
ros2 run my_robot swarm_multi_publisher --ros-args -p num_robots:=5
```

---

# 🔌 ESP32 Integration Guide (Humble)

## How the ESP32 Connects

```
┌─────────────────────────────────────────────────────────────────┐
│                     SWARM-X Architecture                         │
│                                                                  │
│  ┌──────────────┐    USB Serial    ┌──────────────────────┐     │
│  │   ESP32 +    │ ───────────────► │  micro-ROS Agent     │     │
│  │   HC-SR04    │   115200 baud    │  (bridges serial     │     │
│  │   Sensor     │                  │   to ROS2 DDS)       │     │
│  └──────────────┘                  └────────┬─────────────┘     │
│                                             │                    │
│                                    ultrasonic/range              │
│                                             │                    │
│                                    ┌────────▼─────────────┐     │
│                                    │ ultrasonic_listener   │     │
│                                    │ (Python ROS2 node)    │     │
│                                    └──────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

## Hardware Wiring (HC-SR04 → ESP32)

```
    HC-SR04                ESP32
    ┌───────┐             ┌──────────────┐
    │ VCC   │─────────────│ 5V (VIN)     │
    │ GND   │─────────────│ GND          │
    │ TRIG  │─────────────│ GPIO 5       │
    │ ECHO  │─────────────│ GPIO 18      │
    └───────┘             └──────────────┘

    ⚠ ECHO outputs 5V. For safety, use a voltage divider:
       ECHO ──┤1kΩ├──┬──│GPIO 18│
                      │
                    ┤2kΩ├
                      │
                     GND
```

## Install micro-ROS Agent (Humble)

```bash
# Option A — Install from package (recommended)
sudo apt install ros-humble-micro-ros-agent

# Option B — Build from source
mkdir -p ~/microros_ws/src
cd ~/microros_ws/src
git clone -b humble https://github.com/micro-ROS/micro-ROS-Agent.git
cd ~/microros_ws
colcon build
source install/setup.bash
```

## Flash the ESP32

1. Install **Arduino IDE 2.x** from [arduino.cc/en/software](https://www.arduino.cc/en/software)
2. **File → Preferences** → Add ESP32 board URL:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. **Tools → Board → Boards Manager** → Search "esp32" → Install
4. Download `micro_ros_arduino` Humble release from [GitHub](https://github.com/micro-ROS/micro_ros_arduino/releases)
5. **Sketch → Include Library → Add .ZIP Library** → Select the zip
6. Open `esp32_firmware/ultrasonic_publisher.ino`
7. **Tools → Board** → `ESP32 Dev Module`
8. **Tools → Port** → Select your port
9. Click **Upload** ▶

## Run with ESP32

```bash
# Terminal 1: Start micro-ROS Agent
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 -b 115200

# Terminal 2: Run ultrasonic listener
ros2 run my_robot ultrasonic_listener

# Terminal 3 (optional): Echo raw data
ros2 topic echo /ultrasonic/range
```

## Launch file (one-command start):

```bash
ros2 launch my_robot esp32_ultrasonic.launch.py

# Custom serial port:
ros2 launch my_robot esp32_ultrasonic.launch.py serial_port:=/dev/ttyACM0
```

## WSL2 Users — Forward USB

```powershell
# In PowerShell (as Administrator):
winget install usbipd
usbipd list                        # Find ESP32 bus ID (e.g., 1-3)
usbipd bind --busid <BUS_ID>
usbipd attach --wsl --busid <BUS_ID>
```

Then in WSL2:
```bash
ls /dev/ttyUSB*    # Should show /dev/ttyUSB0
```

---

# 🔌 Connecting it to Real Robots!

Right now, the dashboard runs on high-fidelity simulation logic so you can immediately see how it handles obstacle detection, thermal spikes, and motion changes.

When you want to plug this dashboard into your actual Raspberry Pi robot running ROS2 Humble:

1. **Install Rosbridge on the Raspberry Pi**: Rosbridge creates a WebSocket server on the robot so your browser can securely stream live ROS2 topic data.

   ```bash
   # Run this in your Raspberry Pi Terminal
   sudo apt install ros-humble-rosbridge-suite
   ```

2. **Launch the WebSocket Server on the robot**:

   ```bash
   # Run this in your Raspberry Pi Terminal
   ros2 launch rosbridge_server rosbridge_websocket_launch.xml
   ```

3. **Stream data to the Dashboard**: Include a small library called `roslibjs` in the dashboard file to subscribe to real-time telemetry from topics like `/dholu/scan` or `/bholu/ultrasonic/range` instead of the simulated state engine.

---

# 💡 Full Swarm Architecture (Future Vision)

```
┌────────────────────────────────────────────────────────────────┐
│              Full Swarm Architecture                            │
│                                                                │
│   Dholu ──►  /dholu/swarm_status   ◄── swarm_monitor          │
│   Bholu ──►  /bholu/swarm_status       (monitors all robots)  │
│                                                                │
│   Each robot also publishes:                                    │
│     /dholu/ultrasonic/range    ← obstacle detection            │
│     /dholu/cmd_vel             ← movement commands             │
│     /dholu/scan                ← lidar data                    │
│                                                                │
│   Brain Node (per robot):                                       │
│     obstacle_avoider                                            │
│     - Subscribes to /robot/scan                                │
│     - Publishes to /robot/cmd_vel                              │
│     - Threshold: 15 cm → STOP                                 │
│                                                                │
│   Central Coordinator (future):                                 │
│     - Subscribes to all /*/swarm_status topics                 │
│     - Makes decisions (e.g., avoid collision)                  │
│     - Publishes commands to individual robots                  │
└────────────────────────────────────────────────────────────────┘
```

---

# 🔍 Useful Debugging Commands

```bash
# List all active nodes
ros2 node list

# List all topics
ros2 topic list

# Check publishing frequency
ros2 topic hz /dholu/swarm_status

# Inspect topic type and publishers
ros2 topic info /dholu/swarm_status --verbose

# Echo raw topic data
ros2 topic echo /bholu/ultrasonic/range

# Check node details
ros2 node info /dholu/swarm_publisher
ros2 node info /bholu/ultrasonic_listener

# Publish a test message from the command line
ros2 topic pub /dholu/swarm_status std_msgs/msg/String "{data: 'Dholu test'}" --once
```

---

# 🧪 Run Tests

```bash
cd ~/SWARM-X/ros2_ws
colcon test --packages-select my_robot my_robot_controller
colcon test-result --verbose
```

---

# ⚠️ Common Mistakes & How to Fix Them

| # | Problem | Cause | Solution |
|---|---------|-------|----------|
| 1 | `ros2: command not found` | ROS2 not sourced | Run `source /opt/ros/humble/setup.bash` |
| 2 | `Package 'my_robot' not found` | Workspace not sourced or not built | Run `colcon build --packages-select my_robot && source install/setup.bash` |
| 3 | `No executable found` | Entry point missing in setup.py | Check `console_scripts` in `setup.py`, then rebuild |
| 4 | Subscriber shows no messages | Publisher not running | Start the publisher in another terminal first |
| 5 | `ModuleNotFoundError: rclpy` | Python env mismatch | Source ROS2 before running. Don't use conda/venv. |
| 6 | Build succeeds but node doesn't update | Stale build cache | `rm -rf build install log && colcon build` |
| 7 | `SetuptoolsDeprecationWarning` | Newer Python version | Just a warning — code still works. Ignore it. |
| 8 | WSL2 can't see USB devices | USB not forwarded | Use `usbipd attach --wsl --busid <ID>` in PowerShell (Admin) |
| 9 | Agent says "No serial port" | Wrong port or driver missing | Check with `ls /dev/ttyUSB*`. Install CH340/CP2102 driver. |
| 10 | Namespace topics not appearing | Using absolute topic (`/topic`) | Use relative topics (`topic`) in your code |
| 11 | Old builds failing after distro switch | Mixed distro builds | `rm -rf build install log` and rebuild with Humble sourced |

---

# 📋 Quick Reference — All Commands

```bash
# ── ONE-TIME SETUP ──────────────────────────────────────────
source /opt/ros/humble/setup.bash
cd ~/SWARM-X/ros2_ws
colcon build --packages-select my_robot my_robot_controller
source install/setup.bash

# ── TWO-ROBOT SIMULATION (recommended) ─────────────────────
ros2 launch my_robot swarm_simulation.launch.py

# ── INDIVIDUAL NODES ────────────────────────────────────────
ros2 run my_robot swarm_publisher --ros-args -p robot_name:="Dholu"
ros2 run my_robot swarm_subscriber
ros2 run my_robot ultrasonic_simulator
ros2 run my_robot ultrasonic_listener
ros2 run my_robot chatter_publisher

# ── OBSTACLE AVOIDER ───────────────────────────────────────
ros2 run my_robot_controller obstacle_avoider

# ── ESP32 PIPELINE ──────────────────────────────────────────
ros2 launch my_robot esp32_ultrasonic.launch.py

# ── VERIFY ──────────────────────────────────────────────────
ros2 node list
ros2 topic list
ros2 topic echo /dholu/swarm_status
```

---

# 📤 Push to GitHub

```bash
cd ~/SWARM-X
git add .
git commit -m "feat: migrate to Humble + Dholu/Bholu simulation + obstacle avoider"
git push
```

---

# 📜 License

This project is open-source under the Apache-2.0 license.

---

> Built with ❤️ for **SWARM-X** | ROS2 Humble | Ubuntu 22.04
