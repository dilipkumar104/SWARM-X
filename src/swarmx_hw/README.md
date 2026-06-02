# swarmx_hw — Legacy Hardware Package (ARCHIVED)

> **Status:** This package is archived. Its production nodes have been
> consolidated into the `my_robot` package.

## What Was Here

| Old Node | Replaced By | In Package |
|----------|-------------|------------|
| `motor_driver.py` | `motor_controller.py` | `my_robot` |
| `ultrasonic_node.py` | `ultrasonic_listener.py` + ESP32 micro-ROS | `my_robot` |
| `thermal_sensor.py` | `ir_sensor_node.py` | `my_robot` |

## What to Keep

The following files from this package contain **valuable reference material**
that does NOT exist elsewhere:

- **`SETUP_GUIDE.md`** — FastDDS Discovery Server, chrony clock sync, RPLidar
  udev rules, distributed Pi ↔ Laptop architecture
- **`config/fastdds_discovery_server.xml`** — Discovery Server XML for laptop
- **`config/fastdds_discovery_super_client.xml`** — Super Client XML for Pi
- **`config/slam_params.yaml`** — SLAM Toolbox config for namespaced robot

## Removal

Once you have backed up / referenced the above docs, this entire package
can be safely deleted:

```bash
rm -rf src/swarmx_hw
```

The active robot does not depend on this package.
