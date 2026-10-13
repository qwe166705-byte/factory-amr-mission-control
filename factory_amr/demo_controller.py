# Factory AMR Portfolio Demo Fault Controller

import os
import yaml

import rclpy

from rclpy.node import Node
from rclpy.parameter import (
    Parameter,
    parameter_value_to_python
)
from rclpy.parameter_client import AsyncParameterClient

from rclpy.qos import (
    QoSProfile,
    DurabilityPolicy,
    ReliabilityPolicy
)

from std_msgs.msg import String, Bool
from std_srvs.srv import Trigger, SetBool

from ament_index_python.packages import (
    get_package_share_directory
)


class DemoController(Node):

    DEMO_IDLE = 'IDLE'
    DEMO_ACTIVE = 'ACTIVE'
    DEMO_READY = 'READY_FOR_RESET'

    def __init__(self):

        super().__init__('demo_controller')

        # ============================================================
        # CONFIG
        # ============================================================

        self.load_config()

        # ============================================================
        # Runtime
        # ============================================================

        self.system_ready = False

        self.mission_state = 'BOOTING'

        self.demo_status = self.DEMO_IDLE

        # 防止 SAFE_IDLE / FINAL_ERROR
        # 重複觸發 Restore
        self.restoring = False

        self.original_navigation_timeout = None

        self.original_max_retries = None

        # ============================================================
        # QoS
        # ============================================================

        self.state_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL
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

        self.ready_sub = self.create_subscription(
            Bool,
            '/system_ready',
            self.system_ready_callback,
            10
        )

        # ============================================================
        # Demo Status Publisher
        # ============================================================

        self.demo_status_pub = self.create_publisher(
            String,
            '/demo_status',
            self.state_qos
        )

        # ============================================================
        # Demo Service
        # ============================================================

        self.demo_fault_srv = self.create_service(
            Trigger,
            '/demo_fault',
            self.demo_fault_callback
        )

        # ============================================================
        # Service Clients
        # ============================================================

        self.auto_client = self.create_client(
            SetBool,
            '/set_auto_dispatch'
        )

        # ============================================================
        # MissionManager Parameter Client
        # ============================================================

        self.parameter_client = AsyncParameterClient(
            self,
            '/mission_manager'
        )

        # Publisher 建立完成後才發布初始狀態
        self.publish_demo_status(
            self.DEMO_IDLE
        )

        self.get_logger().info(
            'Demo Controller ready.'
        )

        self.get_logger().info(
            f'Fault config: '
            f'timeout={self.fault_navigation_timeout:.1f}s, '
            f'max_retries={self.fault_max_retries}'
        )

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

            data = yaml.safe_load(
                file
            ) or {}

        demo = data.get(
            'demo',
            {}
        )

        self.fault_navigation_timeout = float(
            demo.get(
                'fault_navigation_timeout',
                2.0
            )
        )

        self.fault_max_retries = int(
            demo.get(
                'fault_max_retries',
                0
            )
        )

    # ============================================================
    # DEMO STATUS
    # ============================================================

    def publish_demo_status(
        self,
        status
    ):

        self.demo_status = status

        msg = String()

        msg.data = status

        self.demo_status_pub.publish(
            msg
        )

        self.get_logger().info(
            f'DEMO STATUS -> {status}'
        )

    # ============================================================
    # SYSTEM READY
    # ============================================================

    def system_ready_callback(
        self,
        msg
    ):

        self.system_ready = bool(
            msg.data
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
                f'DEMO WATCH: '
                f'{old_state} -> '
                f'{new_state}'
            )

        # ========================================================
        # RESET 完成
        #
        # SAFE_IDLE / FINAL_ERROR
        #     ↓
        # IDLE
        #
        # Demo 才真正結束
        # ========================================================

        if (
            new_state == 'IDLE'
            and old_state in (
                'SAFE_IDLE',
                'FINAL_ERROR'
            )
            and self.demo_status
            == self.DEMO_READY
        ):

            self.restoring = False

            self.original_navigation_timeout = None
            self.original_max_retries = None

            self.publish_demo_status(
                self.DEMO_IDLE
            )

            self.get_logger().info(
                'Demo reset completed.'
            )

            return

        # ========================================================
        # 沒有 Demo 正在執行
        # ========================================================

        if self.demo_status != self.DEMO_ACTIVE:

            return

        # ========================================================
        # Demo 執行過程
        #
        # Dashboard 一律顯示 ACTIVE
        # 詳細階段只寫 Log
        # ========================================================

        if new_state == 'NAVIGATING':

            self.get_logger().warning(
                'Demo phase: FAULT_ACTIVE'
            )

            return

        if new_state == 'RECOVERING':

            self.get_logger().warning(
                'Demo phase: RECOVERING'
            )

            return

        if new_state == 'RETURNING_HOME':

            self.get_logger().warning(
                'Demo phase: RETURNING_HOME'
            )

            return

        # ========================================================
        # 故障流程結束
        # 恢復正式 Parameter
        # ========================================================

        if new_state in (
            'SAFE_IDLE',
            'FINAL_ERROR'
        ):

            if not self.restoring:

                self.restore_original_parameters()

            return

    # ============================================================
    # DEMO FAULT SERVICE
    # ============================================================

    def demo_fault_callback(
        self,
        request,
        response
    ):

        # --------------------------------------------------------
        # Demo 正在進行
        # --------------------------------------------------------

        if self.demo_status == self.DEMO_ACTIVE:

            response.success = False

            response.message = (
                'Demo fault already active.'
            )

            return response

        # --------------------------------------------------------
        # Demo 已完成，但還沒 RESET
        # --------------------------------------------------------

        if self.demo_status == self.DEMO_READY:

            response.success = False

            response.message = (
                'Demo completed. '
                'RESET MISSION is required first.'
            )

            return response

        # --------------------------------------------------------
        # Robot System 未 Ready
        # --------------------------------------------------------

        if not self.system_ready:

            response.success = False

            response.message = (
                'Demo rejected: '
                'SYSTEM_READY is false.'
            )

            return response

        # --------------------------------------------------------
        # Robot 必須空閒
        # --------------------------------------------------------

        if self.mission_state != 'IDLE':

            response.success = False

            response.message = (
                f'Demo rejected: '
                f'mission_state='
                f'{self.mission_state}. '
                f'Robot must be IDLE.'
            )

            return response

        # --------------------------------------------------------
        # MissionManager Parameter Service
        # --------------------------------------------------------

        if not self.parameter_client.services_are_ready():

            self.parameter_client.wait_for_services(
                timeout_sec=1.0
            )

        if not self.parameter_client.services_are_ready():

            response.success = False

            response.message = (
                'MissionManager parameter '
                'service unavailable.'
            )

            return response

        # --------------------------------------------------------
        # Auto Dispatch Service
        # --------------------------------------------------------

        if not self.auto_client.wait_for_service(
            timeout_sec=1.0
        ):

            response.success = False

            response.message = (
                'Auto Dispatch service '
                'unavailable.'
            )

            return response

        # --------------------------------------------------------
        # 清掉上一次暫存
        # --------------------------------------------------------

        self.original_navigation_timeout = None

        self.original_max_retries = None

        self.restoring = False

        # --------------------------------------------------------
        # Demo 正式啟動
        # --------------------------------------------------------

        self.publish_demo_status(
            self.DEMO_ACTIVE
        )

        self.get_logger().info(
            'Demo phase: PAUSING_AUTO'
        )

        # 先關 AUTO，
        # 避免等待讀 Parameter 時突然派工。
        self.disable_auto()

        response.success = True

        response.message = (
            'Demo fault sequence started.'
        )

        return response

    # ============================================================
    # AUTO OFF
    # ============================================================

    def disable_auto(self):

        request = SetBool.Request()

        request.data = False

        future = self.auto_client.call_async(
            request
        )

        future.add_done_callback(
            self.disable_auto_callback
        )

    def disable_auto_callback(
        self,
        future
    ):

        try:

            result = future.result()

        except Exception as exc:

            self.abort_demo(
                f'AUTO_OFF_EXCEPTION:{exc}'
            )

            return

        if not result.success:

            self.abort_demo(
                f'AUTO_OFF_FAILED:'
                f'{result.message}'
            )

            return

        self.read_original_parameters()

    # ============================================================
    # READ ORIGINAL PARAMETERS
    # ============================================================

    def read_original_parameters(self):

        self.get_logger().info(
            'Demo phase: READING_PARAMETERS'
        )

        future = (
            self.parameter_client
            .get_parameters([
                'navigation_timeout',
                'max_retries'
            ])
        )

        future.add_done_callback(
            self.original_parameters_callback
        )

    def original_parameters_callback(
        self,
        future
    ):

        try:

            response = future.result()

            values = response.values

            if len(values) < 2:

                raise RuntimeError(
                    'Parameter response incomplete.'
                )

            navigation_timeout = (
                parameter_value_to_python(
                    values[0]
                )
            )

            max_retries = (
                parameter_value_to_python(
                    values[1]
                )
            )

            if navigation_timeout is None:

                raise RuntimeError(
                    'navigation_timeout is NOT_SET.'
                )

            if max_retries is None:

                raise RuntimeError(
                    'max_retries is NOT_SET.'
                )

            self.original_navigation_timeout = float(
                navigation_timeout
            )

            self.original_max_retries = int(
                max_retries
            )

        except Exception as exc:

            self.get_logger().error(
                f'Failed reading parameters: '
                f'{type(exc).__name__}: {exc}'
            )

            self.abort_demo(
                'READ_PARAMETER_FAILED'
            )

            return

        self.get_logger().info(
            f'Saved original parameters: '
            f'timeout='
            f'{self.original_navigation_timeout}, '
            f'max_retries='
            f'{self.original_max_retries}'
        )

        self.set_fault_parameters()

    # ============================================================
    # SET FAULT PARAMETERS
    # ============================================================

    def set_fault_parameters(self):

        self.get_logger().info(
            'Demo phase: SETTING_FAULT'
        )

        parameters = [

            Parameter(
                'navigation_timeout',
                Parameter.Type.DOUBLE,
                self.fault_navigation_timeout
            ),

            Parameter(
                'max_retries',
                Parameter.Type.INTEGER,
                self.fault_max_retries
            )

        ]

        future = (
            self.parameter_client
            .set_parameters(
                parameters
            )
        )

        future.add_done_callback(
            self.set_fault_parameters_callback
        )

    def set_fault_parameters_callback(
        self,
        future
    ):

        try:

            response = future.result()

            results = response.results

        except Exception as exc:

            self.abort_demo(
                f'SET_FAULT_EXCEPTION:{exc}'
            )

            return

        if not results:

            self.abort_demo(
                'SET_FAULT_EMPTY_RESPONSE'
            )

            return

        if not all(
            result.successful
            for result in results
        ):

            reasons = [

                result.reason

                for result in results

                if not result.successful

            ]

            self.get_logger().error(
                f'Fault parameter rejected: '
                f'{reasons}'
            )

            self.abort_demo(
                'SET_FAULT_PARAMETER_FAILED'
            )

            return

        self.get_logger().warning(
            'Demo fault parameters applied.'
        )

        self.enable_auto()

    # ============================================================
    # AUTO ON
    # ============================================================

    def enable_auto(self):

        self.get_logger().info(
            'Demo phase: ENABLING_AUTO'
        )

        request = SetBool.Request()

        request.data = True

        future = self.auto_client.call_async(
            request
        )

        future.add_done_callback(
            self.enable_auto_callback
        )

    def enable_auto_callback(
        self,
        future
    ):

        try:

            result = future.result()

        except Exception as exc:

            self.abort_demo(
                f'AUTO_ON_EXCEPTION:{exc}'
            )

            return

        if not result.success:

            self.abort_demo(
                f'AUTO_ON_FAILED:'
                f'{result.message}'
            )

            return

        self.get_logger().warning(
            'Demo fault armed. '
            'Next mission should fail.'
        )

    # ============================================================
    # RESTORE ORIGINAL PARAMETERS
    # ============================================================

    def restore_original_parameters(self):

        if (
            self.original_navigation_timeout
            is None
            or
            self.original_max_retries
            is None
        ):

            self.abort_demo(
                'NO_ORIGINAL_PARAMETERS'
            )

            return

        self.restoring = True

        self.get_logger().info(
            'Demo phase: RESTORING_PARAMETERS'
        )

        parameters = [

            Parameter(
                'navigation_timeout',
                Parameter.Type.DOUBLE,
                self.original_navigation_timeout
            ),

            Parameter(
                'max_retries',
                Parameter.Type.INTEGER,
                self.original_max_retries
            )

        ]

        future = (
            self.parameter_client
            .set_parameters(
                parameters
            )
        )

        future.add_done_callback(
            self.restore_parameters_callback
        )

    def restore_parameters_callback(
        self,
        future
    ):

        try:

            response = future.result()

            results = response.results

        except Exception as exc:

            self.get_logger().error(
                f'Failed restoring parameters: '
                f'{exc}'
            )

            self.abort_demo(
                'RESTORE_FAILED'
            )

            return

        if not results:

            self.abort_demo(
                'RESTORE_EMPTY_RESPONSE'
            )

            return

        if not all(
            result.successful
            for result in results
        ):

            reasons = [

                result.reason

                for result in results

                if not result.successful

            ]

            self.get_logger().error(
                f'Restore parameter rejected: '
                f'{reasons}'
            )

            self.abort_demo(
                'RESTORE_FAILED'
            )

            return

        self.restoring = False

        self.get_logger().info(
            f'Demo parameters restored: '
            f'timeout='
            f'{self.original_navigation_timeout}, '
            f'max_retries='
            f'{self.original_max_retries}'
        )

        # Demo 流程跑完，
        # 但仍需人工 RESET。
        self.publish_demo_status(
            self.DEMO_READY
        )

    # ============================================================
    # ABORT
    # ============================================================

    def abort_demo(
        self,
        reason
    ):

        self.restoring = False

        self.get_logger().error(
            f'Demo aborted: {reason}'
        )

        self.publish_demo_status(
            f'ERROR:{reason}'
        )


def main(args=None):

    rclpy.init(
        args=args
    )

    node = DemoController()

    try:

        rclpy.spin(
            node
        )

    except KeyboardInterrupt:

        pass

    finally:

        node.destroy_node()

        rclpy.shutdown()


if __name__ == '__main__':

    main()