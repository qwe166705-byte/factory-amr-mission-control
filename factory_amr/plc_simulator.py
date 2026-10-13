# 假PLC訊號
# 假 PLC 訊號 / Auto Dispatch Controller

import os
import yaml

import rclpy

from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    DurabilityPolicy,
    ReliabilityPolicy
)

from std_msgs.msg import String, Bool
from std_srvs.srv import SetBool

from ament_index_python.packages import (
    get_package_share_directory
)


class PlcSimulator(Node):

    def __init__(self):

        super().__init__('plc_simulator')

        # ============================================================
        # CONFIG
        # ============================================================

        self.load_config()

        # ============================================================
        # RUNTIME
        # ============================================================

        self.system_ready = False

        self.mission_state = 'BOOTING'

        self.route_index = 0

        self.current_target = None

        self.dispatch_timer = None

        # ============================================================
        # QoS
        # ============================================================

        self.state_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL
        )

        # ============================================================
        # PUBLISHERS
        # ============================================================

        self.request_pub = self.create_publisher(
            String,
            'station_request',
            10
        )

        self.auto_status_pub = self.create_publisher(
            Bool,
            '/auto_dispatch_status',
            self.state_qos
        )

        # ============================================================
        # SUBSCRIBERS
        # ============================================================

        self.arrival_sub = self.create_subscription(
            String,
            'station_arrival',
            self.arrival_callback,
            10
        )

        self.status_sub = self.create_subscription(
            String,
            'mission_status',
            self.status_callback,
            10
        )

        self.ready_sub = self.create_subscription(
            Bool,
            '/system_ready',
            self.system_ready_callback,
            10
        )

        self.mission_state_sub = self.create_subscription(
            String,
            '/mission_state',
            self.mission_state_callback,
            self.state_qos
        )

        # ============================================================
        # SERVICES
        # ============================================================

        self.auto_dispatch_srv = self.create_service(
            SetBool,
            '/set_auto_dispatch',
            self.set_auto_dispatch_callback
        )

        # ============================================================
        # STARTUP LOG
        # ============================================================

        self.get_logger().info(
            'Fake PLC ready.'
        )

        self.get_logger().info(
            f'Route: {self.route}'
        )

        self.get_logger().info(
            f'Auto dispatch: '
            f'{"ON" if self.auto_dispatch_enabled else "OFF"}'
        )

        self.publish_auto_status()


    # ============================================================
    # CONFIG
    # ============================================================

    def load_config(self):

        package_share = (
            get_package_share_directory(
                'factory_amr'
            )
        )

        config_file = os.path.join(
            package_share,
            'config',
            'mission.yaml'
        )

        with open(
            config_file,
            'r'
        ) as file:

            data = yaml.safe_load(file) or {}

        config = data.get(
            'plc_simulator',
            {}
        )

        self.route = config.get(
            'route',
            []
        )

        self.ready_delay = float(
            config.get(
                'ready_delay',
                3.0
            )
        )

        self.dwell_seconds = float(
            config.get(
                'dwell_seconds',
                30.0
            )
        )

        self.auto_dispatch_enabled = bool(
            config.get(
                'auto_dispatch_enabled',
                False
            )
        )

        if not self.route:

            raise RuntimeError(
                'PLC route is empty.'
            )

        if self.ready_delay <= 0:

            raise RuntimeError(
                'ready_delay must be > 0.'
            )

        if self.dwell_seconds <= 0:

            raise RuntimeError(
                'dwell_seconds must be > 0.'
            )

    # ============================================================
    # SYSTEM READY
    # ============================================================

    def system_ready_callback(
        self,
        msg
    ):

        old_ready = self.system_ready

        self.system_ready = bool(
            msg.data
        )

        # --------------------------------------------------------
        # Ready -> False
        # --------------------------------------------------------

        if not self.system_ready:

            if old_ready:

                self.get_logger().warning(
                    'SYSTEM READY -> FALSE'
                )

            self.cancel_dispatch_timer()

            return

        # --------------------------------------------------------
        # False -> True
        # --------------------------------------------------------

        if not old_ready:

            self.get_logger().info(
                'SYSTEM READY -> TRUE'
            )

            self.try_schedule_dispatch(
                self.ready_delay
            )

    # ============================================================
    # MISSION STATE
    # ============================================================

    def mission_state_callback(
        self,
        msg
    ):

        new_state = msg.data.strip()

        old_state = self.mission_state

        self.mission_state = new_state

        if old_state != new_state:

            self.get_logger().info(
                f'MISSION STATE <- '
                f'{old_state} -> '
                f'{new_state}'
            )

        # --------------------------------------------------------
        # Recovery / Alarm 狀態
        # --------------------------------------------------------

        if new_state in (
            'RECOVERING',
            'RETURNING_HOME',
            'SAFE_IDLE',
            'FINAL_ERROR'
        ):

            self.cancel_dispatch_timer()

            return

        # --------------------------------------------------------
        # 回到 IDLE
        # --------------------------------------------------------

        if (
            new_state == 'IDLE'
            and old_state != 'IDLE'
        ):

            self.try_schedule_dispatch(
                self.ready_delay
            )

    # ============================================================
    # AUTO DISPATCH SERVICE
    # ============================================================
    def set_auto_dispatch_callback(
        self,
        request,
        response
    ):

        requested_state = bool(
            request.data
        )

        # ============================================================
        # AUTO ON
        # ============================================================

        if requested_state:

            self.auto_dispatch_enabled = True

            # 對外發布實際 AUTO 狀態
            self.publish_auto_status()

            self.get_logger().info(
                'AUTO DISPATCH -> ON'
            )

            self.try_schedule_dispatch(
                self.ready_delay
            )

            response.success = True

            if (
                self.system_ready
                and self.mission_state == 'IDLE'
            ):

                response.message = (
                    'Auto dispatch enabled. '
                    'Dispatch scheduled.'
                )

            else:

                response.message = (
                    'Auto dispatch enabled. '
                    'Waiting for SYSTEM_READY '
                    'and IDLE.'
                )

            return response

        # ============================================================
        # AUTO OFF
        # ============================================================

        self.auto_dispatch_enabled = False

        self.cancel_dispatch_timer()

        # 對外發布實際 AUTO 狀態
        self.publish_auto_status()

        self.get_logger().warning(
            'AUTO DISPATCH -> OFF'
        )

        response.success = True

        response.message = (
            'Auto dispatch disabled.'
        )

        return response

    # ============================================================
    # DISPATCH TIMER
    # ============================================================

    def cancel_dispatch_timer(self):

        if self.dispatch_timer is not None:

            self.dispatch_timer.cancel()

            self.dispatch_timer = None

    def try_schedule_dispatch(
        self,
        delay,
        replace=False
    ):

        # --------------------------------------------------------
        # Interlock
        # --------------------------------------------------------

        if not self.auto_dispatch_enabled:
            return

        if not self.system_ready:
            return

        if self.mission_state != 'IDLE':
            return

        # --------------------------------------------------------
        # 已存在 Timer
        # --------------------------------------------------------

        if self.dispatch_timer is not None:

            if not replace:
                return

            self.dispatch_timer.cancel()

            self.dispatch_timer = None

        self.get_logger().info(
            f'Next dispatch scheduled '
            f'in {delay:.1f} sec.'
        )

        self.dispatch_timer = (
            self.create_timer(
                delay,
                self.dispatch_timer_callback
            )
        )

    def dispatch_timer_callback(self):

        if self.dispatch_timer is not None:

            self.dispatch_timer.cancel()

            self.dispatch_timer = None

        self.dispatch_next_station()

    # ============================================================
    # DISPATCH
    # ============================================================

    def dispatch_next_station(self):

        # --------------------------------------------------------
        # 最後一道 Interlock
        # --------------------------------------------------------

        if not self.auto_dispatch_enabled:

            self.get_logger().warning(
                'Dispatch blocked: '
                'AUTO is OFF.'
            )

            return

        if not self.system_ready:

            self.get_logger().warning(
                'Dispatch blocked: '
                'SYSTEM_READY is FALSE.'
            )

            return

        if self.mission_state != 'IDLE':

            self.get_logger().warning(
                f'Dispatch blocked: '
                f'mission_state='
                f'{self.mission_state}'
            )

            return

        # --------------------------------------------------------
        # 正式派工
        # --------------------------------------------------------

        station = self.route[
            self.route_index
        ]

        self.current_target = station

        msg = String()

        msg.data = station

        self.request_pub.publish(
            msg
        )

        self.get_logger().info(
            f'PLC REQUEST -> {station}'
        )

        # 不在這裡增加 route_index
        # 必須 ARRIVED 才代表完成。

    def publish_auto_status(self):

        msg = Bool()

        msg.data = (
            self.auto_dispatch_enabled
        )

        self.auto_status_pub.publish(msg)

    # ============================================================
    # MISSION STATUS
    # ============================================================

    def status_callback(
        self,
        msg
    ):

        status = msg.data

        self.get_logger().info(
            f'MISSION STATUS <- {status}'
        )

        # mission_status 現在主要用於 Log。
        # 派工控制以 /mission_state 為準。

        if status.startswith(
            'RECOVERING:'
        ):

            self.get_logger().warning(
                'Robot recovery started.'
            )

        elif status.startswith(
            'RETURN_HOME:'
        ):

            self.get_logger().warning(
                'Robot is returning Home.'
            )

        elif status.startswith(
            'SAFE_IDLE:'
        ):

            self.get_logger().warning(
                'Robot entered SAFE_IDLE. '
                'Waiting for manual reset.'
            )

        elif status.startswith(
            'FINAL_ERROR:'
        ):

            self.get_logger().error(
                'Robot entered FINAL_ERROR. '
                'Manual intervention required.'
            )


    # ============================================================
    # ARRIVAL
    # ============================================================

    def arrival_callback(
        self,
        msg
    ):

        station = msg.data.strip()

        if self.current_target is None:

            self.get_logger().warning(
                f'Unexpected arrival: '
                f'{station}. '
                f'No current target.'
            )

            return

        if station != self.current_target:

            self.get_logger().warning(
                f'Unexpected arrival. '
                f'Expected='
                f'{self.current_target}, '
                f'Actual={station}'
            )

            return

        self.get_logger().info(
            f'PLC ARRIVAL <- {station}'
        )

        # --------------------------------------------------------
        # 任務完成後才切下一站
        # --------------------------------------------------------

        self.current_target = None

        self.route_index = (
            self.route_index + 1
        ) % len(self.route)

        next_station = self.route[
            self.route_index
        ]

        self.get_logger().info(
            f'Next station: '
            f'{next_station}. '
            f'Waiting '
            f'{self.dwell_seconds:.0f} sec.'
        )

        # Arrival dwell_seconds 優先於
        # mission_state IDLE 的 ready_delay。

        self.try_schedule_dispatch(
            self.dwell_seconds,
            replace=True
        )


def main(args=None):

    rclpy.init(args=args)

    node = PlcSimulator()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        pass

    finally:

        node.cancel_dispatch_timer()

        node.destroy_node()

        rclpy.shutdown()


if __name__ == '__main__':
    main()