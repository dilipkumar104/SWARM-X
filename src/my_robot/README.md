# my_robot — SWARM-X ROS2 Package

The single active ROS2 Python package for the SWARM-X robot.

## Production Nodes

These nodes form the active robot runtime pipeline:

| Node | Executable | Purpose | Hardware |
|------|-----------|---------|----------|
| `motor_controller` | `ros2 run my_robot motor_controller` | cmd_vel → L298N GPIO PWM differential drive | L298N + 4× BO Motors |
| `obstacle_avoider` | `ros2 run my_robot obstacle_avoider` | Fused LiDAR + HC-SR04 + MLX90614 obstacle avoidance FSM | — (reads sensor topics) |
| `ultrasonic_listener` | `ros2 run my_robot ultrasonic_listener` | ESP32 micro-ROS Range → status classifier (DANGER/WARNING/CLEAR) | HC-SR04 via ESP32 |
| `ir_sensor_node` | `ros2 run my_robot ir_sensor_node` | MLX90614 object + ambient temperature publisher | MLX90614 I2C |
| `imu_node` | `ros2 run my_robot imu_node` | MPU6050 roll/pitch/yaw with complementary filter | MPU6050 I2C |
| `odometry_node` | `ros2 run my_robot odometry_node` | Dead-reckoning from cmd_vel integration (no encoders) | — |
| `diagnostics_node` | `ros2 run my_robot diagnostics_node` | Topic heartbeat watchdog → robot_diagnostics | — |
| `system_monitor` | `ros2 run my_robot system_monitor` | CPU / RAM / Pi temperature | Pi sysfs / psutil |
| `battery_monitor` | `ros2 run my_robot battery_monitor` | 3S LiPo voltage via ADS1115 ADC | ADS1115 I2C |

## Demo Nodes

These are tutorial, test, and experimental nodes. Not part of the robot pipeline:

| Node | Purpose |
|------|---------|
| `chatter_publisher` | ROS2 hello-world demo |
| `ultrasonic_simulator` | Fake HC-SR04 data for testing without ESP32 |
| `swarm_publisher` | Single-robot swarm heartbeat demo |
| `swarm_subscriber` | Swarm status listener demo |
| `swarm_multi_publisher` | Multi-robot swarm simulation demo |

## Future Nodes

| Node | Purpose | Status |
|------|---------|--------|
| `thermal_node` | AMG8833 8×8 thermal camera | Waiting for hardware |

## Launch Files

| File | Usage | Description |
|------|-------|-------------|
| `master.launch.py` | `ros2 launch my_robot master.launch.py` | Full stack with feature toggles (`use_esp32`, `use_slam`, `use_nav2`, `use_rviz`) |
| `robot.launch.py` | `ros2 launch my_robot robot.launch.py` | Minimal Pi-only launch (motor + avoider + ultrasonic + IR + odom) |
| `esp32_ultrasonic.launch.py` | `ros2 launch my_robot esp32_ultrasonic.launch.py` | ESP32 micro-ROS agent + ultrasonic_listener |
| `dashboard.launch.py` | `ros2 launch my_robot dashboard.launch.py` | All sensors + rosbridge for browser dashboard |
| `navigation.launch.py` | (included by master.launch.py) | Nav2 stack (controller, planner, AMCL, costmaps) |
| `rviz.launch.py` | (included by master.launch.py) | RViz2 with swarmx.rviz config |

## I2C Address Map

| Device | Address | Bus |
|--------|---------|-----|
| MLX90614 | `0x5A` (90) | 1 |
| MPU6050 | `0x68` (104) | 1 |
| ADS1115 | `0x48` (72) | 1 |
| AMG8833 (future) | `0x69` (105) | 1 |

> **Note:** MPU6050 and AMG8833 can both be `0x68`. When AMG8833 arrives,
> set MPU6050 AD0 pin HIGH to move it to `0x69`, or set AMG8833 to `0x69`.

## Build

```bash
cd ~/SWARM-X
colcon build --packages-select my_robot
source install/setup.bash
```

## Test

```bash
colcon test --packages-select my_robot
colcon test-result --verbose
```
