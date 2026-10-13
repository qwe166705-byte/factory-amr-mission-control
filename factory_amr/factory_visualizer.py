import os
import re
import yaml
import math

import rclpy
from rclpy.node import Node

from std_msgs.msg import String
from visualization_msgs.msg import Marker
from visualization_msgs.msg import MarkerArray

from ament_index_python.packages import get_package_share_directory


class FactoryVisualizer(Node):

    def __init__(self):
        super().__init__('factory_visualizer')

        self.stations = self.load_stations()

        self.current_target = None
        self.current_state = 'IDLE'
        self.current_mission_id = '-'

        self.marker_pub = self.create_publisher(
            MarkerArray,
            '/factory_amr/markers',
            10
        )

        self.create_subscription(
            String,
            '/station_request',
            self.station_request_callback,
            10
        )

        self.create_subscription(
            String,
            '/station_arrival',
            self.station_arrival_callback,
            10
        )

        self.create_subscription(
            String,
            '/mission_state',
            self.mission_state_callback,
            10
        )

        self.create_subscription(
            String,
            '/mission_status',
            self.mission_status_callback,
            10
        )

        self.timer = self.create_timer(
            0.5,
            self.publish_markers
        )

        self.get_logger().info(
            'Factory AMR Visualizer ready.'
        )

    def load_stations(self):

        package_share = get_package_share_directory(
            'factory_amr'
        )

        config_file = os.path.join(
            package_share,
            'config',
            'stations.yaml'
        )

        with open(config_file, 'r') as file:
            data = yaml.safe_load(file)

        return data.get('stations', {})

    def station_request_callback(self, msg):

        station = msg.data.strip()

        if station in self.stations:
            self.current_target = station

    def station_arrival_callback(self, msg):

        station = msg.data.strip()

        if station == self.current_target:
            self.current_target = None

    def mission_state_callback(self, msg):

        self.current_state = msg.data.strip()

    def mission_status_callback(self, msg):

        text = msg.data

        match = re.search(r'M\d{4}', text)

        if match:
            self.current_mission_id = match.group(0)

    def publish_markers(self):

        markers = MarkerArray()

        marker_id = 0

        # ==========================================
        # Station markers
        # ==========================================

        for name, config in self.stations.items():

            x = float(config['x'])
            y = float(config['y'])
            yaw = float(config.get('yaw', 0.0))

            # ======================================
            # Station cylinder
            # ======================================

            station_marker = Marker()

            station_marker.header.frame_id = 'map'
            station_marker.header.stamp = (
                self.get_clock().now().to_msg()
            )

            station_marker.ns = 'stations'
            station_marker.id = marker_id
            marker_id += 1

            station_marker.type = Marker.CYLINDER
            station_marker.action = Marker.ADD

            station_marker.pose.position.x = x
            station_marker.pose.position.y = y
            station_marker.pose.position.z = 0.08

            station_marker.pose.orientation.w = 1.0

            station_marker.scale.x = 0.30
            station_marker.scale.y = 0.30
            station_marker.scale.z = 0.16

            if name == self.current_target:

                station_marker.color.r = 1.0
                station_marker.color.g = 0.15
                station_marker.color.b = 0.10

            else:

                station_marker.color.r = 0.10
                station_marker.color.g = 0.85
                station_marker.color.b = 0.25

            station_marker.color.a = 0.9

            markers.markers.append(
                station_marker
            )

            # ======================================
            # Station label
            # ======================================

            text_marker = Marker()

            text_marker.header.frame_id = 'map'
            text_marker.header.stamp = (
                self.get_clock().now().to_msg()
            )

            text_marker.ns = 'station_labels'
            text_marker.id = marker_id
            marker_id += 1

            text_marker.type = Marker.TEXT_VIEW_FACING
            text_marker.action = Marker.ADD

            text_marker.pose.position.x = x
            text_marker.pose.position.y = y
            text_marker.pose.position.z = 0.45

            text_marker.pose.orientation.w = 1.0

            text_marker.scale.z = 0.22

            text_marker.color.r = 1.0
            text_marker.color.g = 1.0
            text_marker.color.b = 1.0
            text_marker.color.a = 1.0

            text_marker.text = name

            markers.markers.append(
                text_marker
            )

            # ======================================
            # Station orientation arrow
            # ======================================

            arrow_marker = Marker()

            arrow_marker.header.frame_id = 'map'
            arrow_marker.header.stamp = (
                self.get_clock().now().to_msg()
            )

            arrow_marker.ns = 'station_direction'
            arrow_marker.id = marker_id
            marker_id += 1

            arrow_marker.type = Marker.ARROW
            arrow_marker.action = Marker.ADD

            arrow_marker.pose.position.x = x
            arrow_marker.pose.position.y = y
            arrow_marker.pose.position.z = 0.18

            # yaw -> quaternion
            arrow_marker.pose.orientation.z = (
                math.sin(yaw / 2.0)
            )

            arrow_marker.pose.orientation.w = (
                math.cos(yaw / 2.0)
            )

            arrow_marker.scale.x = 0.55
            arrow_marker.scale.y = 0.08
            arrow_marker.scale.z = 0.08

            if name == self.current_target:

                arrow_marker.color.r = 1.0
                arrow_marker.color.g = 0.2
                arrow_marker.color.b = 0.1

            else:

                arrow_marker.color.r = 0.2
                arrow_marker.color.g = 0.7
                arrow_marker.color.b = 1.0

            arrow_marker.color.a = 1.0

            markers.markers.append(
                arrow_marker
            )

        # ==========================================
        # Mission information
        # ==========================================

        info_marker = Marker()

        info_marker.header.frame_id = 'map'
        info_marker.header.stamp = (
            self.get_clock().now().to_msg()
        )

        info_marker.ns = 'mission_info'
        info_marker.id = marker_id
        marker_id += 1

        info_marker.type = Marker.TEXT_VIEW_FACING
        info_marker.action = Marker.ADD

        info_marker.pose.position.x = 0.0
        info_marker.pose.position.y = 0.0
        info_marker.pose.position.z = 1.2

        info_marker.pose.orientation.w = 1.0

        info_marker.scale.z = 0.20

        info_marker.color.r = 1.0
        info_marker.color.g = 0.85
        info_marker.color.b = 0.15
        info_marker.color.a = 1.0

        target = (
            self.current_target
            if self.current_target is not None
            else '-'
        )

        info_marker.text = (
            f'Mission: {self.current_mission_id}\n'
            f'State: {self.current_state}\n'
            f'Target: {target}'
        )

        markers.markers.append(
            info_marker
        )

        # ==========================================
        # Publish 全部 Marker
        # ==========================================

        self.marker_pub.publish(
            markers
        )



def main(args=None):

    rclpy.init(args=args)

    node = FactoryVisualizer()

    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()