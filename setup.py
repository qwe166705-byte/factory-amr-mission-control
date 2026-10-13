import os

from glob import glob
from setuptools import find_packages, setup


package_name = 'factory_amr'


setup(
    name=package_name,
    version='0.1.0',

    packages=find_packages(
        exclude=['test']
    ),

    data_files=[

        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name]
        ),

        (
            'share/' + package_name,
            ['package.xml']
        ),

        (
            os.path.join(
                'share',
                package_name,
                'launch'
            ),
            glob('launch/*.launch.py')
        ),

        (
            os.path.join(
                'share',
                package_name,
                'config'
            ),
            glob('config/*.yaml')
        ),

        (
            os.path.join(
                'share',
                package_name,
                'maps'
            ),
            glob('maps/*')
        ),

        (
            os.path.join(
                'share',
                package_name,
                'rviz'
            ),
            glob('rviz/*.rviz')
        ),

        (
            os.path.join(
                'share',
                package_name,
                'web'
            ),
            glob('web/*')
        ),
    ],

    install_requires=[
        'setuptools'
    ],

    zip_safe=True,

    maintainer='myuser',

    maintainer_email='chengjie859@gmail.com',

    description=(
        'ROS2 factory AMR mission control demo'
    ),

    license='Apache-2.0',

    entry_points={
        'console_scripts': [

            'mission_manager = '
            'factory_amr.mission_manager:main',

            'plc_simulator = '
            'factory_amr.plc_simulator:main',

            'factory_visualizer = '
            'factory_amr.factory_visualizer:main',

            'mission_monitor = '
            'factory_amr.mission_monitor:main',

            'dashboard_server = '
            'factory_amr.dashboard_server:main',

            'demo_controller = '
            'factory_amr.demo_controller:main',
        ],
    },
)