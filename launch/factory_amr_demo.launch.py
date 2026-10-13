import os

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

from launch_ros.actions import Node

from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    # ============================================================
    # Package Paths
    # ============================================================

    factory_amr_share = get_package_share_directory(
        'factory_amr'
    )

    nav2_bringup_share = get_package_share_directory(
        'nav2_bringup'
    )

    map_file = os.path.join(
        factory_amr_share,
        'maps',
        'factory_map.yaml'
    )

    nav2_params_file = os.path.join(
        factory_amr_share,
        'config',
        'nav2_params.yaml'
    )

    factory_amr_share = get_package_share_directory(
        'factory_amr'
    )

    rviz_config_file = os.path.join(
        factory_amr_share,
        'rviz',
        'factory_amr.rviz'
    )

    # ============================================================
    # Nav2 + Gazebo + RViz
    # ============================================================

    nav2_simulation = IncludeLaunchDescription(

        PythonLaunchDescriptionSource(

            os.path.join(
                nav2_bringup_share,
                'launch',
                'tb3_simulation_launch.py'
            )

        ),

        launch_arguments={

            'slam': 'False',

            'map': map_file,

            'params_file': nav2_params_file,

            'use_sim_time': 'True',

            'autostart': 'True',

            'use_simulator': 'True',

            'use_robot_state_pub': 'True',

            'use_rviz': 'True',

            'headless': 'False',

            'rviz_config_file':
                rviz_config_file,

        }.items()

    )

    # ============================================================
    # Mission Manager
    # ============================================================

    mission_manager = Node(

        package='factory_amr',

        executable='mission_manager',

        name='mission_manager',

        output='screen',

        parameters=[
            {
                'use_sim_time': True
            }
        ]

    )

    # ============================================================
    # Fake PLC / Auto Dispatch
    # ============================================================

    plc_simulator = Node(

        package='factory_amr',

        executable='plc_simulator',

        name='plc_simulator',

        output='screen',

        parameters=[
            {
                'use_sim_time': True
            }
        ]

    )

    # ============================================================
    # RViz Factory Visualization
    # ============================================================

    factory_visualizer = Node(

        package='factory_amr',

        executable='factory_visualizer',

        name='factory_visualizer',

        output='screen',

        parameters=[
            {
                'use_sim_time': True
            }
        ]

    )

    # ============================================================
    # Mission Monitor / SQLite History
    # ============================================================

    mission_monitor = Node(

        package='factory_amr',

        executable='mission_monitor',

        name='mission_monitor',

        output='screen',

        parameters=[
            {
                'use_sim_time': True
            }
        ]

    )

    # ============================================================
    # Web Dashboard
    # ============================================================

    dashboard_server = Node(
        package='factory_amr',
        executable='dashboard_server',
        name='dashboard_bridge',
        output='screen'
    )

    demo_controller = Node(
        package='factory_amr',
        executable='demo_controller',
        name='demo_controller',
        output='screen'
    )

    # ============================================================
    # Launch
    # ============================================================

    return LaunchDescription([

        nav2_simulation,

        mission_manager,

        plc_simulator,

        factory_visualizer,

        mission_monitor,

        demo_controller,

        dashboard_server,

    ])