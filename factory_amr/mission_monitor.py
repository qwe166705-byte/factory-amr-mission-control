# Factory AMR Monitor / Mission History

import json
import math
import os
import re
import sqlite3
from datetime import datetime

import rclpy

from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    DurabilityPolicy,
    ReliabilityPolicy
)

from std_msgs.msg import String, Bool

from tf2_ros import (
    Buffer,
    TransformListener,
    TransformException
)


class MissionMonitor(Node):

    def __init__(self):

        super().__init__('mission_monitor')

        # ============================================================
        # Runtime Status
        # ============================================================

        self.system_ready = False
        self.auto_dispatch = False

        self.mission_state = 'BOOTING'

        self.tf_error_count = 0

        self.mission_id = None
        self.target = None

        self.retry_count = 0

        self.last_error = None

        self.x = None
        self.y = None
        self.yaw = None

        self.demo_status = 'IDLE'

        # ============================================================
        # QoS
        # ============================================================

        self.state_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL
        )

        # ============================================================
        # TF
        # ============================================================

        self.tf_buffer = Buffer()

        self.tf_listener = TransformListener(
            self.tf_buffer,
            self
        )

        # ============================================================
        # Subscribers
        # ============================================================

        self.state_sub = self.create_subscription(
            String,
            '/mission_state',
            self.mission_state_callback,
            self.state_qos
        )

        self.status_sub = self.create_subscription(
            String,
            '/mission_status',
            self.mission_status_callback,
            10
        )

        self.ready_sub = self.create_subscription(
            Bool,
            '/system_ready',
            self.system_ready_callback,
            10
        )

        self.auto_sub = self.create_subscription(
            Bool,
            '/auto_dispatch_status',
            self.auto_dispatch_callback,
            self.state_qos
        )

        self.demo_sub = self.create_subscription(
            String,
            '/demo_status',
            self.demo_status_callback,
            self.state_qos
        )

        # ============================================================
        # Consolidated System Status
        # ============================================================

        self.system_status_pub = self.create_publisher(
            String,
            '/factory_amr/system_status',
            self.state_qos
        )

        # ============================================================
        # SQLite
        # ============================================================

        self.init_database()

        # ============================================================
        # Timers
        # ============================================================

        self.tf_timer = self.create_timer(
            0.5,
            self.update_robot_pose
        )

        self.status_timer = self.create_timer(
            1.0,
            self.publish_system_status
        )

        self.get_logger().info(
            'Factory AMR Mission Monitor ready.'
        )

        self.get_logger().info(
            f'History DB: {self.db_path}'
        )

    # ============================================================
    # DATABASE
    # ============================================================

    def init_database(self):

        db_dir = os.path.expanduser(
            '~/.ros/factory_amr'
        )

        os.makedirs(
            db_dir,
            exist_ok=True
        )

        self.db_path = os.path.join(
            db_dir,
            'mission_history.db'
        )

        self.db = sqlite3.connect(
            self.db_path
        )

        self.db.execute(
            'PRAGMA journal_mode=WAL'
        )

        self.db.execute(
            'PRAGMA synchronous=NORMAL'
        )

        self.db.execute(
            '''
            CREATE TABLE IF NOT EXISTS mission_events
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                created_at TEXT NOT NULL,

                mission_id TEXT,

                state TEXT,

                target TEXT,

                retry_count INTEGER,

                system_ready INTEGER,

                auto_dispatch INTEGER,

                event_type TEXT,

                detail TEXT,

                x REAL,
                y REAL,
                yaw REAL
            )
            '''
        )

        self.db.commit()

    def record_event(
        self,
        event_type,
        detail=''
    ):

        created_at = (
            datetime
            .now()
            .astimezone()
            .isoformat(
                timespec='seconds'
            )
        )

        self.db.execute(
            '''
            INSERT INTO mission_events
            (
                created_at,
                mission_id,
                state,
                target,
                retry_count,
                system_ready,
                auto_dispatch,
                event_type,
                detail,
                x,
                y,
                yaw
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                created_at,
                self.mission_id,
                self.mission_state,
                self.target,
                self.retry_count,
                int(self.system_ready),
                int(self.auto_dispatch),
                event_type,
                detail,
                self.x,
                self.y,
                self.yaw
            )
        )

        self.db.commit()

    # ============================================================
    # SYSTEM READY
    # ============================================================

    def system_ready_callback(
        self,
        msg
    ):

        new_value = bool(
            msg.data
        )

        if new_value == self.system_ready:
            return

        self.system_ready = new_value

        self.record_event(
            'SYSTEM_READY',
            'TRUE'
            if new_value
            else 'FALSE'
        )

    # ============================================================
    # SYSTEM DEMO
    # ============================================================
    def demo_status_callback(
        self,
        msg
    ):

        new_status = msg.data.strip()

        if new_status == self.demo_status:
            return

        self.demo_status = new_status

        self.record_event(
            'DEMO_STATUS',
            new_status
        )

    # ============================================================
    # AUTO DISPATCH
    # ============================================================

    def auto_dispatch_callback(
        self,
        msg
    ):

        new_value = bool(
            msg.data
        )

        if new_value == self.auto_dispatch:
            return

        self.auto_dispatch = new_value

        self.record_event(
            'AUTO_DISPATCH',
            'ON'
            if new_value
            else 'OFF'
        )

    # ============================================================
    # MISSION STATE
    # ============================================================

    def mission_state_callback(
        self,
        msg
    ):

        new_state = (
            msg.data.strip()
        )

        if (
            new_state
            == self.mission_state
        ):
            return

        old_state = (
            self.mission_state
        )

        self.mission_state = (
            new_state
        )

        self.record_event(
            'STATE_CHANGE',
            f'{old_state}->{new_state}'
        )

    # ============================================================
    # MISSION STATUS
    # ============================================================

    def mission_status_callback(
        self,
        msg
    ):

        status = msg.data.strip()


        # --------------------------------------------------------
        # Mission ID
        # --------------------------------------------------------

        mission_match = re.search(
            r'M\d{4}',
            status
        )

        if mission_match:

            self.mission_id = (
                mission_match.group(0)
            )

        # --------------------------------------------------------
        # MOVING
        # MOVING:Station_A:M0001:ATTEMPT_1
        # --------------------------------------------------------

        if status.startswith(
            'MOVING:'
        ):

            parts = status.split(':')

            if len(parts) >= 2:

                self.target = (
                    parts[1]
                )

            # ATTEMPT_1 = 第一次，
            # retry_count 仍為 0
            if len(parts) >= 4:

                attempt_match = re.search(
                    r'ATTEMPT_(\d+)',
                    parts[3]
                )

                if attempt_match:

                    attempt = int(
                        attempt_match.group(1)
                    )

                    self.retry_count = max(
                        0,
                        attempt - 1
                    )

        # --------------------------------------------------------
        # RETRYING
        # RETRYING:M0001:Station_A:1/3:TIMEOUT
        # --------------------------------------------------------

        elif status.startswith(
            'RETRYING:'
        ):

            parts = status.split(':')

            if len(parts) >= 4:

                self.target = (
                    parts[2]
                )

                try:

                    self.retry_count = int(
                        parts[3]
                        .split('/')[0]
                    )

                except ValueError:

                    pass

            if len(parts) >= 5:

                self.last_error = (
                    parts[4]
                )

        # --------------------------------------------------------
        # TIMEOUT
        # TIMEOUT:Station_A
        # --------------------------------------------------------

        elif status.startswith(
            'TIMEOUT:'
        ):

            parts = status.split(':')

            if len(parts) >= 2:

                self.target = (
                    parts[1]
                )

            self.last_error = (
                'TIMEOUT'
            )

        # --------------------------------------------------------
        # RECOVERING
        # RECOVERING:M0001:Station_A:TIMEOUT
        # --------------------------------------------------------

        elif status.startswith(
            'RECOVERING:'
        ):

            parts = status.split(':')

            if len(parts) >= 3:

                self.target = (
                    parts[2]
                )

            if len(parts) >= 4:

                self.last_error = (
                    parts[3]
                )

        # --------------------------------------------------------
        # RETURN HOME
        # RETURN_HOME:Home:M0001
        # --------------------------------------------------------

        elif status.startswith(
            'RETURN_HOME:'
        ):

            parts = status.split(':')

            if len(parts) >= 2:

                self.target = (
                    parts[1]
                )

        # --------------------------------------------------------
        # SAFE IDLE
        # --------------------------------------------------------

        elif status.startswith(
            'SAFE_IDLE:'
        ):

            self.target = None

        # --------------------------------------------------------
        # FINAL ERROR
        # --------------------------------------------------------

        elif status.startswith(
            'FINAL_ERROR:'
        ):

            self.target = None

            parts = status.split(':')

            if len(parts) >= 4:

                self.last_error = (
                    parts[3]
                )

        # --------------------------------------------------------
        # ARRIVAL
        # --------------------------------------------------------

        elif status.startswith(
            'ARRIVED:'
        ):

            self.target = None

            self.retry_count = 0

            self.last_error = None

        # --------------------------------------------------------
        # RESET
        # RESET:M0001
        # --------------------------------------------------------

        elif status.startswith(
            'RESET:'
        ):

            self.target = None
            self.retry_count = 0
            self.last_error = None

        self.record_event(
            'MISSION_STATUS',
            status
        )

    # ============================================================
    # ROBOT POSE
    # ============================================================

    def update_robot_pose(self):

        try:

            transform = (
                self.tf_buffer.lookup_transform(
                    'map',
                    'base_link',
                    rclpy.time.Time(),
                    timeout=Duration(
                        seconds=0.2
                    )
                )
            )

        except TransformException as exc:

            self.tf_error_count += 1

            # 每 10 次印一次，避免洗版
            if self.tf_error_count % 10 == 0:

                self.get_logger().warning(
                    f'Robot pose TF unavailable: '
                    f'{exc}'
                )

            return

        # 成功後歸零
        self.tf_error_count = 0

        translation = (
            transform.transform.translation
        )

        rotation = (
            transform.transform.rotation
        )

        self.x = round(
            translation.x,
            3
        )

        self.y = round(
            translation.y,
            3
        )

        siny_cosp = (
            2.0
            * (
                rotation.w * rotation.z
                +
                rotation.x * rotation.y
            )
        )

        cosy_cosp = (
            1.0
            -
            2.0
            * (
                rotation.y * rotation.y
                +
                rotation.z * rotation.z
            )
        )

        self.yaw = round(
            math.atan2(
                siny_cosp,
                cosy_cosp
            ),
            3
        )

    # ============================================================
    # SYSTEM STATUS
    # ============================================================

    def publish_system_status(self):

        data = {

            'system_ready':
                self.system_ready,

            'auto_dispatch':
                self.auto_dispatch,

            'mission_id':
                self.mission_id,

            'state':
                self.mission_state,

            'target':
                self.target,

            'retry_count':
                self.retry_count,

            'last_error':
                self.last_error,

            'demo_status':
                self.demo_status,

            'pose': {

                'x':
                    self.x,

                'y':
                    self.y,

                'yaw':
                    self.yaw

            }

        }

        msg = String()

        msg.data = json.dumps(
            data,
            ensure_ascii=False
        )

        self.system_status_pub.publish(
            msg
        )

    # ============================================================
    # SHUTDOWN
    # ============================================================

    def destroy_node(self):

        try:

            self.db.commit()
            self.db.close()

        except Exception:

            pass

        super().destroy_node()


def main(args=None):

    rclpy.init(args=args)

    node = MissionMonitor()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        pass

    finally:

        node.destroy_node()

        rclpy.shutdown()


if __name__ == '__main__':

    main()