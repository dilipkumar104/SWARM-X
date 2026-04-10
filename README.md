# 🤖 SWARM-X — ROS2 + ESP32 Ultrasonic Sensor Platform

A ROS2 (Humble/Iron/Jazzy) Python workspace for the **SWARM-X** robot swarm project. Currently implements:

1. **Chatter Publisher** — broadcasts "Hello Swarm-X" to `/chatter` *(✅ working)*
2. **Ultrasonic Listener** — subscribes to `/ultrasonic/range` from an ESP32 and provides proximity alerts *(🆕 new)*
3. **ESP32 Firmware** — micro-ROS Arduino sketch that reads an HC-SR04 sensor and publishes to ROS2 *(🆕 new)*

---

## 📁 Project Structure

```
ros2_ws/
├── .gitignore
├── README.md
└── src/
    └── my_robot/
        ├── package.xml                     # ROS2 package manifest
        ├── setup.py                        # Python build + entry points
        ├── setup.cfg                       # Colcon install paths
        ├── resource/
        │   └── my_robot                    # Ament index marker
        ├── my_robot/
        │   ├── __init__.py
        │   ├── chatter_publisher.py        # ★ Publisher node (/chatter)
        │   └── ultrasonic_listener.py      # ★ Listener node (/ultrasonic/range)
        ├── launch/
        │   └── esp32_ultrasonic.launch.py  # ★ Launch file (agent + listener)
        ├── esp32_firmware/
        │   ├── ultrasonic_publisher.ino    # ★ ESP32 Arduino sketch
        │   └── README.md                   # ESP32 setup guide
        └── test/
            ├── test_copyright.py
            ├── test_flake8.py
            └── test_pep257.py
```

---

## ✅ Prerequisites

| Requirement             | Version / Notes |
|-------------------------|-----------------|
| Ubuntu                  | 22.04 / 24.04 (or WSL2) |
| ROS2                    | Humble / Iron / Jazzy |
| Python                  | 3.10+ |
| colcon                  | latest |
| Arduino IDE             | 2.x (for ESP32 firmware) |
| micro_ros_arduino       | Matching your ROS2 distro |
| micro-ROS Agent         | `ros-humble-micro-ros-agent` |
| ESP32 Dev Board         | Any variant |
| HC-SR04 Sensor          | Ultrasonic range sensor |

Make sure you have sourced your ROS2 installation:

```bash
source /opt/ros/<your-distro>/setup.bash
# Example: source /opt/ros/humble/setup.bash
```

---

## 🔧 Hardware Wiring (HC-SR04 → ESP32)

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

---

## 🔨 Build the ROS2 Package

```bash
cd ~/ros2_ws
colcon build --packages-select my_robot
source install/setup.bash
```

> **Tip:** Add `source ~/ros2_ws/install/setup.bash` to your `~/.bashrc`:
> ```bash
> echo "source ~/ros2_ws/install/setup.bash" >> ~/.bashrc
> ```

---

# 📚 Step-by-Step Guide (Basic → Advanced)

## Level 1 — Basic: Test the Publisher (No Hardware Needed)

This verifies your ROS2 workspace is set up correctly.

```bash
# Terminal 1: Run the chatter publisher
ros2 run my_robot chatter_publisher
```

**Expected output:**
```
[INFO] [chatter_publisher]: ChatterPublisher node started — publishing to /chatter every 1s
[INFO] [chatter_publisher]: [1] Publishing: "Hello Swarm-X"
[INFO] [chatter_publisher]: [2] Publishing: "Hello Swarm-X"
```

```bash
# Terminal 2: Echo the topic
ros2 topic echo /chatter
```

**Expected output:**
```yaml
data: Hello Swarm-X
---
```

✅ **Checkpoint**: If you see messages flowing, your workspace is working.

---

## Level 2 — Intermediate: Test the Listener with Simulated Data (No ESP32 Needed)

Test the ultrasonic listener using the ROS2 CLI to simulate ESP32 data.

```bash
# Terminal 1: Run the listener
ros2 run my_robot ultrasonic_listener
```

**Expected output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🤖 SWARM-X Ultrasonic Listener
  Waiting for ESP32 on /ultrasonic/range ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Now simulate sensor data from a **second terminal**:

```bash
# Simulate an object at 15 cm (0.15 m)
ros2 topic pub /ultrasonic/range sensor_msgs/msg/Range \
  "{header: {frame_id: 'ultrasonic_link'}, radiation_type: 0, field_of_view: 0.26, min_range: 0.02, max_range: 4.0, range: 0.15}" \
  --qos-reliability best_effort
```

**Expected listener output — first message (connection detected):**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ ESP32 CONNECTED — receiving sensor data
  Frame ID       : ultrasonic_link
  Radiation type : Ultrasound
  FOV            : 14.9°
  Min range      : 0.02 m
  Max range      : 4.00 m
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[1] 🟡 WARNING: 15.0 cm — Object nearby
[2] 🟡 WARNING: 15.0 cm — Object nearby
```

### Try different distances:

```bash
# 🔴 DANGER — object at 5 cm
ros2 topic pub /ultrasonic/range sensor_msgs/msg/Range \
  "{header: {frame_id: 'ultrasonic_link'}, radiation_type: 0, field_of_view: 0.26, min_range: 0.02, max_range: 4.0, range: 0.05}" \
  --qos-reliability best_effort

# 🟢 CLEAR — object at 50 cm
ros2 topic pub /ultrasonic/range sensor_msgs/msg/Range \
  "{header: {frame_id: 'ultrasonic_link'}, radiation_type: 0, field_of_view: 0.26, min_range: 0.02, max_range: 4.0, range: 0.50}" \
  --qos-reliability best_effort
```

### Check the status topic:

```bash
# Terminal 3: See processed status
ros2 topic echo /ultrasonic/status
```

**Expected:**
```yaml
data: "🟡 WARNING | 15.0 cm"
---
```

### Test disconnection detection:

1. Stop the `ros2 topic pub` command (Ctrl+C)
2. Wait 3 seconds
3. The listener will show:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ❌ ESP32 DISCONNECTED — no data for 3.1s
  Check USB cable / micro-ROS agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

✅ **Checkpoint**: Listener detects connection, classifies distances, and detects disconnection.

---

## Level 3 — Advanced: Full ESP32 Integration

### Step 3.1 — Flash the ESP32

Follow the detailed guide in [`esp32_firmware/README.md`](src/my_robot/esp32_firmware/README.md).

Quick summary:
1. Install **Arduino IDE 2.x**
2. Add **ESP32 board support** (Espressif)
3. Install **micro_ros_arduino** library (`.zip` from GitHub releases)
4. Open `esp32_firmware/ultrasonic_publisher.ino`
5. Select **Board: ESP32 Dev Module**, **Port: COM3** (or your port)
6. Click **Upload**

### Step 3.2 — Install micro-ROS Agent

```bash
sudo apt install ros-humble-micro-ros-agent
```

> If not available as a package, build from source:
> ```bash
> mkdir -p ~/microros_ws/src
> cd ~/microros_ws/src
> git clone -b humble https://github.com/micro-ROS/micro-ROS-Agent.git
> cd ~/microros_ws
> colcon build
> source install/setup.bash
> ```

### Step 3.3 — Connect and Run

You need **3 terminals** (all with workspace sourced):

```bash
# ── Terminal 1: Start micro-ROS Agent ──────────────────────────
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 -b 115200

# ── Terminal 2: Run the ultrasonic listener ────────────────────
ros2 run my_robot ultrasonic_listener

# ── Terminal 3: Monitor raw data (optional) ────────────────────
ros2 topic echo /ultrasonic/range
```

### Step 3.4 — Verify Everything Is Working

#### ✅ Check 1: ESP32 LED

| LED State          | Meaning |
|--------------------|---------|
| **OFF**            | Waiting for agent — agent not started yet |
| **Solid ON**       | Connected to agent, publishing data |
| **Rapid blink**    | Error — check wiring and re-flash |

#### ✅ Check 2: Agent shows connection

The micro-ROS agent terminal should show:
```
[info] [agent] New session established.
[info] [agent] New publisher created.
```

#### ✅ Check 3: Node is visible

```bash
ros2 node list
```
Expected output includes:
```
/esp32_ultrasonic
/ultrasonic_listener
```

#### ✅ Check 4: Topic is flowing

```bash
ros2 topic list
```
Expected output includes:
```
/ultrasonic/range
/ultrasonic/status
```

```bash
ros2 topic hz /ultrasonic/range
```
Expected: ~10 Hz

#### ✅ Check 5: Listener shows real data

The listener terminal should show live readings:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ ESP32 CONNECTED — receiving sensor data
  Frame ID       : ultrasonic_link
  Radiation type : Ultrasound
  FOV            : 15.0°
  Min range      : 0.02 m
  Max range      : 4.00 m
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[1] 🟢 CLEAR: 45.2 cm
[2] 🟢 CLEAR: 44.8 cm
[3] 🟡 WARNING: 22.1 cm — Object nearby
[4] 🔴 DANGER: 6.3 cm — Object VERY close!
```

#### ✅ Check 6: Unplug the USB cable

1. Physically disconnect the ESP32
2. Within 3 seconds, the listener shows:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ❌ ESP32 DISCONNECTED — no data for 3.1s
  Check USB cable / micro-ROS agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

3. Reconnect the ESP32 — it should auto-reconnect and show ✅ again.

### 🚀 One-Command Launch (Shortcut)

Instead of opening 3 terminals manually, use the launch file:

```bash
# Default (uses /dev/ttyUSB0)
ros2 launch my_robot esp32_ultrasonic.launch.py

# Custom serial port
ros2 launch my_robot esp32_ultrasonic.launch.py serial_port:=/dev/ttyACM0
```

This starts both the micro-ROS agent and the ultrasonic listener automatically.

---

## 🔀 Level 4 — WiFi Mode (Future Upgrade)

To switch from USB Serial to **WiFi UDP**:

### Firmware change

In `ultrasonic_publisher.ino`, modify `setup()`:

```cpp
// Replace this line:
set_microros_transports();

// With:
set_microros_wifi_transports("YOUR_WIFI_SSID", "YOUR_PASSWORD", "192.168.1.100", 8888);
//                            ↑ WiFi name       ↑ WiFi pass     ↑ PC's IP         ↑ Port
```

### Agent change

```bash
# Instead of serial mode, run:
ros2 run micro_ros_agent micro_ros_agent udp4 --port 8888
```

> **Finding your PC's IP:**
> ```bash
> hostname -I   # Linux
> ipconfig      # Windows
> ```

---

## 🔍 Useful Debugging Commands

```bash
# List all active nodes
ros2 node list

# List all topics
ros2 topic list

# Check publishing frequency
ros2 topic hz /ultrasonic/range

# Inspect topic type and publishers
ros2 topic info /ultrasonic/range --verbose

# Echo raw sensor data
ros2 topic echo /ultrasonic/range

# Echo processed status
ros2 topic echo /ultrasonic/status

# Check node details
ros2 node info /esp32_ultrasonic
ros2 node info /ultrasonic_listener
```

---

## 🧪 Run Tests

```bash
cd ~/ros2_ws
colcon test --packages-select my_robot
colcon test-result --verbose
```

---

## ⚠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| `ros2 run my_robot ultrasonic_listener` → "Package not found" | Run `colcon build --packages-select my_robot && source install/setup.bash` |
| Agent says "No serial port" | Check port with `ls /dev/ttyUSB*` — install CH340/CP2102 driver if needed |
| ESP32 LED stays OFF | Agent not running — start it first with `ros2 run micro_ros_agent ...` |
| ESP32 LED blinks rapidly | Firmware error — re-flash and check wiring |
| Listener says "Waiting..." but no data | Check: ① Agent running? ② ESP32 powered? ③ `ros2 topic list` shows `/ultrasonic/range`? |
| WSL2 can't see USB | Use `usbipd` to forward: `usbipd attach --wsl --busid <ID>` |
| WiFi mode no data | Verify PC IP, firewall allows UDP 8888, ESP32 on same network |
| Readings show `inf` | Object too close (< 2 cm) or too far (> 4 m) for HC-SR04 |

---

## 📤 Push to GitHub

```bash
cd ~/ros2_ws
git add .
git commit -m "feat: add ESP32 ultrasonic listener + micro-ROS firmware"
git push
```

---

## 📜 License

This project is open-source. Feel free to use and modify.

---

> Built with ❤️ for **SWARM-X**
