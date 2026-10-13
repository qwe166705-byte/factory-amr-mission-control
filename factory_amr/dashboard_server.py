import json
import os
import sqlite3
import threading
import time

import rclpy

from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import (
    QoSProfile,
    DurabilityPolicy,
    ReliabilityPolicy
)

from std_msgs.msg import String
from std_srvs.srv import SetBool, Trigger

from ament_index_python.packages import (
    get_package_share_directory
)

from flask import (
    Flask,
    jsonify,
    request,
    send_file
)


class DashboardBridge(Node):

    def __init__(self):

        super().__init__('dashboard_bridge')

        # ============================================================
        # Runtime
        # ============================================================

        self.status_lock = threading.Lock()

        self.latest_status = {
            'system_ready': False,
            'auto_dispatch': False,
            'mission_id': None,
            'state': 'UNKNOWN',
            'target': None,
            'retry_count': 0,
            'last_error': None,
            'pose': {
                'x': None,
                'y': None,
                'yaw': None
            }
        }

        self.last_status_time = None

        # ============================================================
        # QoS
        # ============================================================

        state_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL
        )

        # ============================================================
        # ROS Subscriber
        # ============================================================

        self.status_sub = self.create_subscription(
            String,
            '/factory_amr/system_status',
            self.status_callback,
            state_qos
        )

        # ============================================================
        # ROS Service Clients
        # ============================================================

        self.auto_client = self.create_client(
            SetBool,
            '/set_auto_dispatch'
        )

        self.reset_client = self.create_client(
            Trigger,
            '/reset_mission'
        )

        self.demo_fault_client = self.create_client(
            Trigger,
            '/demo_fault'
        )

        # ============================================================
        # Files
        # ============================================================

        package_share = get_package_share_directory(
            'factory_amr'
        )

        self.dashboard_file = os.path.join(
            package_share,
            'web',
            'dashboard.html'
        )

        self.db_path = os.path.expanduser(
            '~/.ros/factory_amr/mission_history.db'
        )

        self.get_logger().info(
            'Dashboard Bridge ready.'
        )

    # ============================================================
    # System Status
    # ============================================================

    def status_callback(self, msg):

        try:

            data = json.loads(
                msg.data
            )

        except Exception as exc:

            self.get_logger().error(
                f'Invalid system status JSON: {exc}'
            )

            return

        with self.status_lock:

            self.latest_status = data
            self.last_status_time = time.monotonic()

    def get_status(self):

        with self.status_lock:

            # 做 copy，避免 Flask thread
            # 剛好碰上 ROS callback 修改資料
            data = json.loads(
                json.dumps(
                    self.latest_status
                )
            )

            last_status_time = (
                self.last_status_time
            )

        online = (
            last_status_time is not None
            and
            (
                time.monotonic()
                - last_status_time
            ) < 3.0
        )

        data['monitor_online'] = online

        return data

    # ============================================================
    # History
    # ============================================================

    def get_history(
        self,
        limit=50
    ):

        if not os.path.exists(
            self.db_path
        ):

            return []

        limit = max(
            1,
            min(
                int(limit),
                200
            )
        )

        conn = sqlite3.connect(
            self.db_path,
            timeout=2.0
        )

        conn.row_factory = sqlite3.Row

        try:

            rows = conn.execute(
                '''
                SELECT
                    id,
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
                FROM mission_events
                ORDER BY id DESC
                LIMIT ?
                ''',
                (limit,)
            ).fetchall()

            return [
                dict(row)
                for row in rows
            ]

        finally:

            conn.close()

    # ============================================================
    # Service Helper
    # ============================================================

    def call_service(
        self,
        client,
        service_request,
        timeout=3.0
    ):

        if not client.wait_for_service(
            timeout_sec=1.0
        ):

            return (
                False,
                'Service unavailable.'
            )

        event = threading.Event()

        result_box = {}

        future = client.call_async(
            service_request
        )

        def done_callback(done_future):

            try:

                result_box['result'] = (
                    done_future.result()
                )

            except Exception as exc:

                result_box['error'] = str(exc)

            finally:

                event.set()

        future.add_done_callback(
            done_callback
        )

        if not event.wait(timeout):

            return (
                False,
                'Service call timeout.'
            )

        if 'error' in result_box:

            return (
                False,
                result_box['error']
            )

        return (
            True,
            result_box['result']
        )

    # ============================================================
    # AUTO
    # ============================================================

    def set_auto_dispatch(
        self,
        enabled
    ):

        req = SetBool.Request()

        req.data = bool(
            enabled
        )

        ok, result = self.call_service(
            self.auto_client,
            req
        )

        if not ok:

            return {
                'success': False,
                'message': str(result)
            }

        return {
            'success': bool(
                result.success
            ),
            'message': result.message
        }

    # ============================================================
    # Reset
    # ============================================================

    def reset_mission(self):

        req = Trigger.Request()

        ok, result = self.call_service(
            self.reset_client,
            req
        )

        if not ok:

            return {
                'success': False,
                'message': str(result)
            }

        return {
            'success': bool(
                result.success
            ),
            'message': result.message
        }

    def trigger_demo_fault(self):

        req = Trigger.Request()

        ok, result = self.call_service(
            self.demo_fault_client,
            req
        )

        if not ok:

            return {
                'success': False,
                'message': str(result)
            }

        return {
            'success': bool(
                result.success
            ),
            'message': result.message
        }

def create_app(bridge):

    app = Flask(__name__)

    # ============================================================
    # UI
    # ============================================================

    @app.route('/')
    def dashboard():

        return send_file(
            bridge.dashboard_file
        )

    # ============================================================
    # API - Status
    # ============================================================

    @app.route(
        '/api/status',
        methods=['GET']
    )
    def api_status():

        return jsonify(
            bridge.get_status()
        )

    # ============================================================
    # API - History
    # ============================================================

    @app.route(
        '/api/history',
        methods=['GET']
    )
    def api_history():

        limit = request.args.get(
            'limit',
            50
        )

        try:

            limit = int(limit)

        except ValueError:

            limit = 50

        return jsonify(
            bridge.get_history(
                limit
            )
        )

    # ============================================================
    # API - AUTO
    # ============================================================

    @app.route(
        '/api/auto',
        methods=['POST']
    )
    def api_auto():

        payload = (
            request.get_json(
                silent=True
            )
            or {}
        )

        if 'enabled' not in payload:

            return jsonify({
                'success': False,
                'message': 'Missing enabled.'
            }), 400

        result = bridge.set_auto_dispatch(
            payload['enabled']
        )

        return jsonify(
            result
        )

    # ============================================================
    # API - Reset
    # ============================================================

    @app.route(
        '/api/reset',
        methods=['POST']
    )
    def api_reset():

        return jsonify(
            bridge.reset_mission()
        )

    # ============================================================
    # API - Health
    # ============================================================

    @app.route(
        '/api/health',
        methods=['GET']
    )
    def api_health():

        status = bridge.get_status()

        return jsonify({
            'ok': True,
            'monitor_online':
                status.get(
                    'monitor_online',
                    False
                )
        })

    # ============================================================
    # API - DEMO
    # ============================================================

    @app.route(
        '/api/demo_fault',
        methods=['POST']
    )
    def api_demo_fault():

        return jsonify(
            bridge.trigger_demo_fault()
        )

    return app


def main(args=None):

    rclpy.init(
        args=args
    )

    bridge = DashboardBridge()

    executor = MultiThreadedExecutor(
        num_threads=2
    )

    executor.add_node(
        bridge
    )

    executor_thread = threading.Thread(
        target=executor.spin,
        daemon=True
    )

    executor_thread.start()

    app = create_app(
        bridge
    )

    try:

        bridge.get_logger().info(
            'Dashboard: '
            'http://localhost:8088'
        )

        app.run(
            host='0.0.0.0',
            port=8088,
            debug=False,
            use_reloader=False,
            threaded=True
        )

    except KeyboardInterrupt:

        pass

    finally:

        executor.shutdown()

        bridge.destroy_node()

        rclpy.shutdown()


if __name__ == '__main__':

    main()