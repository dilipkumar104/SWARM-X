# SWARM-X — Single-Robot Search & Rescue Platform

> **Current Scope:** ONE autonomous robot.  
> **Future Scope:** Multi-robot swarm coordination (see `demo/` for early swarm experiments).

---

## Hardware

| Component | Model | Interface | Purpose |
|-----------|-------|-----------|---------|
| SBC | Raspberry Pi 4B (4 GB) | — | Main computer |
| LiDAR | RPLidar A1M8 | USB `/dev/rplidar` | SLAM, navigation, obstacle detection |
| Ultrasonic | HC-SR04 | ESP32 → micro-ROS | Close-range backup / emergency stop |
| Thermal (temporary) | MLX90614 | I2C `0x5A` | Survivor heat detection |
| Thermal (future) | AMG8833 | I2C `0x69` | 8×8 thermal camera (replaces MLX90614) |
| IMU | MPU6050 | I2C `0x68` | Roll / pitch / yaw orientation |
| Motor Driver | L298N Dual H-Bridge | Pi GPIO PWM | Differential-drive motor control |
| Motors | 4× BO DC Motors | L298N outputs | Locomotion |
| Microcontroller | ESP32 DevKit | USB serial / micro-ROS | HC-SR04 bridge to ROS2 |
| Battery | 3S LiPo (11.1 V) | ADS1115 ADC (optional) | Power supply |

### NOT in current build

Jetson Nano, YOLOv8, webcam, PIR sensor (HC-SR501), ESP8266, multi-robot coordination.

---

## Architecture

```
RPLidar A1 ──→ /scan ──→ obstacle_avoider ──→ cmd_vel ──→ motor_controller ──→ L298N ──→ Motors
                              ↑                    ↓
HC-SR04 (ESP32) ──→ ultrasonic/range ──→ ultrasonic_listener ──→ ultrasonic/status
                              ↑
MLX90614 ──→ ir/temperature + ir/ambient
              (ambient-relative detection: obj - amb >= 5°C)

MPU6050  ──→ imu/data + imu/euler
ADS1115  ──→ battery/voltage + battery/status
Pi CPU   ──→ system/status

diagnostics_node ──→ robot_diagnostics (topic heartbeat watchdog)
odometry_node    ──→ odom + TF odom→base_link (dead-reckoning, NO encoders)
```

---

## Repository Structure

```
SWARM-X/
├── dashboard/index.html           # Browser-based live monitoring dashboard
├── docker/pi/                     # Docker deployment for Pi
│   ├── Dockerfile
│   └── entrypoint.sh
├── docker-compose.yml
│
└── src/my_robot/                  # ← Single active ROS2 package
    ├── my_robot/                  # Python nodes
    │   ├── motor_controller.py    # cmd_vel → L298N GPIO PWM
    │   ├── obstacle_avoider.py    # LiDAR + HC-SR04 + IR fused avoidance FSM
    │   ├── ultrasonic_listener.py # ESP32 micro-ROS range → status classifier
    │   ├── ir_sensor_node.py      # MLX90614 object + ambient temperature
    │   ├── imu_node.py            # MPU6050 orientation (complementary filter)
    │   ├── odometry_node.py       # Dead-reckoning from cmd_vel integration
    │   ├── diagnostics_node.py    # Topic heartbeat health monitor
    │   ├── system_monitor.py      # CPU / RAM / temperature
    │   ├── battery_monitor.py     # Battery voltage via ADS1115 ADC
    │   ├── chatter_publisher.py   # [demo] ROS2 hello-world
    │   ├── ultrasonic_simulator.py# [demo] Fake HC-SR04 for testing
    │   ├── swarm_publisher.py     # [demo] Swarm heartbeat publisher
    │   ├── swarm_subscriber.py    # [demo] Swarm heartbeat listener
    │   ├── swarm_multi_publisher.py # [demo] Multi-robot simulation
    │   └── thermal_node.py        # [future] AMG8833 8×8 thermal camera
    │
    ├── launch/
    │   ├── master.launch.py       # Full stack with feature toggles
    │   ├── robot.launch.py        # Minimal Pi-only launch
    │   ├── esp32_ultrasonic.launch.py  # ESP32 micro-ROS + listener
    │   ├── dashboard.launch.py    # Dashboard + rosbridge
    │   ├── navigation.launch.py   # Nav2 autonomous navigation
    │   └── rviz.launch.py         # RViz2 visualisation
    │
    ├── config/
    │   ├── nav2_params.yaml       # Nav2 stack parameters
    │   └── slam_toolbox.yaml      # SLAM Toolbox online async config
    │
    ├── urdf/robot.urdf.xacro      # Robot model (4-wheel + LiDAR + ultrasonic)
    ├── rviz/swarmx.rviz           # Pre-configured RViz2 layout
    ├── esp32_firmware/             # micro-ROS firmware for ESP32
    └── test/                      # Unit tests
```

---

## Quick Start

### 1. Build (on Raspberry Pi)

```bash
cd ~/SWARM-X
colcon build --packages-select my_robot
source install/setup.bash
```

### 2. Launch the Robot

```bash
# Minimal — motors + obstacle avoidance + sensors:
ros2 launch my_robot robot.launch.py

# Full stack with ESP32, IR sensor, IMU, battery monitor:
ros2 launch my_robot master.launch.py

# With SLAM mapping:
ros2 launch my_robot master.launch.py use_slam:=true

# With Nav2 autonomous navigation:
ros2 launch my_robot master.launch.py use_nav2:=true map:=/path/to/map.yaml

# Everything ON (SLAM + Nav2 + RViz on laptop):
ros2 launch my_robot master.launch.py use_slam:=true use_nav2:=true use_rviz:=true
```

### 3. ESP32 Setup (HC-SR04 Ultrasonic)

```bash
# Flash esp32_firmware/ultrasonic_publisher.ino to ESP32
# Then launch the micro-ROS bridge:
ros2 launch my_robot esp32_ultrasonic.launch.py serial_port:=/dev/ttyUSB0
```

### 4. Dashboard

```bash
# Start the dashboard bridge (rosbridge WebSocket):
ros2 launch my_robot dashboard.launch.py

# Open in browser:
# file:///home/pi/SWARM-X/dashboard/index.html
# Or on laptop: http://<pi-ip>:9090 (rosbridge) + open index.html locally
```

### 5. Test Individual Nodes

```bash
# Run any node in simulator mode (no hardware needed):
ros2 run my_robot ir_sensor_node
ros2 run my_robot imu_node --ros-args -p simulate:=true
ros2 run my_robot battery_monitor --ros-args -p simulate:=true
ros2 run my_robot system_monitor

# Test ultrasonic pipeline without ESP32:
ros2 run my_robot ultrasonic_simulator  # Terminal 1
ros2 run my_robot ultrasonic_listener   # Terminal 2
```

---

## Topic Map

| Topic | Message Type | Publisher | Subscriber |
|-------|-------------|----------|------------|
| `scan` | LaserScan | rplidar_ros | obstacle_avoider, diagnostics |
| `ultrasonic/range` | Range | ESP32 (micro-ROS) | ultrasonic_listener |
| `ultrasonic/status` | String | ultrasonic_listener | obstacle_avoider, diagnostics |
| `ir/temperature` | Temperature | ir_sensor_node | obstacle_avoider, diagnostics |
| `ir/ambient` | Temperature | ir_sensor_node | obstacle_avoider |
| `imu/data` | Imu | imu_node | — |
| `imu/euler` | String (JSON) | imu_node | dashboard |
| `cmd_vel` | Twist | obstacle_avoider | motor_controller, odometry |
| `odom` | Odometry | odometry_node | diagnostics, Nav2 |
| `battery/voltage` | BatteryState | battery_monitor | — |
| `battery/status` | String (JSON) | battery_monitor | dashboard |
| `system/status` | String (JSON) | system_monitor | dashboard |
| `robot_diagnostics` | String (JSON) | diagnostics_node | dashboard |

---

## GPIO Pinout (BCM)

| Pin | Function | Connected To |
|-----|----------|-------------|
| GPIO 2 (SDA) | I2C Data | MLX90614, MPU6050 |
| GPIO 3 (SCL) | I2C Clock | MLX90614, MPU6050 |
| GPIO 12 | PWM (ENA) | L298N Left Motor Enable |
| GPIO 13 | PWM (ENB) | L298N Right Motor Enable |
| GPIO 23 | Digital Out (IN1) | L298N Left Forward |
| GPIO 24 | Digital Out (IN2) | L298N Left Reverse |
| GPIO 27 | Digital Out (IN3) | L298N Right Forward |
| GPIO 22 | Digital Out (IN4) | L298N Right Reverse |

ESP32 manages: GPIO 5 (TRIG), GPIO 18 (ECHO) for HC-SR04.

---

## Thermal Detection Strategy

The obstacle avoider uses **ambient-relative** thermal detection:

```
detection = (object_temp - ambient_temp) >= delta_threshold
```

Default `delta_threshold = 5°C`. This prevents false positives in hot Indian summers (30-35°C ambient) while still detecting humans (~37°C body temp → delta ≈ 5-7°C above ambient).

The parameter `ir_delta_threshold_c` can be tuned at launch time.

---

## Known Limitations

1. **Odometry is dead-reckoning only** — no wheel encoders. Drift accumulates without bound. SLAM corrects this via LiDAR scan matching.
2. **IMU yaw drifts** — MPU6050 has no magnetometer. Yaw is pure gyro integration (~1-5°/min drift). Roll and pitch are corrected via accelerometer.
3. **MLX90614 has narrow FOV (~5°)** — it can miss targets outside its cone. The AMG8833 (60° FOV, 8×8 grid) is the planned replacement.
4. **Battery monitoring requires ADS1115** — runs in simulator mode if ADC hardware is not connected.

---

## License

Apache-2.0
