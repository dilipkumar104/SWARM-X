# 🤖 SWARM-X — ROS2 Chatter Publisher

A minimal ROS2 (Humble/Iron/Jazzy) Python workspace demonstrating a publisher node that broadcasts **"Hello Swarm-X"** to the `/chatter` topic every 1 second.

---

## 📁 Project Structure

```
ros2_ws/
├── .gitignore
├── README.md
└── src/
    └── my_robot/
        ├── package.xml              # ROS2 package manifest
        ├── setup.py                 # Python build + entry points
        ├── setup.cfg                # Colcon install paths
        ├── resource/
        │   └── my_robot             # Ament index marker
        ├── my_robot/
        │   ├── __init__.py
        │   └── chatter_publisher.py # ★ Publisher node
        └── test/
            ├── test_copyright.py
            ├── test_flake8.py
            └── test_pep257.py
```

---

## ✅ Prerequisites

| Requirement | Version |
|-------------|---------|
| Ubuntu      | 22.04 / 24.04 (or WSL2) |
| ROS2        | Humble / Iron / Jazzy |
| Python      | 3.10+ |
| colcon      | latest |

Make sure you have sourced your ROS2 installation:

```bash
source /opt/ros/<your-distro>/setup.bash
# Example: source /opt/ros/humble/setup.bash
```

---

## 🔨 Build

```bash
cd ~/ros2_ws
colcon build --packages-select my_robot
```

After building, source the workspace overlay:

```bash
source install/setup.bash
```

> **Tip:** Add this to your `~/.bashrc` so it's sourced automatically:
> ```bash
> echo "source ~/ros2_ws/install/setup.bash" >> ~/.bashrc
> ```

---

## 🚀 Run the Publisher Node

```bash
ros2 run my_robot chatter_publisher
```

**Expected output:**

```
[INFO] [1234567890.123] [chatter_publisher]: ChatterPublisher node started — publishing to /chatter
[INFO] [1234567890.123] [chatter_publisher]: Publishing: "Hello Swarm-X"
[INFO] [1234567891.123] [chatter_publisher]: Publishing: "Hello Swarm-X"
...
```

---

## 🔍 Verify the Topic

Open a **second terminal**, source the workspace, and echo the topic:

```bash
source ~/ros2_ws/install/setup.bash
ros2 topic echo /chatter
```

You should see:

```yaml
data: Hello Swarm-X
---
data: Hello Swarm-X
---
```

### Other Useful Commands

```bash
# List all active topics
ros2 topic list

# Check publishing frequency
ros2 topic hz /chatter

# Inspect topic type
ros2 topic info /chatter
```

---

## 📦 How It Works

1. **`ChatterPublisher`** is a ROS2 node (subclass of `rclpy.node.Node`).
2. On construction it creates a **publisher** on `/chatter` with message type `std_msgs/msg/String`.
3. A **timer** fires every **1.0 second**, calling `timer_callback()`.
4. Each callback builds a `String` message with `data = "Hello Swarm-X"` and publishes it.
5. `rclpy.spin()` keeps the node alive until you press `Ctrl+C`.

---

## 🧪 Run Tests

```bash
cd ~/ros2_ws
colcon test --packages-select my_robot
colcon test-result --verbose
```

---

## 📤 Push to GitHub

```bash
cd ~/ros2_ws
git init
git add .
git commit -m "feat: ROS2 chatter publisher — Hello Swarm-X"
git remote add origin https://github.com/<your-username>/<repo-name>.git
git branch -M main
git push -u origin main
```

---

## 📜 License

This project is open-source. Feel free to use and modify.

---

> Built with ❤️ for **SWARM-X**
