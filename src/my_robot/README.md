# 🤖 My First Robot Friend — SWARM-X Guide

> A setup guide written so clearly that even a 10-year-old could follow it.

---

## 📖 What Is This?

This is the SWARM-X robot project!  
It uses a **Raspberry Pi 4** as the "brain" and a **Laptop** as the "boss."

The robot can:
- 🚗 **Drive around** using 4 wheels controlled by a red motor board (L298N).
- 👁️ **See obstacles** using a spinning laser eye (LIDAR).
- 🔄 **Turn away automatically** when it gets too close to a wall.

Everything runs inside **Docker containers** — think of Docker like a lunchbox that holds all the food (software) the robot needs, so nothing spills!

---

## 🧩 The Robot's Body Parts

| Part | What It Does | Where It Lives |
|------|--------------|----------------|
| Raspberry Pi 4 | The Robot's **Brain** | On the robot |
| L298N Motor Driver | The Robot's **Muscle** (makes wheels spin) | On the robot |
| RPLidar A1/A2 | The Robot's **Laser Eye** | On the robot |
| Your Laptop | The **Boss** (sends commands, records data) | In your hands |
| Docker | A **Magic Lunchbox** for software | Both |
| ROS 2 Humble | The **Language** the brain speaks | Both |

---

## 🔌 How to Turn It ON

### Step 1 — Plug in the Brain
Plug the power cable into your **Raspberry Pi**.  
You will see a **red light** (power) and a **green light** (blinking = thinking).

### Step 2 — Give It Muscle Power
Switch on the **battery pack** connected to the **L298N** (the red board with silver walls).

> ⚠️ **Important:** The motors are very "hungry" — they need their own batteries!  
> They cannot eat from the Raspberry Pi's tiny power supply.

### Step 3 — Start the Software (on the Pi)

SSH into the Pi, then run:

```bash
# Make sure Docker is installed and running
cd ~/SWARM-X

# Start both the motor controller AND the obstacle avoider
ROS_DOMAIN_ID=42 docker compose up
```

When you see **"Motor Controller — Node Started"** and **"Obstacle Avoider — Node Started"** in the terminal, your robot is awake and listening! 🎉

---

## 🛑 How to Turn It OFF

### Step 1 — Stop the Thinking
On the Pi terminal, press **`Ctrl + C`**.  
This tells the robot to stop moving and sets all motor pins to LOW (safe stop).

### Step 2 — Cut the Muscle Power
Unplug the **battery from the red L298N board** first.

### Step 3 — Shut Down the Brain
Unplug the **Raspberry Pi**.

---

## 💻 What the Laptop Does

Your laptop is the **boss**. It doesn't need to run Docker — just install ROS 2 Humble on it, or use the provided laptop Docker image.

**On your laptop terminal, run:**

```bash
# Set the same domain ID as the Pi so they can talk!
export ROS_DOMAIN_ID=42

# See what the robot sees (the laser data):
ros2 topic echo /scan

# Watch the robot's speed commands:
ros2 topic echo /cmd_vel

# Record EVERYTHING (laser, speed, etc.) to a file on your laptop:
ros2 bag record -a

# Open the visual map (RViz2):
rviz2
```

> 📝 The bag file is saved on your **laptop**, NOT on the Pi — this saves the Pi's tiny memory!

---

## 🛠️ Wiring Diagram — L298N to Raspberry Pi

```
Raspberry Pi 4          L298N Motor Driver
(BCM Pin Numbers)       (Terminal Block)
─────────────────       ─────────────────

GPIO 12 (PWM)    ──►   ENA   (Left motor speed)
GPIO 23          ──►   IN1   (Left motor direction A)
GPIO 24          ──►   IN2   (Left motor direction B)

GPIO 13 (PWM)    ──►   ENB   (Right motor speed)
GPIO 27          ──►   IN3   (Right motor direction A)
GPIO 22          ──►   IN4   (Right motor direction B)

GND              ──►   GND   ← ⚠️ CRITICAL: shared ground!

                       OUT1/OUT2 ──► Left  motors (M1, M2)
                       OUT3/OUT4 ──► Right motors (M3, M4)
```

> ⚠️ **Golden Rule:** Always connect **GND (Ground) of the L298N** to **GND of the Pi**.  
> If you forget this, the motors will twitch and behave randomly!

---

## 🧠 How the Software Works (Simple Version)

```
       LAPTOP (Boss)                     RASPBERRY PI (Brain)
    ┌─────────────────┐               ┌────────────────────────────┐
    │                 │               │                            │
    │  RViz2 (Map)    │◄─── /scan ────┤  RPLidar Driver            │
    │  bag record     │               │      │                     │
    │                 │               │      ▼                     │
    │                 │     Wi-Fi     │  obstacle_avoider          │
    │                 │  ──────────►  │  (sees wall → publish      │
    │                 │               │   stop + turn to /cmd_vel) │
    │                 │               │      │                     │
    │                 │               │      ▼                     │
    │                 │               │  motor_controller          │
    │                 │               │  (/cmd_vel → L298N GPIO)   │
    │                 │               │      │                     │
    └─────────────────┘               │      ▼                     │
                                      │  ⚙️ Wheels spin!            │
                                      └────────────────────────────┘
```

**The obstacle avoider uses this logic:**

1. 🚗 **FORWARD** — Move forward at 0.2 m/s
2. 🚨 **OBSTACLE!** — If the laser sees something closer than **0.5 metres** ahead → STOP
3. 🔄 **ROTATE** — Spin 90 degrees in place
4. 🚗 **FORWARD** — Move forward again … repeat!

It's just like a robot vacuum cleaner! 🧹

---

## ⚠️ The Golden Safety Rules

1. **Watch your fingers!** Keep hands away from the wheels when the L298N is powered on.
2. **The "Wall" Rule:** The Lidar can see walls. Don't stand in front of the robot — it will automatically turn away!
3. **Heartbeat Safety:** If the software crashes or the Wi-Fi disconnects, the motors automatically STOP after **0.5 seconds**. The robot will never run away!
4. **Batteries first, Pi second:** Always power the L298N BEFORE turning on the Pi. And ALWAYS turn off the L298N BEFORE turning off the Pi.

---

## 🗂️ File Structure

```
SWARM-X/
├── docker-compose.yml              ← Starts both Pi services with one command
├── docker/
│   └── pi/
│       ├── Dockerfile              ← Builds the ARM64 ROS 2 Humble image
│       └── entrypoint.sh           ← Sets up ROS environment on start
└── ros2_ws/
    └── src/
        └── my_robot/
            ├── my_robot/
            │   ├── motor_controller.py    ← L298N GPIO driver (Task 2)
            │   └── obstacle_avoider.py    ← Lidar state machine (Task 3)
            └── launch/
                └── robot.launch.py        ← Starts both nodes (Task 4)
```

---

## 🔧 Build & Run (on the Raspberry Pi)

```bash
# 1. Clone the repo
git clone <your-repo-url> ~/SWARM-X
cd ~/SWARM-X

# 2. Build and start with Docker Compose
ROS_DOMAIN_ID=42 docker compose up --build

# ─── OR: Build the ROS workspace manually (without Docker) ───

# 3. Source ROS 2 Humble
source /opt/ros/humble/setup.bash

# 4. Build
cd ~/SWARM-X/ros2_ws
colcon build --symlink-install

# 5. Source the overlay
source install/setup.bash

# 6. Launch!
ros2 launch my_robot robot.launch.py
```

### Override Parameters

```bash
# Slow down the robot (default 0.2 m/s → 0.1 m/s)
ros2 launch my_robot robot.launch.py forward_speed:=0.1

# Stop earlier when obstacle is 0.8m away (default 0.5m)
ros2 launch my_robot robot.launch.py obstacle_distance:=0.8

# Use custom GPIO pins
ros2 launch my_robot robot.launch.py ena_pin:=18 in1_pin:=17 in2_pin:=27
```

---

## 🐧 Memory Tips for the 2 GB Pi

| Tip | Command / Action |
|-----|-----------------|
| Disable Desktop GUI | `sudo raspi-config` → System Options → Boot → CLI |
| Check free RAM | `free -h` |
| Check Docker memory | `docker stats` |
| Increase SHM for FastDDS | Already set to **128 MB** in `docker-compose.yml` |

---

## 🙋 Frequently Asked Questions

**Q: The motors don't spin — what do I check first?**  
A: Check the shared GND wire between the L298N and the Pi. This is the #1 most common mistake!

**Q: The laptop can't see the Pi's topics.**  
A: Make sure both are on the **same Wi-Fi network** AND both use `export ROS_DOMAIN_ID=42`.

**Q: The robot doesn't stop when it sees a wall.**  
A: Check that the lidar USB is connected and run `ros2 topic echo /scan` on the laptop to confirm data is flowing.

**Q: How do I change which GPIO pins are used?**  
A: Edit the `robot.launch.py` default values, OR pass them as arguments:  
`ros2 launch my_robot robot.launch.py ena_pin:=18`

---

*Built with ❤️ by the SWARM-X team — ROS 2 Humble | Raspberry Pi 4 | Docker*
