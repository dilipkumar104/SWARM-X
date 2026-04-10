# 🔌 ESP32 Firmware — Ultrasonic Publisher (micro-ROS)

This directory contains the Arduino sketch that runs on the **ESP32** to read an **HC-SR04 ultrasonic sensor** and publish `sensor_msgs/msg/Range` to the ROS2 topic `/ultrasonic/range` via **micro-ROS over USB Serial**.

---

## 📦 Hardware Required

| Component         | Quantity | Notes |
|-------------------|----------|-------|
| ESP32 Dev Board   | 1        | Any variant (DevKitC, NodeMCU-32S, etc.) |
| HC-SR04 Sensor    | 1        | 5V ultrasonic range sensor |
| Jumper wires      | 4        | Female-to-male |
| USB cable          | 1        | Micro-USB or USB-C (depends on board) |

---

## 🔧 Wiring Diagram

```
    HC-SR04                ESP32
    ┌───────┐             ┌──────────┐
    │ VCC   │─────────────│ 5V (VIN) │
    │ GND   │─────────────│ GND      │
    │ TRIG  │─────────────│ GPIO 5   │
    │ ECHO  │─────────────│ GPIO 18  │
    └───────┘             └──────────┘
```

> ⚠️ **Voltage Note**: The HC-SR04 ECHO pin outputs **5V** logic. Most ESP32 GPIOs are 5V-tolerant on input, but for long-term safety, use a **voltage divider** (1kΩ + 2kΩ) on the ECHO line to step down to 3.3V.

---

## 🛠️ Software Setup

### Step 1 — Install Arduino IDE

Download from [arduino.cc/en/software](https://www.arduino.cc/en/software) (v2.x recommended).

### Step 2 — Add ESP32 Board Support

1. Open **File → Preferences**
2. In **Additional Board Manager URLs**, add:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. Go to **Tools → Board → Boards Manager**
4. Search **"esp32"** and install **"esp32 by Espressif Systems"**

### Step 3 — Install micro_ros_arduino Library

1. Download the pre-built library from:
   - **ROS2 Humble**: [micro_ros_arduino releases](https://github.com/micro-ROS/micro_ros_arduino/releases)
   - Download the `.zip` for your ROS2 distro (e.g., `micro_ros_arduino-humble-v2.x.x.zip`)
2. In Arduino IDE: **Sketch → Include Library → Add .ZIP Library...**
3. Select the downloaded `.zip`

> **Alternative** — Build from source (advanced):
> ```bash
> cd ~/Arduino/libraries
> git clone -b humble https://github.com/micro-ROS/micro_ros_arduino.git
> ```

### Step 4 — Configure Board

In Arduino IDE:
- **Tools → Board** → `ESP32 Dev Module`
- **Tools → Upload Speed** → `115200`
- **Tools → Port** → Select your ESP32's COM port (e.g., `COM3` on Windows, `/dev/ttyUSB0` on Linux)

### Step 5 — Flash the Firmware

1. Open `ultrasonic_publisher.ino` in Arduino IDE
2. Click **Upload** (→ arrow button)
3. Wait for "Done uploading"

---

## 🚦 LED Status Indicators

| LED State            | Meaning |
|----------------------|---------|
| **OFF**              | Waiting for micro-ROS agent — not connected |
| **Solid ON**         | Connected to agent, publishing data |
| **Rapid blinking**   | Error — check wiring or re-flash |
| **Brief flash**      | Each sensor reading published (normal) |

---

## 🖥️ Running the micro-ROS Agent (PC Side)

The micro-ROS agent bridges the ESP32's serial communication to the ROS2 DDS network.

### Install micro-ROS Agent

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

### Start the Agent (USB Serial)

```bash
# Find your port first
ls /dev/ttyUSB*    # Linux
ls /dev/tty.usb*   # macOS

# Start agent
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 -b 115200
```

> **Windows (WSL2)**: You need to attach the USB device to WSL2 first:
> ```powershell
> # In PowerShell (admin):
> usbipd list                          # Find the ESP32 bus ID
> usbipd bind --busid <BUS_ID>
> usbipd attach --wsl --busid <BUS_ID>
> ```
> Then in WSL2 terminal, run the agent command above.

### Start the Agent (WiFi — for future use)

```bash
ros2 run micro_ros_agent micro_ros_agent udp4 --port 8888
```

> For WiFi mode, you'll need to modify the firmware to use `set_microros_wifi_transports("SSID", "PASSWORD", "AGENT_IP", 8888)` instead of `set_microros_transports()`.

---

## ✅ Quick Verification

```bash
# Terminal 1: Start agent
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 -b 115200

# Terminal 2: Check the ESP32 node is visible
ros2 node list
# Expected: /esp32_ultrasonic

# Terminal 3: Echo raw data
ros2 topic echo /ultrasonic/range

# Terminal 4: Run the SWARM-X listener
ros2 run my_robot ultrasonic_listener
```

---

## 🔀 Switching to WiFi (Future)

To switch from USB Serial to WiFi UDP, modify the firmware:

```cpp
// In setup(), replace:
set_microros_transports();

// With:
set_microros_wifi_transports("YOUR_WIFI_SSID", "YOUR_WIFI_PASSWORD", "PC_IP_ADDRESS", 8888);
```

Then on the PC side, run the agent in UDP mode:
```bash
ros2 run micro_ros_agent micro_ros_agent udp4 --port 8888
```
