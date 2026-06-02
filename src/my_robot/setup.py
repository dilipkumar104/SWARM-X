import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'my_robot'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        # Register package with ament index
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        # Install package.xml
        ('share/' + package_name, ['package.xml']),
        # Install launch files
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        # Install URDF
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*')),
        # Install config files (SLAM, Nav2)
        (os.path.join('share', package_name, 'config'), glob('config/*')),
        # Install RViz2 config
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='dilip',
    maintainer_email='dilip@todo.todo',
    description='SWARM-X ROS2 — single-robot stack: LiDAR, HC-SR04, MLX90614, MPU6050, L298N, SLAM, Nav2',
    license='Apache-2.0',
    tests_require=['pytest'],

    # ── Entry Points ──────────────────────────────────────────────
    # This is how ROS2 discovers your nodes.
    # Format:  'executable_name = package.module:function'
    #
    # After building, you can run any production node:
    #   ros2 run my_robot motor_controller
    #   ros2 run my_robot obstacle_avoider
    #   ros2 run my_robot ir_sensor_node
    #   ros2 run my_robot imu_node
    #   ros2 run my_robot ultrasonic_listener
    # ──────────────────────────────────────────────────────────────
    entry_points={
        'console_scripts': [
            # ── Production nodes (active robot pipeline) ────────────
            'motor_controller      = my_robot.motor_controller:main',
            'obstacle_avoider      = my_robot.obstacle_avoider:main',
            'ultrasonic_listener   = my_robot.ultrasonic_listener:main',
            'ir_sensor_node        = my_robot.ir_sensor_node:main',
            'imu_node              = my_robot.imu_node:main',
            'odometry_node         = my_robot.odometry_node:main',
            'diagnostics_node      = my_robot.diagnostics_node:main',
            'system_monitor        = my_robot.system_monitor:main',
            'battery_monitor       = my_robot.battery_monitor:main',
            # ── Demo / test utilities (not part of robot pipeline) ──
            'chatter_publisher     = my_robot.chatter_publisher:main',
            'ultrasonic_simulator  = my_robot.ultrasonic_simulator:main',
            'swarm_publisher       = my_robot.swarm_publisher:main',
            'swarm_subscriber      = my_robot.swarm_subscriber:main',
            'swarm_multi_publisher = my_robot.swarm_multi_publisher:main',
            # ── Future (AMG8833 thermal camera) ─────────────────────
            'thermal_node          = my_robot.thermal_node:main',
        ],
    },
)
