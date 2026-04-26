from __future__ import annotations

import pathlib
import socket
import sys
import threading
import time
from typing import Optional

import rclpy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import Image


RELAY_ROOT = pathlib.Path("/relay")
if RELAY_ROOT.exists() and str(RELAY_ROOT) not in sys.path:
    sys.path.insert(0, str(RELAY_ROOT))

from protocol import recv_frame, send_frame  # noqa: E402


class GaussmiRos2Relay(Node):
    def __init__(self) -> None:
        super().__init__("gaussmi_ros2_relay")
        self.declare_parameter("peer_host", "127.0.0.1")
        self.declare_parameter("peer_port", 50051)
        self.declare_parameter("rgb_topic", "/camera/bgr")
        self.declare_parameter("depth_topic", "/camera/depth")
        self.declare_parameter("pose_topic", "/camera/pose")
        self.declare_parameter("odom_topic", "/j100/platform/odom/filtered")
        self.declare_parameter("camera_z_offset", 1.0)
        self.declare_parameter("nbv_topic", "/gaussmi/nbv_pose")

        self._peer_host = self.get_parameter("peer_host").value
        self._peer_port = int(self.get_parameter("peer_port").value)
        self._rgb_topic = self.get_parameter("rgb_topic").value
        self._depth_topic = self.get_parameter("depth_topic").value
        self._pose_topic = self.get_parameter("pose_topic").value
        self._odom_topic = self.get_parameter("odom_topic").value
        self._camera_z_offset = float(self.get_parameter("camera_z_offset").value)
        self._nbv_topic = self.get_parameter("nbv_topic").value

        self._sock: Optional[socket.socket] = None
        self._sock_lock = threading.Lock()
        self._stats_lock = threading.Lock()
        self._running = True
        self._tx_counts = {"rgb": 0, "depth": 0, "pose": 0, "nbv": 0}
        self._rx_counts = {"rgb": 0, "depth": 0, "pose": 0, "nbv": 0}
        self._dropped_no_socket = 0
        self._last_stats_time = time.time()

        self._nbv_pub = self.create_publisher(PoseStamped, self._nbv_topic, 10)

        self._rgb_sub = None
        if self._rgb_topic:
            self._rgb_sub = self.create_subscription(
                Image,
                self._rgb_topic,
                lambda msg: self._send_image("rgb", msg),
                10,
            )

        self._depth_sub = None
        if self._depth_topic:
            self._depth_sub = self.create_subscription(
                Image,
                self._depth_topic,
                lambda msg: self._send_image("depth", msg),
                10,
            )

        self._pose_sub = None
        if self._pose_topic:
            self._pose_sub = self.create_subscription(
                PoseStamped,
                self._pose_topic,
                lambda msg: self._send_pose("pose", msg),
                10,
            )

        self._odom_sub = None
        if self._odom_topic:
            self._odom_sub = self.create_subscription(
                Odometry,
                self._odom_topic,
                self._send_odom_as_pose,
                10,
            )

        self._reader_thread = threading.Thread(target=self._connect_and_read, daemon=True)
        self._reader_thread.start()
        self._stats_timer = self.create_timer(5.0, self._log_stats)

        self.get_logger().info(
            f"ROS 2 relay ready; connecting to ROS 1 relay at {self._peer_host}:{self._peer_port} "
            f"with odom_topic={self._odom_topic} camera_z_offset={self._camera_z_offset}m"
        )

    def _connect_and_read(self) -> None:
        while self._running and rclpy.ok():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            try:
                sock.connect((self._peer_host, self._peer_port))
            except OSError as exc:
                self.get_logger().warn(f"ROS 2 relay connect failed: {exc}; retrying")
                sock.close()
                time.sleep(1.0)
                continue

            with self._sock_lock:
                self._sock = sock

            self.get_logger().info("ROS 2 relay connected")
            try:
                self._recv_loop(sock)
            finally:
                with self._sock_lock:
                    if self._sock is sock:
                        self._sock = None
                try:
                    sock.close()
                except OSError:
                    pass

            time.sleep(1.0)

    def _recv_loop(self, sock: socket.socket) -> None:
        while self._running and rclpy.ok():
            frame = recv_frame(sock)
            if frame is None:
                self.get_logger().warn("ROS 2 relay socket closed")
                return
            meta, payload = frame
            stream = meta.get("stream")
            self._bump_counter(self._rx_counts, str(stream))
            if stream == "nbv":
                try:
                    pose = _pose_from_meta(meta)
                    self.get_logger().info(f"ROS 2 relay: Publishing NBV pose: {pose.pose.position}")
                    self._nbv_pub.publish(pose)
                except Exception as exc:
                    self.get_logger().error(f"ROS 2 relay: Failed to process NBV: {exc}")
            else:
                self.get_logger().warn(f"ROS 2 relay received unexpected stream {stream}")

    def _send(self, meta: dict, payload: bytes = b"") -> None:
        with self._sock_lock:
            sock = self._sock
        if sock is None:
            with self._stats_lock:
                self._dropped_no_socket += 1
            return
        try:
            send_frame(sock, meta, payload)
            self._bump_counter(self._tx_counts, str(meta.get("stream", "")))
        except OSError as exc:
            self.get_logger().warn(f"ROS 2 relay send failed: {exc}")

    def _bump_counter(self, counter: dict, key: str) -> None:
        if key not in counter:
            return
        with self._stats_lock:
            counter[key] += 1

    def _log_stats(self) -> None:
        with self._sock_lock:
            connected = self._sock is not None
        with self._stats_lock:
            now = time.time()
            elapsed = max(1e-3, now - self._last_stats_time)
            self._last_stats_time = now
            tx = dict(self._tx_counts)
            rx = dict(self._rx_counts)
            dropped = self._dropped_no_socket
            self._dropped_no_socket = 0
        self.get_logger().info(
            "Relay stats connected=%s tx(rgb=%d depth=%d pose=%d nbv=%d) "
            "rx(rgb=%d depth=%d pose=%d nbv=%d) drop_no_socket=%d dt=%.1fs"
            % (
                str(connected).lower(),
                tx["rgb"], tx["depth"], tx["pose"], tx["nbv"],
                rx["rgb"], rx["depth"], rx["pose"], rx["nbv"],
                dropped,
                elapsed,
            )
        )

    def _send_image(self, stream: str, msg: Image) -> None:
        self._send(_image_meta(stream, msg), bytes(msg.data))

    def _send_pose(self, stream: str, msg: PoseStamped) -> None:
        self._send(_pose_meta(stream, msg))

    def _send_odom_as_pose(self, msg: Odometry) -> None:
        self._send(_pose_meta_from_odom("pose", msg, self._camera_z_offset))

    def destroy_node(self):  # type: ignore[override]
        self._running = False
        with self._sock_lock:
            sock = self._sock
            self._sock = None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
        return super().destroy_node()


def _stamp_meta(stamp) -> dict:
    return {"sec": int(stamp.sec), "nsec": int(stamp.nanosec)}


def _image_meta(stream: str, msg: Image) -> dict:
    return {
        "stream": stream,
        "kind": "image",
        "stamp": _stamp_meta(msg.header.stamp),
        "frame_id": msg.header.frame_id,
        "height": int(msg.height),
        "width": int(msg.width),
        "encoding": msg.encoding,
        "is_bigendian": int(msg.is_bigendian),
        "step": int(msg.step),
        "data_len": int(len(msg.data)),
    }


def _pose_meta(stream: str, msg: PoseStamped) -> dict:
    return {
        "stream": stream,
        "kind": "pose",
        "stamp": _stamp_meta(msg.header.stamp),
        "frame_id": msg.header.frame_id,
        "position": {
            "x": float(msg.pose.position.x),
            "y": float(msg.pose.position.y),
            "z": float(msg.pose.position.z),
        },
        "orientation": {
            "x": float(msg.pose.orientation.x),
            "y": float(msg.pose.orientation.y),
            "z": float(msg.pose.orientation.z),
            "w": float(msg.pose.orientation.w),
        },
    }


def _pose_meta_from_odom(stream: str, msg: Odometry, camera_z_offset: float = 0.0) -> dict:
    return {
        "stream": stream,
        "kind": "pose",
        "stamp": _stamp_meta(msg.header.stamp),
        "frame_id": msg.header.frame_id,
        "position": {
            "x": float(msg.pose.pose.position.x),
            "y": float(msg.pose.pose.position.y),
            "z": float(msg.pose.pose.position.z) + camera_z_offset,
        },
        "orientation": {
            "x": float(msg.pose.pose.orientation.x),
            "y": float(msg.pose.pose.orientation.y),
            "z": float(msg.pose.pose.orientation.z),
            "w": float(msg.pose.pose.orientation.w),
        },
    }


def _pose_from_meta(meta: dict) -> PoseStamped:
    msg = PoseStamped()
    msg.header.stamp.sec = int(meta["stamp"]["sec"])
    msg.header.stamp.nanosec = int(meta["stamp"]["nsec"])
    msg.header.frame_id = meta.get("frame_id", "")
    msg.pose.position.x = float(meta["position"]["x"])
    msg.pose.position.y = float(meta["position"]["y"])
    msg.pose.position.z = float(meta["position"]["z"])
    msg.pose.orientation.x = float(meta["orientation"]["x"])
    msg.pose.orientation.y = float(meta["orientation"]["y"])
    msg.pose.orientation.z = float(meta["orientation"]["z"])
    msg.pose.orientation.w = float(meta["orientation"]["w"])
    return msg


def main() -> None:
    rclpy.init()
    node = GaussmiRos2Relay()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
