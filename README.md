# 🤖 SWARM-X — ROS2 Swarm Robotics Platform

A ROS2 (Humble/Iron/Jazzy) Python workspace for the **SWARM-X** robot swarm project.

### What's inside:

| # | Node | Topic | Status |
|---|------|-------|--------|
| 1 | **Swarm Publisher** | `/swarm_status` | ✅ NEW |
| 2 | **Swarm Subscriber** | `/swarm_status` | ✅ NEW |
| 3 | **Swarm Multi-Publisher** | `/swarm_status` | ✅ NEW (Bonus) |
| 4 | **Chatter Publisher** | `/chatter` | ✅ Working |
| 5 | **Ultrasonic Listener** | `/ultrasonic/range` | ✅ Working |
| 6 | **ESP32 Firmware** | micro-ROS over serial | ✅ Working |

---

## 📁 Project Structure

```
SWARM-X/
└── ros2_ws/                            ← ROS2 workspace root
    ├── .gitignore
    ├── README.md                       ← 📖 You are here
    └── src/
        └── my_robot/                   ← ROS2 Python package
            ├── package.xml             # Package manifest (dependencies)
            ├── setup.py                # Python build config + entry points
            ├── setup.cfg               # Colcon install paths
            ├── resource/
            │   └── my_robot            # Ament index marker file
            ├── my_robot/               # ★ Python source files
            │   ├── __init__.py
            │   ├── swarm_publisher.py       # ★ NEW — Publisher  (/swarm_status)
            │   ├── swarm_subscriber.py      # ★ NEW — Subscriber (/swarm_status)
            │   ├── swarm_multi_publisher.py # ★ NEW — Multi-robot publisher (Bonus)
            │   ├── chatter_publisher.py     # Publisher  (/chatter)
            │   └── ultrasonic_listener.py   # Listener   (/ultrasonic/range)
            ├── launch/
            │   └── esp32_ultrasonic.launch.py
            ├── esp32_firmware/
            │   ├── ultrasonic_publisher.ino # ESP32 Arduino sketch
            │   └── README.md               # ESP32 setup guide
            └── test/
                ├── test_copyright.py
                ├── test_flake8.py
                └── test_pep257.py
```

---

# 📚 COMPLETE STEP-BY-STEP GUIDE

> This guide walks you through **everything** — from setting up your workspace to running the swarm publisher/subscriber system. Every command is copy-paste ready.

---

## ✅ Prerequisites (What You Need Before Starting)

| Requirement | How to check | How to install |
|-------------|--------------|----------------|
| **Ubuntu 22.04/24.04** (or WSL2 on Windows) | `lsb_release -a` | [Install WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) |
| **ROS2 Humble** (or Iron/Jazzy) | `ros2 --version` | [Install ROS2 Humble](https://docs.ros.org/en/humble/Installation.html) |
| **Python 3.10+** | `python3 --version` | Included with Ubuntu 22.04 |
| **colcon** (build tool) | `colcon --help` | `sudo apt install python3-colcon-common-extensions` |
| **Git** | `git --version` | `sudo apt install git` |

### Additional tools for ESP32 integration (optional — only needed for Level 3):

| Requirement | Notes |
|-------------|-------|
| **Arduino IDE 2.x** | For flashing ESP32 firmware |
| **micro_ros_arduino** | Library matching your ROS2 distro |
| **micro-ROS Agent** | `ros-humble-micro-ros-agent` package |
| **ESP32 Dev Board** | Any variant (DevKitC, NodeMCU-32S, etc.) |
| **HC-SR04 Sensor** | Ultrasonic range sensor |

---

## Step 1 — Source ROS2 Installation

**What this does:** Tells your terminal where ROS2 is installed so you can use `ros2` commands.

```bash
source /opt/ros/humble/setup.bash
```

> 💡 **Replace `humble` with your distro** if you use Iron or Jazzy:
> ```bash
> source /opt/ros/iron/setup.bash    # for Iron
> source /opt/ros/jazzy/setup.bash   # for Jazzy
> ```

> 🔁 **Make it permanent** (so you don't have to type it every time):
> ```bash
> echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
> source ~/.bashrc
> ```

---

## Step 2 — Create the ROS2 Workspace (If Not Already Created)

**What is a workspace?** It's a folder where ROS2 looks for your packages. Think of it as a "project folder" for ROS2.

```bash
# Create the workspace directory
mkdir -p ~/ros2_ws/src

# Go into the workspace
cd ~/ros2_ws
```

> ⚠️ **If you already have the SWARM-X project**, you can skip this step. The workspace is at `SWARM-X/ros2_ws/`.

---

## Step 3 — Create the ROS2 Package (If Not Already Created)

**What is a package?** It's a self-contained unit of code in ROS2 — like a Python project with a specific structure.

```bash
cd ~/ros2_ws/src

# Create a Python package named 'my_robot'
ros2 pkg create --build-type ament_python my_robot
```

This creates the folder structure:
```
src/my_robot/
├── package.xml       ← Lists dependencies
├── setup.py          ← Build configuration + entry points
├── setup.cfg         ← Install paths
├── resource/
│   └── my_robot      ← Marker file (don't delete!)
├── my_robot/
│   └── __init__.py   ← Python package init
└── test/
    └── ...
```

> ⚠️ **If you cloned the SWARM-X repo**, the package already exists. Skip to Step 4.

---

## Step 4 — Add the Publisher Node

**What is a publisher?** A node that SENDS messages to a topic. Other nodes can subscribe to that topic to receive the messages.

Create the file `~/ros2_ws/src/my_robot/my_robot/swarm_publisher.py`:

```python
#!/usr/bin/env python3
"""
swarm_publisher.py — Publishes "Robot 1 online" to /swarm_status every 1 second.
"""

import rclpy                        # ROS2 Python client library
from rclpy.node import Node         # Base class for ROS2 nodes
from std_msgs.msg import String     # Standard string message type


class SwarmPublisher(Node):
    """Publishes robot status messages to /swarm_status."""

    def __init__(self):
        # Initialize the node with name 'swarm_publisher'
        super().__init__('swarm_publisher')

        # Create a publisher on topic '/swarm_status'
        # String = message type, 10 = queue size
        self.publisher_ = self.create_publisher(String, '/swarm_status', 10)

        # Create a timer that fires every 1 second
        self.timer = self.create_timer(1.0, self.timer_callback)

        # Message counter
        self.count = 0

        self.get_logger().info(
            '🟢 SwarmPublisher started — publishing to /swarm_status every 1s'
        )

    def timer_callback(self):
        """Called every 1 second. Publishes the status message."""
        msg = String()
        msg.data = 'Robot 1 online'
        self.publisher_.publish(msg)
        self.count += 1
        self.get_logger().info(f'[{self.count}] Publishing: "{msg.data}"')


def main(args=None):
    rclpy.init(args=args)
    node = SwarmPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
```

### 🔍 Code Explained (Line by Line):

| Line | What it does |
|------|-------------|
| `import rclpy` | Imports the ROS2 Python library |
| `from rclpy.node import Node` | Imports the base class for creating nodes |
| `from std_msgs.msg import String` | Imports the standard String message type |
| `super().__init__('swarm_publisher')` | Creates a node named "swarm_publisher" |
| `self.create_publisher(String, '/swarm_status', 10)` | Creates a publisher that sends String messages to /swarm_status |
| `self.create_timer(1.0, self.timer_callback)` | Calls `timer_callback` every 1.0 second |
| `msg.data = 'Robot 1 online'` | Sets the message content |
| `self.publisher_.publish(msg)` | Sends the message to the topic |
| `rclpy.init()` | Starts the ROS2 system |
| `rclpy.spin(node)` | Keeps the node alive (blocks until Ctrl+C) |

---

## Step 5 — Add the Subscriber Node

**What is a subscriber?** A node that LISTENS for messages on a topic. When a message arrives, it calls a "callback" function.

Create the file `~/ros2_ws/src/my_robot/my_robot/swarm_subscriber.py`:

```python
#!/usr/bin/env python3
"""
swarm_subscriber.py — Subscribes to /swarm_status and prints messages.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class SwarmSubscriber(Node):
    """Listens for robot status messages on /swarm_status."""

    def __init__(self):
        super().__init__('swarm_subscriber')

        # Subscribe to '/swarm_status' topic
        # When a message arrives, call self.listener_callback
        self.subscription = self.create_subscription(
            String,
            '/swarm_status',
            self.listener_callback,
            10,
        )
        self.count = 0
        self.get_logger().info(
            '👂 SwarmSubscriber started — listening on /swarm_status'
        )

    def listener_callback(self, msg: String):
        """Called every time a message arrives on /swarm_status."""
        self.count += 1
        self.get_logger().info(f'[{self.count}] Received: "{msg.data}"')


def main(args=None):
    rclpy.init(args=args)
    node = SwarmSubscriber()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
```

### 🔍 Key Difference from Publisher:

| Publisher | Subscriber |
|-----------|-----------|
| Uses `create_publisher()` | Uses `create_subscription()` |
| Uses a **timer** to send messages at a fixed rate | Uses a **callback** that fires when a message arrives |
| Calls `publisher_.publish(msg)` | Receives `msg` as a function parameter |

---

## Step 6 — Update `setup.py` (Register the Nodes)

**Why?** ROS2 uses `setup.py` to know which Python files are executable nodes. Without this, `ros2 run` won't find your nodes.

Open `~/ros2_ws/src/my_robot/setup.py` and make sure it looks like this:

```python
import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'my_robot'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='dilip',
    maintainer_email='dilip@todo.todo',
    description='SWARM-X ROS2 package — swarm status, chatter publisher + ESP32 ultrasonic listener',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # ── Swarm Status Nodes (NEW) ─────────────────────────
            'swarm_publisher      = my_robot.swarm_publisher:main',
            'swarm_subscriber     = my_robot.swarm_subscriber:main',
            'swarm_multi_publisher = my_robot.swarm_multi_publisher:main',
            # ── Existing Nodes ───────────────────────────────────
            'chatter_publisher    = my_robot.chatter_publisher:main',
            'ultrasonic_listener  = my_robot.ultrasonic_listener:main',
        ],
    },
)
```

### 🔍 Entry Points Explained:

```
'swarm_publisher = my_robot.swarm_publisher:main'
 ↑                 ↑                         ↑
 executable name   package.module            function to call
 (what you type    (file location)           (entry point)
  after ros2 run)
```

---

## Step 7 — Verify `package.xml` (Dependencies)

Open `~/ros2_ws/src/my_robot/package.xml` and ensure these dependencies are listed:

```xml
<!-- Runtime dependencies -->
<exec_depend>rclpy</exec_depend>
<exec_depend>std_msgs</exec_depend>
```

> ✅ These should already be present in the SWARM-X project. `rclpy` is the ROS2 Python library, and `std_msgs` provides the `String` message type.

---

## Step 8 — Build the Package

**What does building do?** It compiles/installs your Python package so ROS2 can find and run your nodes.

```bash
# Go to the workspace root
cd ~/ros2_ws

# Build only our package (faster than building everything)
colcon build --packages-select my_robot
```

**Expected output:**
```
Starting >>> my_robot
Finished <<< my_robot [1.23s]

Summary: 1 package finished [1.45s]
```

> ⚠️ **If you see errors:**
> - `SetuptoolsDeprecationWarning` → This is just a warning, not an error. It still works.
> - `package.xml not found` → Make sure you're in the `ros2_ws` directory, not `ros2_ws/src`.

---

## Step 9 — Source the Workspace

**Why?** After building, you need to tell your terminal about the newly built package.

```bash
source ~/ros2_ws/install/setup.bash
```

> 🔁 **Make it permanent:**
> ```bash
> echo "source ~/ros2_ws/install/setup.bash" >> ~/.bashrc
> source ~/.bashrc
> ```

> ⚠️ **IMPORTANT:** You must source BOTH the ROS2 installation AND your workspace:
> ```bash
> source /opt/ros/humble/setup.bash        # ROS2 itself
> source ~/ros2_ws/install/setup.bash      # Your workspace
> ```

---

## Step 10 — Run the Publisher (Terminal 1)

Open a terminal and run:

```bash
# Source the workspace (if not in .bashrc already)
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

# Run the swarm publisher
ros2 run my_robot swarm_publisher
```

**Expected output:**
```
[INFO] [swarm_publisher]: 🟢 SwarmPublisher started — publishing to /swarm_status every 1s
[INFO] [swarm_publisher]: [1] Publishing: "Robot 1 online"
[INFO] [swarm_publisher]: [2] Publishing: "Robot 1 online"
[INFO] [swarm_publisher]: [3] Publishing: "Robot 1 online"
...
```

> 📌 **Leave this terminal running!** The publisher must be active for the subscriber to receive messages.

---

## Step 11 — Run the Subscriber (Terminal 2)

Open a **NEW terminal** (don't close Terminal 1!) and run:

```bash
# Source the workspace (if not in .bashrc already)
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

# Run the swarm subscriber
ros2 run my_robot swarm_subscriber
```

**Expected output:**
```
[INFO] [swarm_subscriber]: 👂 SwarmSubscriber started — listening on /swarm_status
[INFO] [swarm_subscriber]: [1] Received: "Robot 1 online"
[INFO] [swarm_subscriber]: [2] Received: "Robot 1 online"
[INFO] [swarm_subscriber]: [3] Received: "Robot 1 online"
...
```

> 🎉 **SUCCESS!** If you see "Received" messages in Terminal 2, the publisher and subscriber are communicating!

---

## Step 12 — Verify Everything Works

### ✅ Check 1: List active nodes

Open a **third terminal**:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

ros2 node list
```

**Expected output:**
```
/swarm_publisher
/swarm_subscriber
```

### ✅ Check 2: List active topics

```bash
ros2 topic list
```

**Expected output (should include):**
```
/swarm_status
```

### ✅ Check 3: Inspect the topic

```bash
ros2 topic info /swarm_status
```

**Expected output:**
```
Type: std_msgs/msg/String
Publisher count: 1
Subscription count: 1
```

### ✅ Check 4: Echo the topic directly

```bash
ros2 topic echo /swarm_status
```

**Expected output:**
```yaml
data: Robot 1 online
---
data: Robot 1 online
---
```

### ✅ Check 5: Check publishing frequency

```bash
ros2 topic hz /swarm_status
```

**Expected output:**
```
average rate: 1.000
```

---

## Step 13 — Stop Everything

Press `Ctrl+C` in each terminal to stop the nodes.

---

# 🌟 BONUS: Multi-Robot Publisher

## How to Extend for Multiple Robots

The `swarm_multi_publisher` node simulates multiple robots — all publishing to the same `/swarm_status` topic.

### Run with default 3 robots:

```bash
ros2 run my_robot swarm_multi_publisher
```

**Expected output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🤖 SWARM-X Multi-Robot Publisher
  Simulating 3 robots on /swarm_status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Robot 1 | msg #1] Publishing: "Robot 1 online"
[Robot 2 | msg #1] Publishing: "Robot 2 online"
[Robot 3 | msg #1] Publishing: "Robot 3 online"
[Robot 1 | msg #2] Publishing: "Robot 1 online"
...
```

### Run with 5 robots:

```bash
ros2 run my_robot swarm_multi_publisher --ros-args -p num_robots:=5
```

### Subscribe to see all robots:

In another terminal:

```bash
ros2 run my_robot swarm_subscriber
```

**Expected output:**
```
[1] Received: "Robot 1 online"
[2] Received: "Robot 2 online"
[3] Received: "Robot 3 online"
[4] Received: "Robot 1 online"
[5] Received: "Robot 2 online"
...
```

---

# 🔌 ESP32 Integration Guide

## How the ESP32 Connects to This System

```
┌─────────────────────────────────────────────────────────────────┐
│                     SWARM-X Architecture                        │
│                                                                 │
│  ┌──────────────┐    USB Serial    ┌──────────────────────┐    │
│  │   ESP32 +    │ ───────────────► │  micro-ROS Agent     │    │
│  │   HC-SR04    │   115200 baud    │  (bridges serial     │    │
│  │   Sensor     │                  │   to ROS2 DDS)       │    │
│  └──────────────┘                  └────────┬─────────────┘    │
│                                             │                   │
│                                    /ultrasonic/range            │
│                                             │                   │
│                                    ┌────────▼─────────────┐    │
│                                    │ ultrasonic_listener   │    │
│                                    │ (Python ROS2 node)    │    │
│                                    └────────┬─────────────┘    │
│                                             │                   │
│                                    /ultrasonic/status           │
│                                             │                   │
│  ┌──────────────┐ /swarm_status   ┌────────▼─────────────┐    │
│  │   swarm      │ ◄──────────────►│  (future: decision   │    │
│  │  subscriber  │                 │   making node)        │    │
│  └──────────────┘                 └──────────────────────┘    │
│                                                                 │
│  ┌──────────────┐ /swarm_status                                │
│  │   swarm      │ ──────────────► All subscribers               │
│  │  publisher   │                                               │
│  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 ESP32 Hardware Wiring (HC-SR04 → ESP32)

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

### What you need to buy/download for ESP32:

| Item | Where to get it |
|------|----------------|
| **ESP32 Dev Board** 
| **HC-SR04 Ultrasonic Sensor** 
| **4× Jumper Wires** (Female-to-Male) 
| **USB Cable** (Micro-USB or USB-C) 
| **Arduino IDE 2.x** | [arduino.cc/en/software](https://www.arduino.cc/en/software) |
| **ESP32 Board Support** | Added via Arduino IDE Board Manager |
| **micro_ros_arduino Library** | [GitHub Releases](https://github.com/micro-ROS/micro_ros_arduino/releases) |
| **micro-ROS Agent (PC side)** | `sudo apt install ros-humble-micro-ros-agent` |

### Flash the ESP32:

1. Install **Arduino IDE 2.x**
2. **File → Preferences** → Add ESP32 board URL:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. **Tools → Board → Boards Manager** → Search "esp32" → Install
4. **Sketch → Include Library → Add .ZIP Library** → Select `micro_ros_arduino` zip
5. Open `esp32_firmware/ultrasonic_publisher.ino`
6. **Tools → Board** → `ESP32 Dev Module`
7. **Tools → Port** → Select your port (COM3 on Windows, /dev/ttyUSB0 on Linux)
8. Click **Upload** ▶

### Run with ESP32:

```bash
# Terminal 1: Start micro-ROS Agent
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 -b 115200

# Terminal 2: Run ultrasonic listener
ros2 run my_robot ultrasonic_listener

# Terminal 3 (optional): Echo raw data
ros2 topic echo /ultrasonic/range
```

### WSL2 Users — Forward USB to WSL:

```powershell
# In PowerShell (as Administrator):
winget install usbipd           # Install once
usbipd list                     # Find ESP32 bus ID (e.g., 1-3)
usbipd bind --busid <BUS_ID>   # Bind the device
usbipd attach --wsl --busid <BUS_ID>  # Forward to WSL
```

Then in your WSL2 terminal:
```bash
ls /dev/ttyUSB*    # Should show /dev/ttyUSB0
```

---

## 🔀 WiFi Mode (Future Upgrade)

To switch from USB Serial to **WiFi UDP**:

### Firmware change (in `ultrasonic_publisher.ino`):

```cpp
// Replace this line in setup():
set_microros_transports();

// With:
set_microros_wifi_transports("YOUR_WIFI_SSID", "YOUR_PASSWORD", "192.168.1.100", 8888);
//                            ↑ WiFi name       ↑ WiFi pass     ↑ PC's IP         ↑ Port
```

### Agent change:

```bash
ros2 run micro_ros_agent micro_ros_agent udp4 --port 8888
```

> **Finding your PC's IP:**
> ```bash
> hostname -I   # Linux
> ipconfig      # Windows
> ```

---

## 🚀 Launch File (One-Command Start for ESP32)

```bash
# Default (uses /dev/ttyUSB0)
ros2 launch my_robot esp32_ultrasonic.launch.py

# Custom serial port
ros2 launch my_robot esp32_ultrasonic.launch.py serial_port:=/dev/ttyACM0
```

---

# 💡 How This Fits Into a Swarm Robotics System

```
┌────────────────────────────────────────────────────────────────┐
│              Full Swarm Architecture (Future)                   │
│                                                                │
│   Robot 1 ──►  /swarm_status  ◄── swarm_subscriber            │
│   Robot 2 ──►  /swarm_status       (monitors all robots)      │
│   Robot 3 ──►  /swarm_status                                   │
│                                                                │
│   Each robot also publishes:                                    │
│     /robot_1/ultrasonic/range   ← obstacle detection           │
│     /robot_1/cmd_vel            ← movement commands            │
│     /robot_1/battery            ← battery level                │
│                                                                │
│   Central Coordinator:                                          │
│     - Subscribes to all /swarm_status topics                   │
│     - Makes decisions (e.g., avoid collision)                  │
│     - Publishes commands to individual robots                  │
└────────────────────────────────────────────────────────────────┘
```

### Next steps for a real swarm:

| Feature | Topic | Message Type |
|---------|-------|-------------|
| Robot position | `/robot_N/pose` | `geometry_msgs/msg/Pose` |
| Movement commands | `/robot_N/cmd_vel` | `geometry_msgs/msg/Twist` |
| Obstacle detection | `/robot_N/ultrasonic/range` | `sensor_msgs/msg/Range` |
| Battery status | `/robot_N/battery` | `std_msgs/msg/Float32` |
| Formation control | `/swarm/formation` | Custom message |

---

# 🔍 Useful Debugging Commands

```bash
# List all active nodes
ros2 node list

# List all topics
ros2 topic list

# Check publishing frequency
ros2 topic hz /swarm_status

# Inspect topic type and publishers
ros2 topic info /swarm_status --verbose

# Echo raw topic data
ros2 topic echo /swarm_status

# Check node details
ros2 node info /swarm_publisher
ros2 node info /swarm_subscriber

# Publish a test message from the command line
ros2 topic pub /swarm_status std_msgs/msg/String "{data: 'Robot 99 online'}" --once
```

---

# 🧪 Run Tests

```bash
cd ~/ros2_ws
colcon test --packages-select my_robot
colcon test-result --verbose
```

---

# ⚠️ Common Mistakes & How to Fix Them

| # | Problem | Cause | Solution |
|---|---------|-------|----------|
| 1 | `ros2: command not found` | ROS2 not sourced | Run `source /opt/ros/humble/setup.bash` |
| 2 | `Package 'my_robot' not found` | Workspace not sourced or not built | Run `colcon build --packages-select my_robot && source install/setup.bash` |
| 3 | `No executable found` for swarm_publisher | Entry point missing in setup.py | Add the entry to `console_scripts` in `setup.py`, then rebuild |
| 4 | Subscriber shows no messages | Publisher not running | Make sure the publisher is running in another terminal first |
| 5 | `ModuleNotFoundError: rclpy` | Python environment mismatch | Make sure you source ROS2 before running. Don't use a conda/venv. |
| 6 | Build succeeds but node doesn't update | Stale build cache | Delete `build/` and `install/` folders, then rebuild: `rm -rf build install log && colcon build` |
| 7 | `SetuptoolsDeprecationWarning` | Newer Python version | This is just a warning — your code still works. You can ignore it. |
| 8 | WSL2 can't see USB devices | USB not forwarded | Use `usbipd attach --wsl --busid <ID>` in PowerShell (Admin) |
| 9 | Agent says "No serial port" | Wrong port or driver missing | Check port with `ls /dev/ttyUSB*`. Install CH340/CP2102 driver if needed. |
| 10 | Multiple terminals, different behavior | Each terminal needs sourcing | Run `source /opt/ros/humble/setup.bash && source ~/ros2_ws/install/setup.bash` in EVERY new terminal |

---

# 📋 Quick Reference — All Commands in Order

```bash
# ── ONE-TIME SETUP ──────────────────────────────────────────
source /opt/ros/humble/setup.bash
cd ~/ros2_ws
colcon build --packages-select my_robot
source install/setup.bash

# ── TERMINAL 1: Publisher ───────────────────────────────────
ros2 run my_robot swarm_publisher

# ── TERMINAL 2: Subscriber ──────────────────────────────────
ros2 run my_robot swarm_subscriber

# ── TERMINAL 3 (optional): Verify ──────────────────────────
ros2 node list
ros2 topic list
ros2 topic echo /swarm_status
```

---

# 📤 Push to GitHub

```bash
cd ~/ros2_ws
git add .
git commit -m "feat: add swarm publisher/subscriber + multi-robot support"
git push
```

---

# 📜 License

This project is open-source. Feel free to use and modify.

---

> Built with ❤️ for **SWARM-X**
