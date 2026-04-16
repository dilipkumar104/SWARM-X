import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'swarmx_hw'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        # Register package with ament index
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        # Package manifest
        ('share/' + package_name, ['package.xml']),
        # Launch files
        (os.path.join('share', package_name, 'launch'),
            glob(os.path.join('launch', '*launch.[pxy][yma]*'))),
        # Config files
        (os.path.join('share', package_name, 'config'),
            glob(os.path.join('config', '*'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='dilip',
    maintainer_email='dilip@todo.todo',
    description='SWARM-X Pi4 hardware nodes: L298N motors, HC-SR04 ultrasonic, MLX90614 thermal',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'motor_driver    = swarmx_hw.motor_driver:main',
            'ultrasonic_node = swarmx_hw.ultrasonic_node:main',
            'thermal_sensor  = swarmx_hw.thermal_sensor:main',
        ],
    },
)
