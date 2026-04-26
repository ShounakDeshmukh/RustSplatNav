# SplatNav

ROS 2 Jazzy + Gazebo Jackal stack with a simple Python controller and a ROS 1 GauSS-MI sidecar bridge.

## Current State

- Rust has been fully removed.
- Controller is now Python (`rclpy`) in `spin_robot_node`.
- ROS 2 image is lean and does not include conda.
- GauSS-MI stays in the official ROS 1 image (`johanna17/gauss-mi:v1`) from the upstream README.
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

**→ See [STARTUP_GUIDE.md](STARTUP_GUIDE.md) for a complete 0-10 step guide.**

In summary:

1. **Host setup** (first time only):
   ```bash
   chmod +x setupvm.bash && ./setupvm.bash && newgrp docker
   cd docker && ./setup-x11.sh
   ```

2. **Start stack**:
   ```bash
   cd ros2_ws
   just compose-up-gaussmi
   ```

3. **Launch services** (in ROS 2 container):
   ```bash
   docker exec -it ros2_jackal_nerf bash
   just launch-sim        # Terminal 1: Gazebo simulator
   just launch-nav2       # Terminal 2: Nav2 + SLAM + RViz
   ```

4. **Launch GauSS-MI** (in ROS 1 container):
   ```bash
   docker exec -it gaussmi_ros1 bash
   just run-gaussmi-active
   ```

5. **Stop all**:
   ```bash
   just compose-down-gaussmi
   ```
```

`just launch-sim` now tries GUI first when X11 is reachable and automatically falls back to headless mode if GUI startup fails.

To force GUI mode only:

```bash
just launch-sim-ui
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

To run it as a simple active-exploration controller that follows the best-next-view pose published on `/gaussmi/nbv_pose`, pass:

```bash
ros2 run spin_robot_node spin_robot_node --ros-args -p mode:=nbv
```

In `nbv` mode it uses `/j100/platform/odom/filtered` plus `/gaussmi/nbv_pose` and drives toward the selected viewpoint instead of only spinning in place.

## Nav2 Integration (Clearpath Demos)

Inside `ros2_jackal_nerf`:

```bash
cd /workspace
just launch-nav2-nbv
```

This launches Clearpath's Nav2 demo stack (`clearpath_nav2_demos` Nav2 + SLAM) and starts the NBV bridge node that forwards `/gaussmi/nbv_pose` goals to `/navigate_to_pose`.

## Generate and Retrieve a Splat

1. Bring up the stack from `ros2_ws`:

```bash
just compose-up-gaussmi
```

2. In another shell, start GauSS-MI active mapping:

```bash
cd /home/sdeshmu4/RustSplatNav/ros2_ws
just run-gaussmi-active
```

3. After the run completes, print the latest generated PLY on the host:

```bash
cd /home/sdeshmu4/RustSplatNav/ros2_ws
just latest-splat
```

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

