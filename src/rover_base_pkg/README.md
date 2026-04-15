# 🤖 rover_base_pkg — Minimal Rover Base System

A minimal, clean, and testable ROS2 Humble package for a 4WD rover using:
- **Raspberry Pi 4B** — runs ROS2 nodes
- **ESP32** — reads sensors + drives motors
- **UART Serial** — communication bridge between Pi ↔ ESP32

---

## 📁 Folder Structure

```
SWARM-X/
├── esp32_firmware/
│   └── esp32_rover.ino          # ESP32 Arduino firmware
├── src/
│   └── rover_base_pkg/
│       ├── package.xml
│       ├── setup.py
│       ├── setup.cfg
│       ├── resource/
│       │   └── rover_base_pkg   # ament marker
│       ├── rover_base_pkg/
│       │   ├── __init__.py
│       │   ├── ultrasonic_node.py   # Reads distance from ESP32
│       │   └── motor_cmd_node.py    # Sends motor commands to ESP32
│       └── launch/
│           └── rover_launch.py      # Launches both nodes
└── README.md
```

---

## 🔌 Wiring Diagram

### HC-SR04 Ultrasonic Sensor → ESP32

| HC-SR04 Pin | ESP32 Pin | Notes              |
|-------------|----------|--------------------|
| VCC         | 5V       | Use 5V supply      |
| GND         | GND      | Common ground       |
| TRIG        | GPIO 5   | Trigger pulse       |
| ECHO        | GPIO 18  | ⚠️ Use voltage divider (5V → 3.3V) |

> **⚠️ IMPORTANT:** The HC-SR04 ECHO pin outputs 5V. ESP32 GPIOs are 3.3V tolerant at best. Use a voltage divider (1kΩ + 2kΩ) or a level shifter on the ECHO line to avoid damaging your ESP32.

### L298N Motor Driver → ESP32

| L298N Pin | ESP32 Pin | Function               |
|-----------|----------|------------------------|
| ENA       | GPIO 13  | Left motors speed (PWM) |
| IN1       | GPIO 12  | Left motors direction   |
| IN2       | GPIO 14  | Left motors direction   |
| ENB       | GPIO 27  | Right motors speed (PWM)|
| IN3       | GPIO 26  | Right motors direction  |
| IN4       | GPIO 25  | Right motors direction  |
| GND       | GND      | Common ground           |

### Motor Connections to L298N

| L298N Output | Motor                |
|-------------|----------------------|
| OUT1 + OUT2 | Left motors (front + rear wired in parallel) |
| OUT3 + OUT4 | Right motors (front + rear wired in parallel)|

### ESP32 ↔ Raspberry Pi (UART)

| Connection     | Details                    |
|---------------|----------------------------|
| ESP32 USB     | → Raspberry Pi USB port    |
| Serial device | `/dev/ttyUSB0` (default)   |
| Baud rate     | 115200                     |

> Connect the ESP32 to the Raspberry Pi via a USB cable. The ESP32 will appear as `/dev/ttyUSB0` (or `/dev/ttyACM0` depending on the ESP32 board).

### Power

| Component   | Power Source                        |
|------------|-------------------------------------|
| ESP32      | USB from Raspberry Pi (or separate) |
| L298N      | External 7–12V battery              |
| Motors     | Via L298N output terminals          |
| Raspberry Pi | 5V 3A supply (separate from motors)|

---

## 📡 Serial Protocol

### ESP32 → Raspberry Pi (Sensor Data)
```
DIST:25\n
DIST:142\n
DIST:-1\n     ← no echo / out of range
```
Sent every **200ms**.

### Raspberry Pi → ESP32 (Motor Commands)
| Command | Action                                    |
|---------|-------------------------------------------|
| `F`     | Forward — all motors forward              |
| `B`     | Backward — all motors backward            |
| `L`     | Left — left motors stop, right forward    |
| `R`     | Right — right motors stop, left forward   |
| `S`     | Stop — all motors stop                    |

---

## ⚡ ESP32 Firmware Upload

### Prerequisites
- Install [Arduino IDE](https://www.arduino.cc/en/software) or [PlatformIO](https://platformio.org/)
- Add ESP32 board support:
  - Arduino IDE: File → Preferences → Add to Board URLs:
    ```
    https://espressif.github.io/arduino-esp32/package_esp32_index.json
    ```
  - Then: Tools → Board → Board Manager → search "esp32" → Install

### Upload Steps
1. Open `esp32_firmware/esp32_rover.ino` in Arduino IDE
2. Select board: **Tools → Board → ESP32 Dev Module**
3. Select port: **Tools → Port → COMx** (your ESP32)
4. Click **Upload** (→ button)
5. Open **Serial Monitor** at **115200 baud** to verify `DIST:XX` output

---

## 🚀 ROS2 Setup & Run (Raspberry Pi)

### Prerequisites
```bash
# Install ROS2 Humble (if not already)
# See: https://docs.ros.org/en/humble/Installation.html

# Install Python serial library
pip install pyserial
```

### Build the Package
```bash
cd ~/SWARM-X

# Build only this package
colcon build --packages-select rover_base_pkg

# Source the workspace
source install/setup.bash
```

### Run Both Nodes (Launch File)
```bash
ros2 launch rover_base_pkg rover_launch.py
```

### Run Nodes Individually
```bash
# Terminal 1: Ultrasonic node
ros2 run rover_base_pkg ultrasonic_node

# Terminal 2: Motor command node
ros2 run rover_base_pkg motor_cmd_node
```

### Override Serial Port (if not /dev/ttyUSB0)
```bash
ros2 run rover_base_pkg ultrasonic_node --ros-args -p serial_port:=/dev/ttyACM0
ros2 run rover_base_pkg motor_cmd_node --ros-args -p serial_port:=/dev/ttyACM0
```

---

## 🧪 Testing

### 1. Check Ultrasonic Data
```bash
# Monitor the /ultrasonic topic
ros2 topic echo /ultrasonic
```
You should see:
```
data: 25.0
---
data: 34.0
---
```

### 2. Send Motor Commands
```bash
# Forward
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 1.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# Backward
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: -1.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# Turn Left
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 1.0}}"

# Turn Right
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: -1.0}}"

# Stop
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

### 3. Check Active Topics
```bash
ros2 topic list
# Should show:
#   /ultrasonic
#   /cmd_vel
```

### 4. Check Node Status
```bash
ros2 node list
# Should show:
#   /ultrasonic_node
#   /motor_cmd_node
```

---

## ⚠️ Important Notes

### Serial Port Sharing
Both nodes use the same serial port (`/dev/ttyUSB0`) by default. The ESP32 USB serial handles full-duplex communication, so both reading and writing can occur simultaneously. However, if you experience issues:
- Use **two separate USB-to-UART adapters** with different ports
- Update the launch file with different `serial_port` parameters for each node

### Serial Permissions (Linux)
```bash
# Add your user to the dialout group (one-time setup)
sudo usermod -a -G dialout $USER

# Then log out and back in, or run:
newgrp dialout
```

### Debugging
```bash
# Check if ESP32 is detected
ls -la /dev/ttyUSB*
ls -la /dev/ttyACM*

# Monitor raw serial data (install screen first)
screen /dev/ttyUSB0 115200
# Press Ctrl+A then K to exit screen
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Raspberry Pi 4B                      │
│                     (ROS2 Humble)                        │
│                                                         │
│  ┌──────────────────┐     ┌──────────────────┐         │
│  │ ultrasonic_node   │     │  motor_cmd_node  │         │
│  │                   │     │                  │         │
│  │ Reads serial      │     │ Subscribes to    │         │
│  │ Publishes Float32 │     │ /cmd_vel (Twist) │         │
│  │ → /ultrasonic     │     │ Sends F/B/L/R/S  │         │
│  └────────┬──────────┘     └────────┬─────────┘         │
│           │ UART RX                 │ UART TX            │
└───────────┼─────────────────────────┼───────────────────┘
            │        USB Serial       │
┌───────────┼─────────────────────────┼───────────────────┐
│           ▼                         ▼                    │
│  ┌─────────────────┐     ┌──────────────────┐           │
│  │ HC-SR04 Reader   │     │  Motor Driver    │           │
│  │ Sends DIST:XX    │     │  L298N Control   │           │
│  └─────────────────┘     └──────────────────┘           │
│                          ESP32                           │
└─────────────────────────────────────────────────────────┘
```
