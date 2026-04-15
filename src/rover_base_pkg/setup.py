import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'rover_base_pkg'

setup(
    name=package_name,
    version='0.1.0',
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
    ],
    install_requires=['setuptools', 'pyserial'],
    zip_safe=True,
    maintainer='developer',
    maintainer_email='developer@example.com',
    description='Minimal rover base: ultrasonic sensor + DC motor control via ESP32 UART',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'ultrasonic_node = rover_base_pkg.ultrasonic_node:main',
            'motor_cmd_node = rover_base_pkg.motor_cmd_node:main',
        ],
    },
)
