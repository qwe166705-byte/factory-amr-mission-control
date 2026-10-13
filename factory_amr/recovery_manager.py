# 出現異常時回歸起點
import math

from action_msgs.msg import GoalStatus
from nav2_msgs.action import NavigateToPose

from factory_amr.mission_state import MissionState


class RecoveryManager:

    def __init__(
        self,
        node,
        nav_client,
        stations,
        home_station,
        recovery_delay,
        return_home_timeout,
        set_state_callback,
        publish_status_callback
    ):

        self.node = node

        self.nav_client = nav_client

        self.stations = stations

        self.home_station = home_station

        self.recovery_delay = recovery_delay

        self.return_home_timeout = (
            return_home_timeout
        )

        self.set_state = (
            set_state_callback
        )

        self.publish_status = (
            publish_status_callback
        )

        # Runtime
        self.mission_id = None
        self.failed_station = None
        self.failure_reason = None

        self.goal_handle = None

        self.recovery_timer = None
        self.timeout_timer = None

        self.timeout_triggered = False

    # ============================================================
    # START RECOVERY
    # ============================================================

    def start(
        self,
        mission_id,
        failed_station,
        reason
    ):

        self.cancel_all_timers()

        # 保存這次失敗任務資訊
        self.mission_id = mission_id
        self.failed_station = failed_station
        self.failure_reason = reason

        self.goal_handle = None
        self.timeout_triggered = False

        # 進入 Recovery 狀態
        self.set_state(
            MissionState.RECOVERING
        )

        self.publish_status(
            f'RECOVERING:'
            f'{mission_id}:'
            f'{failed_station}:'
            f'{reason}'
        )

        self.node.get_logger().warning(
            f'{mission_id}: '
            f'Recovery started. '
            f'Failed station={failed_station}, '
            f'Reason={reason}'
        )

        # 稍微等待，讓 Robot 停穩後再回 Home
        self.recovery_timer = (
            self.node.create_timer(
                self.recovery_delay,
                self.recovery_timer_callback
            )
        )

    # ============================================================
    # RECOVERY DELAY
    # ============================================================

    def recovery_timer_callback(self):

        if self.recovery_timer is not None:

            self.recovery_timer.cancel()
            self.recovery_timer = None

        self.start_return_home()

    # ============================================================
    # RETURN HOME
    # ============================================================

    def start_return_home(self):

        if self.home_station not in self.stations:

            self.enter_final_error(
                'HOME_STATION_NOT_FOUND'
            )
            return

        if not self.nav_client.wait_for_server(
            timeout_sec=2.0
        ):

            self.enter_final_error(
                'NAV2_UNAVAILABLE_DURING_RECOVERY'
            )
            return

        x, y, yaw = self.stations[
            self.home_station
        ]

        goal = NavigateToPose.Goal()

        goal.pose.header.frame_id = 'map'

        goal.pose.header.stamp = (
            self.node
            .get_clock()
            .now()
            .to_msg()
        )

        goal.pose.pose.position.x = x
        goal.pose.pose.position.y = y

        goal.pose.pose.orientation.z = (
            math.sin(yaw / 2.0)
        )

        goal.pose.pose.orientation.w = (
            math.cos(yaw / 2.0)
        )

        self.set_state(
            MissionState.RETURNING_HOME
        )

        self.publish_status(
            f'RETURN_HOME:'
            f'{self.home_station}:'
            f'{self.mission_id}'
        )

        self.node.get_logger().warning(
            f'{self.mission_id}: '
            f'Returning Home -> '
            f'{self.home_station} '
            f'(x={x:.2f}, '
            f'y={y:.2f}, '
            f'yaw={yaw:.2f})'
        )

        future = (
            self.nav_client.send_goal_async(
                goal,
                feedback_callback=(
                    self.feedback_callback
                )
            )
        )

        future.add_done_callback(
            self.goal_response_callback
        )

    # ============================================================
    # GOAL RESPONSE
    # ============================================================

    def goal_response_callback(
        self,
        future
    ):

        try:

            self.goal_handle = (
                future.result()
            )

        except Exception as exc:

            self.enter_final_error(
                f'RECOVERY_GOAL_EXCEPTION:{exc}'
            )
            return

        if not self.goal_handle.accepted:

            self.enter_final_error(
                'RETURN_HOME_REJECTED'
            )
            return

        self.node.get_logger().warning(
            'Return Home goal accepted.'
        )

        self.start_timeout_timer()

        result_future = (
            self.goal_handle
            .get_result_async()
        )

        result_future.add_done_callback(
            self.result_callback
        )

    # ============================================================
    # FEEDBACK
    # ============================================================

    def feedback_callback(
        self,
        feedback_msg
    ):

        distance = (
            feedback_msg
            .feedback
            .distance_remaining
        )

        self.node.get_logger().warning(
            f'RETURN HOME: '
            f'{distance:.2f} m remaining'
        )

    # ============================================================
    # TIMEOUT
    # ============================================================

    def start_timeout_timer(self):

        self.cancel_timeout_timer()

        self.timeout_timer = (
            self.node.create_timer(
                self.return_home_timeout,
                self.timeout_callback
            )
        )

    def cancel_timeout_timer(self):

        if self.timeout_timer is not None:

            self.timeout_timer.cancel()
            self.timeout_timer = None

    def timeout_callback(self):

        self.cancel_timeout_timer()

        if self.goal_handle is None:
            return

        self.timeout_triggered = True

        self.node.get_logger().error(
            f'Return Home TIMEOUT after '
            f'{self.return_home_timeout:.1f}s'
        )

        cancel_future = (
            self.goal_handle.cancel_goal_async()
        )

        cancel_future.add_done_callback(
            self.cancel_response_callback
        )

    # ============================================================
    # CANCEL RESPONSE
    # ============================================================

    def cancel_response_callback(
        self,
        future
    ):

        try:

            response = future.result()

        except Exception as exc:

            self.enter_final_error(
                f'RECOVERY_CANCEL_EXCEPTION:{exc}'
            )
            return

        if response.goals_canceling:

            self.node.get_logger().warning(
                'Return Home cancel accepted.'
            )

        else:

            self.node.get_logger().error(
                'Return Home cancel rejected.'
            )

    # ============================================================
    # RESULT
    # ============================================================

    def result_callback(
        self,
        future
    ):

        self.cancel_timeout_timer()

        try:

            wrapped_result = future.result()

        except Exception as exc:

            self.enter_final_error(
                f'RECOVERY_RESULT_EXCEPTION:{exc}'
            )
            return

        status = wrapped_result.status

        # ------------------------------
        # HOME SUCCESS
        # ------------------------------

        if status == GoalStatus.STATUS_SUCCEEDED:

            self.set_state(
                MissionState.SAFE_IDLE
            )

            self.publish_status(
                f'SAFE_IDLE:'
                f'{self.home_station}:'
                f'{self.mission_id}:'
                f'{self.failure_reason}'
            )

            self.node.get_logger().warning(
                f'{self.mission_id}: '
                f'Recovery completed. '
                f'Robot returned to '
                f'{self.home_station}.'
            )

            self.cleanup()

            return

        # ------------------------------
        # TIMEOUT CANCEL
        # ------------------------------

        if (
            status
            == GoalStatus.STATUS_CANCELED
            and self.timeout_triggered
        ):

            self.enter_final_error(
                'RETURN_HOME_TIMEOUT'
            )

            return

        # ------------------------------
        # ABORT
        # ------------------------------

        if status == GoalStatus.STATUS_ABORTED:

            self.enter_final_error(
                'RETURN_HOME_ABORTED'
            )

            return

        # ------------------------------
        # OTHER CANCEL
        # ------------------------------

        if status == GoalStatus.STATUS_CANCELED:

            self.enter_final_error(
                'RETURN_HOME_CANCELED'
            )

            return

        self.enter_final_error(
            f'RETURN_HOME_STATUS_{status}'
        )

    # ============================================================
    # FINAL ERROR
    # ============================================================

    def enter_final_error(
        self,
        reason
    ):

        self.cancel_all_timers()

        self.set_state(
            MissionState.FINAL_ERROR
        )

        self.publish_status(
            f'FINAL_ERROR:'
            f'{self.mission_id}:'
            f'{self.failed_station}:'
            f'{reason}'
        )

        self.node.get_logger().error(
            f'{self.mission_id}: '
            f'FINAL ERROR. '
            f'Recovery failed. '
            f'Reason={reason}'
        )

        self.cleanup()

    # ============================================================
    # CLEANUP
    # ============================================================

    def cancel_all_timers(self):

        if self.recovery_timer is not None:

            self.recovery_timer.cancel()
            self.recovery_timer = None

        self.cancel_timeout_timer()

    def cleanup(self):

        self.cancel_all_timers()

        self.goal_handle = None

        self.timeout_triggered = False



    # ============================================================
    # RESET
    # ============================================================

    def reset(self):

        self.cancel_all_timers()

        self.mission_id = None
        self.failed_station = None
        self.failure_reason = None

        self.goal_handle = None

        self.timeout_triggered = False

        self.node.get_logger().info(
            'RecoveryManager runtime cleared.'
        )