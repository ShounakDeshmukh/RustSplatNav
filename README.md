# SplatNav

ROS 2 Jazzy + Gazebo Jackal stack with a simple Python controller and a ROS 1 GauSS-MI sidecar bridge.

## Current State

- Rust has been fully removed.
- Controller is now Python (`rclpy`) in `spin_robot_node`.
- ROS 2 image is lean and does not include conda.
- GauSS-MI stays in a separate ROS 1 image (`johanna17/gauss-mi:v1`).
- ROS 1/ROS 2 communication uses the socket relay under `relay/` + `gaussmi_relay`.

## Architecture

```text
Gazebo (Jackal, ROS 2 Jazzy)
       -> /j100/sensors/camera_0/color/image
       -> /j100/sensors/camera_0/depth/image
       -> /j100/platform/odom/filtered
                            |
                            v
gaussmi_relay (ROS 2)
       <-> socket bridge <->
gaussmi_ros1 relay (ROS 1 in sidecar image)
                            |
                            v
/gaussmi/nbv_pose (back to ROS 2)
```

## Repo Layout

```text
RustSplatNav/
       docker/
              Dockerfile
              docker-compose.yml
              setup-x11.sh
       relay/
              ros1/
       ros2_ws/
              justfile
              src/
                     spin_robot_node/
                     GauSS-MI-ros2/
       logs/
       nerf/
```

## Host Requirements

- Ubuntu 22.04/24.04 host
- Docker + Docker Compose
- NVIDIA GPU + `nvidia-container-toolkit`

## Quick Start

### 1. Host setup (first time on a new VM)

From repo root:

```bash
cd /home/sdeshmu4/RustSplatNav
chmod +x setupvm.bash
./setupvm.bash
newgrp docker
```

### 2. Prepare X11 auth

```bash
cd /home/sdeshmu4/RustSplatNav/docker
./setup-x11.sh
```

### 3. Build and start stack

From `ros2_ws`:

```bash
cd /home/sdeshmu4/RustSplatNav/ros2_ws
just compose-up-gaussmi
```

This starts:
- `ros2` (ROS 2 Jazzy stack)
- `gaussmi_relay` (ROS 2 bridge node)
- `gaussmi_ros1` (ROS 1 sidecar image)

Stop all:

```bash
just compose-down-gaussmi
```

### 4. Enter ROS 2 container and launch sim

```bash
docker exec -it ros2_jackal_nerf bash
cd /workspace
just launch-sim
```

If GPU rendering is flaky, use:

```bash
just launch-sim-software
```

## Python Controller

Inside `ros2_jackal_nerf`:

```bash
cd /workspace
just run-controller
```

This publishes `TwistStamped` to `/j100/cmd_vel`.

## Common Commands

- Build ROS workspace: `just build`
- List topics: `just topics`
- Start Foxglove bridge: `just launch-foxglove`

## Notes

- `network_mode: host` is intentional for SSH X11 and local relay sockets.
- `docker/Dockerfile` includes a targeted reinstall of FastRTPS/FastCDR ROS packages to reduce Gazebo symbol mismatch issues.
- If Gazebo still throws symbol errors after Dockerfile changes, rebuild without cache:

```bash
cd /home/sdeshmu4/RustSplatNav/docker
docker compose build --no-cache ros2 gaussmi_relay
docker compose up -d ros2 gaussmi_relay gaussmi_ros1
```

## License

MIT

