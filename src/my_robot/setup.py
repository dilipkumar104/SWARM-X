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
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='dilip',
    maintainer_email='dilip@todo.todo',
    description='A simple ROS2 Python publisher that sends "Hello Swarm-X" to /chatter',
    license='Apache-2.0',
    tests_require=['pytest'],

    # ── Entry Points ──────────────────────────────────────────────
    # This is how ROS2 discovers your node.
    # Format:  'executable_name = package.module:function'
    #
    # After building, you can run:
    #   ros2 run my_robot chatter_publisher
    # ──────────────────────────────────────────────────────────────
    entry_points={
        'console_scripts': [
            'chatter_publisher = my_robot.chatter_publisher:main',
        ],
    },
)
