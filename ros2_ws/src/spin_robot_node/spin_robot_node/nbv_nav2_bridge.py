from __future__ import annotations

import math

import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node


class NbvNav2Bridge(Node):
    def __init__(self) -> None:
        super().__init__('nbv_nav2_bridge')

        self.declare_parameter('nbv_topic', '/gaussmi/nbv_pose')
        self.declare_parameter('goal_frame', 'map')
        self.declare_parameter('goal_preempt_threshold', 0.20)
        self.declare_parameter('navigate_action', '/j100/navigate_to_pose')
        self.declare_parameter('server_wait_sec', 30.0)

        self._nbv_topic = str(self.get_parameter('nbv_topic').value)
        self._goal_frame = str(self.get_parameter('goal_frame').value)
        self._goal_preempt_threshold = float(self.get_parameter('goal_preempt_threshold').value)
        self._server_wait_sec = float(self.get_parameter('server_wait_sec').value)
        self._action_name = str(self.get_parameter('navigate_action').value)

        self._client = ActionClient(self, NavigateToPose, self._action_name)
        self._sub = self.create_subscription(PoseStamped, self._nbv_topic, self._on_nbv, 10)
        self._timer = self.create_timer(0.5, self._tick)

        self._latest_goal: PoseStamped | None = None
        self._active_goal: PoseStamped | None = None
        self._goal_handle = None
        self._server_ready = False

        self.get_logger().info(
            f'NBV bridge waiting for {self._action_name} and listening on {self._nbv_topic}'
        )

    def _on_nbv(self, msg: PoseStamped) -> None:
        msg.header.frame_id = self._goal_frame
        self._latest_goal = msg
        self.get_logger().debug(
            f'NBV bridge received goal: x={msg.pose.position.x:.2f} y={msg.pose.position.y:.2f} z={msg.pose.position.z:.2f}'
        )

    def _tick(self) -> None:
        if not self._server_ready:
            if self._client.wait_for_server(timeout_sec=self._server_wait_sec):
                self._server_ready = True
                self.get_logger().info(f'✓ Connected to {self._action_name}')
            else:
                self.get_logger().warn(f'✗ Waiting for {self._action_name} server...')
                return

        if self._latest_goal is None:
            self.get_logger().debug('Waiting for first NBV goal...')
            return

        if self._active_goal is not None and _goal_distance(self._active_goal, self._latest_goal) < self._goal_preempt_threshold:
            self.get_logger().debug('Current goal too close to latest, skipping')
            return

        if self._goal_handle is not None:
            try:
                self.get_logger().info('Cancelling previous goal to send new one')
                cancel_future = self._goal_handle.cancel_goal_async()
                cancel_future.add_done_callback(lambda _: None)
            except Exception as exc:
                self.get_logger().error(f'Failed to cancel goal: {exc}')
            self._goal_handle = None

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = self._latest_goal
        self.get_logger().info(
            f'→ Sending NBV goal: x={goal_msg.pose.pose.position.x:.3f} y={goal_msg.pose.pose.position.y:.3f} z={goal_msg.pose.pose.position.z:.3f}'
        )
        send_future = self._client.send_goal_async(goal_msg)
        send_future.add_done_callback(self._on_goal_response)

    def _on_goal_response(self, future) -> None:
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('✗ Nav2 REJECTED the NBV goal')
            return

        self._goal_handle = goal_handle
        self._active_goal = self._latest_goal
        self.get_logger().info('✓ NBV goal ACCEPTED by Nav2, robot moving...')


def _goal_distance(a: PoseStamped, b: PoseStamped) -> float:
    dx = float(a.pose.position.x - b.pose.position.x)
    dy = float(a.pose.position.y - b.pose.position.y)
    return math.hypot(dx, dy)


def main() -> None:
    rclpy.init()
    node = NbvNav2Bridge()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
