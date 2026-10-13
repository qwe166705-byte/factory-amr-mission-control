# 任務中心，基本都由這裏來決定該做甚麼
import math
import os
import yaml

import rclpy

from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.qos import (
    QoSProfile,
    DurabilityPolicy,
    ReliabilityPolicy
)

from std_msgs.msg import String, Bool
from std_srvs.srv import Trigger
from action_msgs.msg import GoalStatus
from nav2_msgs.action import NavigateToPose

from ament_index_python.packages import get_package_share_directory

from factory_amr.mission_state import MissionState
from factory_amr.recovery_manager import RecoveryManager

from tf2_ros import Buffer
from tf2_ros import TransformListener
from tf2_ros import TransformException


class MissionManager(Node):

    def __init__(self):
        super().__init__('mission_manager')

        self.stations = self.load_stations()
        self.load_mission_config()

        # ============================================================
        # Runtime Parameters
        # ============================================================

        self.declare_parameter(
            'navigation_timeout',
            self.navigation_timeout
        )

        self.declare_parameter(
            'max_retries',
            self.max_retries
        )

        self.declare_parameter(
            'retry_delay',
            self.retry_delay
        )

        # ==============================
        # ROS Interfaces
        # ==============================

        self.station_request_sub = self.create_subscription(
            String,
            'station_request',
            self.station_request_callback,
            10
        )

        self.arrival_pub = self.create_publisher(
            String,
            'station_arrival',
            10
        )

        self.status_pub = self.create_publisher(
            String,
            'mission_status',
            10
        )

        self.nav_client = ActionClient(
            self,
            NavigateToPose,
            'navigate_to_pose'
        )

        self.reset_mission_srv = self.create_service(
            Trigger,
            '/reset_mission',
            self.reset_mission_callback
        )

        state_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL
        )

        self.state_pub = self.create_publisher(
            String,
            'mission_state',
            state_qos
        )

        # ==============================
        # Mission Runtime
        # ==============================

        self.state = MissionState.BOOTING

        self.current_station = None
        self.current_mission_id = None

        self.mission_sequence = 0

        # retry_count 不包含第一次執行
        self.retry_count = 0

        self.goal_handle = None

        self.timeout_timer = None
        self.retry_timer = None

        # 如果是 Timeout 造成 Cancel，
        # Result callback 會知道真正原因是 TIMEOUT
        self.pending_failure_reason = None

        self.get_logger().info(
            'Factory AMR Mission Manager ready.'
        )

        self.get_logger().info(
            f'Loaded stations: {list(self.stations.keys())}'
        )

        self.get_logger().info(
            f'Navigation timeout={self.navigation_timeout:.1f}s, '
            f'max retries={self.max_retries}, '
            f'retry delay={self.retry_delay:.1f}s'
        )

        self.recovery_manager = RecoveryManager(
            node=self,
            nav_client=self.nav_client,
            stations=self.stations,
            home_station=self.home_station,
            recovery_delay=self.recovery_delay,
            return_home_timeout=(self.return_home_timeout),
            set_state_callback=self.set_state,
            publish_status_callback=(self.publish_status)
        )

        self.set_state(
            MissionState.IDLE
        )

        # ============================================================
        # System Ready / Localization
        # ============================================================

        self.system_ready = False

        self.tf_buffer = Buffer()

        self.tf_listener = TransformListener(
            self.tf_buffer,
            self
        )

        self.system_ready_pub = self.create_publisher(
            Bool,
            '/system_ready',
            10
        )

        self.ready_timer = self.create_timer(
            0.5,
            self.check_system_ready
        )

        self.ready_debug_count = 0

    # ============================================================
    # CONFIG
    # ============================================================

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

        raw_stations = data.get('stations', {})

        if not raw_stations:
            raise RuntimeError(
                'No stations configured.'
            )

        stations = {}

        for name, values in raw_stations.items():

            stations[name] = (
                float(values['x']),
                float(values['y']),
                float(values.get('yaw', 0.0))
            )

        return stations

    def load_mission_config(self):

        package_share = get_package_share_directory(
            'factory_amr'
        )

        config_file = os.path.join(
            package_share,
            'config',
            'mission.yaml'
        )

        with open(config_file, 'r') as file:
            data = yaml.safe_load(file)

        config = data.get(
            'mission_manager',
            {}
        )

        self.navigation_timeout = float(
            config.get(
                'navigation_timeout',
                60.0
            )
        )

        self.max_retries = int(
            config.get(
                'max_retries',
                3
            )
        )

        self.retry_delay = float(
            config.get(
                'retry_delay',
                5.0
            )
        )

        recovery = config.get(
            'recovery',
            {}
        )

        self.home_station = recovery.get(
            'home_station',
            'Home'
        )

        self.recovery_delay = float(
            recovery.get(
                'recovery_delay',
                3.0
            )
        )

        self.return_home_timeout = float(
            recovery.get(
                'return_home_timeout',
                60.0
            )
        )

        if self.home_station not in self.stations:

            raise RuntimeError(
                f'Home station not found: '
                f'{self.home_station}'
            )

    # ============================================================
    # 確認AMCL在正確位置
    # ============================================================

    def check_system_ready(self):

        # ==========================================
        # 1. Localization / TF Ready
        # ==========================================

        tf_ready = False

        try:

            self.tf_buffer.lookup_transform(
                'map',
                'base_link',
                rclpy.time.Time()
            )

            tf_ready = True

        except TransformException:

            tf_ready = False

        # ==========================================
        # 2. Nav2 Ready
        # ==========================================

        nav2_ready = (
            self.nav_client.server_is_ready()
        )

        # ==========================================
        # System Ready
        # ==========================================

        ready = (
            tf_ready
            and nav2_ready
        )

        if ready != self.system_ready:

            self.system_ready = ready

            if ready:

                self.get_logger().info(
                    'SYSTEM READY: '
                    'Localization TF + Nav2 ready.'
                )

            else:

                self.get_logger().warning(
                    'SYSTEM NOT READY.'
                )

        msg = Bool()
        msg.data = ready

        self.system_ready_pub.publish(msg)

        self.ready_debug_count += 1

        if self.ready_debug_count % 10 == 0:

            self.get_logger().info(
                f'READY CHECK: '
                f'TF={tf_ready}, '
                f'Nav2={nav2_ready}'
            )


    # ============================================================
    # STATE
    # ============================================================

    def set_state(self, new_state):

        old_state = self.state

        self.state = new_state

        self.get_logger().info(
            f'STATE: '
            f'{old_state.value} -> '
            f'{new_state.value}'
        )

        msg = String()
        msg.data = new_state.value

        self.state_pub.publish(msg)

    # ============================================================
    # NEW MISSION
    # ============================================================

    def station_request_callback(self, msg):

        # 出現定位前給訊號時 不要把Goal給Nav2
        if not self.system_ready:

            self.get_logger().warning(
                'Mission rejected: '
                'system localization is not ready.'
            )

            self.publish_status(
                'SYSTEM_NOT_READY'
            )

            return

        station = msg.data.strip()

        self.get_logger().info(
            f'Received mission request: {station}'
        )

        if station not in self.stations:

            self.get_logger().error(
                f'Unknown station: {station}'
            )

            self.publish_status(
                f'INVALID_STATION:{station}'
            )

            return

        # ERROR 也不允許接新任務
        if self.state != MissionState.IDLE:

            self.get_logger().warning(
                f'Cannot accept {station}. '
                f'Current state='
                f'{self.state.value}'
            )

            self.publish_status(
                f'BUSY:{self.current_station}'
            )

            return

        self.mission_sequence += 1

        self.current_mission_id = (
            f'M{self.mission_sequence:04d}'
        )

        self.current_station = station

        self.retry_count = 0

        self.pending_failure_reason = None

        self.set_state(
            MissionState.REQUESTED
        )

        self.get_logger().info(
            f'Mission '
            f'{self.current_mission_id} '
            f'created -> {station}'
        )

        self.start_navigation()


    # ==========================================
    # Reset清除狀態
    # ==========================================

    def reset_mission_callback(
        self,
        request,
        response
    ):

        # ==========================================
        # 只有安全停機 / 最終錯誤允許 Reset
        # ==========================================

        allowed_states = (
            MissionState.SAFE_IDLE,
            MissionState.FINAL_ERROR
        )

        if self.state not in allowed_states:

            response.success = False

            response.message = (
                f'Reset rejected. '
                f'Current state={self.state.value}'
            )

            self.get_logger().warning(
                response.message
            )

            return response

        # ==========================================
        # Robot 系統本身必須 Ready
        # ==========================================

        if not self.system_ready:

            response.success = False

            response.message = (
                'Reset rejected: '
                'robot system is not ready.'
            )

            self.get_logger().warning(
                response.message
            )

            return response

        old_mission_id = (
            self.current_mission_id
        )

        # ==========================================
        # 清除 Normal Mission runtime
        # ==========================================

        self.cancel_timeout_timer()

        if self.retry_timer is not None:

            self.retry_timer.cancel()
            self.retry_timer = None

        self.goal_handle = None

        self.current_station = None
        self.current_mission_id = None

        self.retry_count = 0

        self.pending_failure_reason = None

        # ==========================================
        # 清除 Recovery runtime
        # ==========================================

        self.recovery_manager.reset()

        # ==========================================
        # 回到 IDLE
        # ==========================================

        self.set_state(
            MissionState.IDLE
        )

        self.publish_status(
            f'RESET:{old_mission_id}'
        )

        response.success = True

        response.message = (
            f'Mission {old_mission_id} reset. '
            f'System returned to IDLE.'
        )

        self.get_logger().info(
            response.message
        )

        return response

    # ============================================================
    # NAVIGATION
    # ============================================================

    def start_navigation(self):

        station = self.current_station

        if station is None:
            return

        if not self.nav_client.wait_for_server(
            timeout_sec=2.0
        ):

            self.get_logger().error(
                'Nav2 NavigateToPose unavailable.'
            )

            self.handle_failure(
                'NAV2_UNAVAILABLE'
            )

            return

        x, y, yaw = self.stations[station]

        goal = NavigateToPose.Goal()

        goal.pose.header.frame_id = 'map'

        goal.pose.header.stamp = (
            self.get_clock().now().to_msg()
        )

        goal.pose.pose.position.x = x
        goal.pose.pose.position.y = y

        goal.pose.pose.orientation.z = (
            math.sin(yaw / 2.0)
        )

        goal.pose.pose.orientation.w = (
            math.cos(yaw / 2.0)
        )

        attempt = self.retry_count + 1

        self.set_state(
            MissionState.NAVIGATING
        )

        self.publish_status(
            f'MOVING:{station}:'
            f'{self.current_mission_id}:'
            f'ATTEMPT_{attempt}'
        )

        self.get_logger().info(
            f'{self.current_mission_id}: '
            f'Navigate -> {station} '
            f'Attempt={attempt} '
            f'(x={x:.2f}, '
            f'y={y:.2f}, '
            f'yaw={yaw:.2f})'
        )

        future = self.nav_client.send_goal_async(
            goal,
            feedback_callback=self.feedback_callback
        )

        future.add_done_callback(
            self.goal_response_callback
        )

    def goal_response_callback(self, future):

        try:

            self.goal_handle = future.result()

        except Exception as exc:

            self.get_logger().error(
                f'Goal request exception: {exc}'
            )

            self.handle_failure(
                'GOAL_REQUEST_ERROR'
            )

            return

        if not self.goal_handle.accepted:

            self.get_logger().error(
                'Navigation goal rejected.'
            )

            self.handle_failure(
                'GOAL_REJECTED'
            )

            return

        self.get_logger().info(
            f'{self.current_mission_id}: '
            'Navigation goal accepted.'
        )

        # Goal accepted 後才開始 Timeout
        self.start_timeout_timer()

        result_future = (
            self.goal_handle.get_result_async()
        )

        result_future.add_done_callback(
            self.result_callback
        )

    def feedback_callback(self, feedback_msg):

        distance = (
            feedback_msg.feedback.distance_remaining
        )

        self.get_logger().info(
            f'{self.current_mission_id}: '
            f'{self.current_station} '
            f'{distance:.2f} m remaining'
        )

    # ============================================================
    # TIMEOUT
    # ============================================================

    def start_timeout_timer(self):

        self.cancel_timeout_timer()

        self.active_navigation_timeout = float(
            self.get_parameter(
                'navigation_timeout'
            ).value
        )

        self.timeout_timer = self.create_timer(
            self.active_navigation_timeout,
            self.navigation_timeout_callback
        )

        self.get_logger().info(
            f'Navigation watchdog started: '
            f'{self.active_navigation_timeout:.1f}s'
        )

    def cancel_timeout_timer(self):

        if self.timeout_timer is not None:

            self.timeout_timer.cancel()
            self.timeout_timer = None

    def navigation_timeout_callback(self):

        # create_timer 是週期 Timer，
        # Timeout 發生第一時間先取消自己
        self.cancel_timeout_timer()

        if (
            self.state != MissionState.NAVIGATING
            or self.goal_handle is None
        ):
            return

        self.pending_failure_reason = 'TIMEOUT'

        self.get_logger().error(
            f'{self.current_mission_id}: '
            f'Navigation TIMEOUT after '
            f'{self.active_navigation_timeout:.1f}s'
        )

        self.publish_status(
            f'TIMEOUT:{self.current_station}'
        )

        self.get_logger().warning(
            'Canceling Nav2 goal...'
        )

        cancel_future = (
            self.goal_handle.cancel_goal_async()
        )

        cancel_future.add_done_callback(
            self.cancel_response_callback
        )

    def cancel_response_callback(self, future):

        try:

            response = future.result()

        except Exception as exc:

            self.get_logger().error(
                f'Cancel request failed: {exc}'
            )

            return

        if len(response.goals_canceling) > 0:

            self.get_logger().warning(
                'Nav2 goal cancel accepted.'
            )

        else:

            self.get_logger().warning(
                'Nav2 goal cancel was not accepted.'
            )

    # ============================================================
    # RESULT
    # ============================================================

    def result_callback(self, future):

        self.cancel_timeout_timer()

        try:
            wrapped_result = future.result()
        except Exception as exc:
            self.get_logger().error(f'Navigation result exception: 'f'{exc}')
            self.handle_failure('RESULT_EXCEPTION')
            return

        status = wrapped_result.status

        # ------------------------------
        # SUCCESS
        # ------------------------------

        if status == GoalStatus.STATUS_SUCCEEDED:

            self.pending_failure_reason = None

            self.set_state(
                MissionState.ARRIVED
            )

            station = self.current_station

            self.get_logger().info(
                f'{self.current_mission_id}: '
                f'ARRIVED -> {station}'
            )

            msg = String()
            msg.data = station

            self.arrival_pub.publish(msg)

            self.publish_status(
                f'ARRIVED:{station}'
            )

            self.finish_success()

            return

        # ------------------------------
        # ABORTED
        # ------------------------------

        if status == GoalStatus.STATUS_ABORTED:

            self.handle_failure(
                'ABORTED'
            )

            return

        # ------------------------------
        # CANCELED
        # ------------------------------

        if status == GoalStatus.STATUS_CANCELED:

            reason = (
                self.pending_failure_reason
                or 'CANCELED'
            )

            self.pending_failure_reason = None

            self.handle_failure(
                reason
            )

            return

        # ------------------------------
        # UNKNOWN
        # ------------------------------

        self.handle_failure(
            f'NAV2_STATUS_{status}'
        )

    # ============================================================
    # ERROR / RECOVERY
    # ============================================================

    def handle_failure(self, reason):

        self.cancel_timeout_timer()

        self.goal_handle = None

        max_retries = int(
            self.get_parameter(
                'max_retries'
            ).value
        )

        if self.retry_count < max_retries:

            self.retry_count += 1

            self.set_state(
                MissionState.RETRYING
            )

            self.publish_status(
                f'RETRYING:'
                f'{self.current_mission_id}:'
                f'{self.current_station}:'
                f'{self.retry_count}/'
                f'{max_retries}:'
                f'{reason}'
            )

            self.get_logger().warning(
                f'{self.current_mission_id}: '
                f'{reason}. '
                f'Retry '
                f'{self.retry_count}/'
                f'{max_retries}'
            )

            self.schedule_retry()

            return

        self.get_logger().error(
            f'{self.current_mission_id}: '
            f'Normal navigation failed. '
            f'Starting recovery.'
        )

        self.recovery_manager.start(
            mission_id=self.current_mission_id,
            failed_station=self.current_station,
            reason=reason
        )


    def schedule_retry(self):

        if self.retry_timer is not None:

            self.retry_timer.cancel()

        retry_delay = float(
            self.get_parameter(
                'retry_delay'
            ).value
        )

        self.retry_timer = self.create_timer(
            retry_delay,
            self.retry_timer_callback
        )

    def retry_timer_callback(self):

        if self.retry_timer is not None:
            self.retry_timer.cancel()
            self.retry_timer = None

        if self.state != MissionState.RETRYING:

            self.get_logger().warning(
                f'Retry ignored. '
                f'Current state={self.state.value}'
            )

            return

        self.set_state(
            MissionState.REQUESTED
        )

        self.get_logger().info(
            f'{self.current_mission_id}: '
            f'Retrying '
            f'{self.current_station}'
        )

        self.start_navigation()

    # ============================================================
    # SUCCESS FINISH
    # ============================================================

    def finish_success(self):

        mission_id = self.current_mission_id

        self.get_logger().info(
            f'Mission {mission_id} '
            'finished successfully.'
        )

        self.current_station = None
        self.current_mission_id = None
        self.goal_handle = None

        self.retry_count = 0
        self.pending_failure_reason = None

        self.set_state(
            MissionState.IDLE
        )

    # ============================================================
    # STATUS
    # ============================================================

    def publish_status(self, text):

        msg = String()
        msg.data = text

        self.status_pub.publish(msg)


def main(args=None):

    rclpy.init(args=args)

    node = MissionManager()

    rclpy.spin(node)

    node.destroy_node()

    rclpy.shutdown()


if __name__ == '__main__':
    main()