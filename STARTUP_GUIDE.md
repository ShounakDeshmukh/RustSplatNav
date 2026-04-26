# SplatNav 0-10 Startup Guide

**Goal**: Simple Nav2 mapping + Gaussian Splatting on Clearpath Jackal simulator.

**CRITICAL**: This requires **SLAM** to build the map. Nav2 cannot plan without a map. You must run SLAM (Step 5A) before or alongside Nav2 (Step 5B).

## Prerequisites

- **OS**: Ubuntu 22.04/24.04 host
- **Docker**: Docker + Docker Compose installed
- **GPU**: NVIDIA GPU with `nvidia-container-toolkit` configured
- **X11**: X server running (SSH X11 forwarding supported)

---

## Step 0: Host Setup (First Time Only)

Run this once on a fresh VM:

```bash
cd /home/sdeshmu4/SplatNav
chmod +x setupvm.bash
./setupvm.bash
newgrp docker
```

This installs Docker, NVIDIA Container Toolkit, and SSH X11 forwarding.

---

## Step 1: Configure X11 Authentication

```bash
cd /home/sdeshmu4/SplatNav/docker
./setup-x11.sh
```

This allows GUI applications (Gazebo, RViz) to display on your host.

---

## Step 2: Start All Containers

```bash
cd /home/sdeshmu4/SplatNav/ros2_ws
just compose-up-gaussmi
```

This builds and starts:
- **ros2**: ROS 2 Jazzy with Clearpath Jackal simulator
- **gaussmi_relay**: ROS 2 ↔ ROS 1 bridge for GauSS-MI
- **gaussmi_ros1**: ROS 1 container with GauSS-MI active mapping

**Wait 10-15 seconds for all services to initialize.**

---

## Step 3: Enter ROS 2 Container

```bash
docker exec -it ros2_jackal_nerf bash
```

You are now inside the ROS 2 container. All remaining steps run here unless noted.

---

## Step 4: Start Gazebo Simulator

```bash
just launch-sim
```

This launches the Jackal simulator in Gazebo with camera + depth sensors.
- You should see the Jackal robot in a simulated world
- Camera feed is published to `/j100/sensors/camera_0/color/image`
- Depth is on `/j100/sensors/camera_0/depth/image`

**Keep this terminal open.**

---

## Step 5A: Launch SLAM (New Terminal)

**SLAM is REQUIRED.** It publishes the `/map` frame that Nav2 needs to navigate.

In a **new host terminal**, run:

```bash
docker exec -it ros2_jackal_nerf bash
source /opt/ros/jazzy/setup.bash
ros2 launch clearpath_nav2_demos slam.launch.py use_sim_time:=true setup_path:=/root/clearpath
```

This builds a map in real-time from lidar/camera data and publishes:
- `/map` frame and TF transforms
- Occupancy grid
- Odometry corrections

**Keep this terminal open.**

---

## Step 5B: Launch Nav2 (New Terminal)

In a **new host terminal**, run:

```bash
docker exec -it ros2_jackal_nerf bash
source /opt/ros/jazzy/setup.bash
ros2 launch clearpath_nav2_demos nav2_without_slam.launch.py use_sim_time:=true setup_path:=/root/clearpath
```

*(or `nav2.launch.py` if `nav2_without_slam.launch.py` doesn't exist; the key is SLAM from Step 5A is already running)*

This starts:
- **Nav2 Stack**: costmap, planner, controller (using map from SLAM)
- **RViz**: GUI showing map, costmap, and navigation goals

**In RViz**:
1. Wait 5-10 seconds for the map to populate from SLAM
2. Set the initial pose (2D Pose Estimate button, click on robot in map)
3. Give Nav2 a goal (Nav2 Goal button, click on map)
4. Watch the Jackal autonomously navigate in both Gazebo AND RViz

**Keep this terminal open.**

---

## Step 6: Start Gaussian Splatting (New Terminal)

In a **new host terminal**, run:

```bash
docker exec -it gaussmi_ros1 bash
just run-gaussmi-active
```

This starts GauSS-MI active mapping in the ROS 1 sidecar:
- Subscribes to camera, depth, and odometry from the simulator
- Builds a 3D Gaussian splat model in real-time
- Suggests next-best-view poses to improve coverage
- Writes results to `/home/do/ws_gaussmi/results/`

**Keep this terminal open.**

---

## Step 7: Verify Data Flow

In the **ROS 2 container**, verify all critical topics are publishing:

```bash
just verify-system
```

Should show all topics present (count = 1 for each).

Or manually check:
```bash
just topics | grep -E "map|scan|nbv_pose|odom"
```

You should see:
- `/j100/map` (Nav2 SLAM map)
- `/j100/sensors/lidar2d_0/scan` (Lidar scans)
- `/j100/platform/odom/filtered` (Gazebo odometry)
- `/gaussmi/nbv_pose` (GauSS-MI next-best-view suggestions)
- `/gaussmi/nbv_pose` (GauSS-MI next-best-view suggestions)
- `/map` (Nav2 SLAM map)

---

## Step 8: Monitor Nav2 in RViz

- **RViz window** should show the map being built in real-time
- **Costmap** shows navigable areas
- **Odometry** confirms Jackal movement

---

## Step 9: Monitor Gaussian Splatting

The `just run-gaussmi-active` terminal will show:
- Frame counts processed
- Gaussian splat density
- Model save paths

Results are saved to:
```
../gaussmi/results/
  └── <timestamp>/
      ├── final/
      │   └── point_cloud.ply
      └── ...
```

---

## Step 11 (Optional): Autonomous NBV-Following

Instead of manual RViz goals, have the robot **autonomously explore** based on GauSS-MI's next-best-view suggestions.

**New Terminal: NBV→Nav2 Bridge**

```bash
docker exec -it ros2_jackal_nerf bash
source /opt/ros/jazzy/setup.bash
cd /workspace && colcon build --packages-select spin_robot_node --symlink-install
source install/setup.bash
ros2 run spin_robot_node nbv_nav2_bridge --ros-args \
  -p nbv_topic:=/gaussmi/nbv_pose \
  -p goal_frame:=map \
  -p navigate_action:=/navigate_to_pose
```

Now the robot will **automatically navigate to each NBV pose** as GauSS-MI generates them, creating an autonomous exploration loop:

```
Gazebo → Camera/Lidar → GauSS-MI → NBV Poses → NBV Bridge → Nav2 → Jackal Moves → SLAM Updates → Map → repeat
```

The full autonomous pipeline is now running! 🚀

---

## Step 12: Monitor Everything

**Terminals Overview:**
- **Terminal 1**: Gazebo simulator (`just launch-sim`)
- **Terminal 2**: SLAM (`just launch-slam`)
- **Terminal 3**: Nav2 (`just launch-nav2`)
- **Terminal 4**: GauSS-MI (`just run-gaussmi-active`)
- **Terminal 5** (optional): NBV bridge (autonomous exploration)

**Outputs to Watch:**
- **Gazebo**: Robot moving in simulation
- **RViz**: Map building, costmap updating, planned paths
- **GauSS-MI terminal**: Frame counts, splat density, NBV gains
- **Results**: `../gaussmi/results/<timestamp>/final/point_cloud.ply` (the 3D Gaussian splat model)

When done, stop all containers:

```bash
cd /home/sdeshmu4/SplatNav/ros2_ws
just compose-down-gaussmi
```

---

## Troubleshooting

### "Timed out waiting for transform from base_link to map"
This means **SLAM is not running**. Ensure:
1. You ran `slam.launch.py` (Step 5A) BEFORE `nav2.launch.py` (Step 5B)
2. Wait 10-15 seconds after SLAM starts for the map to publish
3. Check SLAM terminal for errors (should show map building progress)
4. In RViz, verify you can see the costmap layer updating

### "Robot moves in RViz but not in Gazebo"
This is usually the transform issue above. Also check:
1. Both Gazebo (Step 4) and SLAM (Step 5A) are running
2. In RViz, set the initial pose with "2D Pose Estimate" 
3. Wait a few seconds for Nav2 to initialize
4. Only THEN set a goal with "Nav2 Goal"

### "SLAM not building map / no occupancy grid visible"
- Check lidar is publishing: `ros2 topic list | grep scan` or `ros2 topic list | grep lidar`
- Verify robot.yaml is correctly mounted with your lidar config
- Check that `use_sim_time:=true` is set (it uses Gazebo's simulated time, not wall time)

---

## Essential Commands Reference

| Command | What | Where |
|---------|------|-------|
| `just compose-up-gaussmi` | Start all containers | ros2_ws |
| `just compose-down-gaussmi` | Stop all containers | ros2_ws |
| `just launch-sim` | Start Gazebo simulator | ros2 container |
| `just launch-nav2` | Start Nav2 + SLAM + RViz | ros2 container |
| `just run-gaussmi-active` | Start GauSS-MI mapping | gaussmi_ros1 container |
| `just topics` | List ROS topics | ros2 container |
| `just build` | Rebuild ROS workspace | ros2 container |

---

## Architecture Overview

```
Host Machine (Ubuntu 22.04/24.04)
    ↓
Docker Compose
    ├── ros2 (ROS 2 Jazzy)
    │   ├── Gazebo Jackal Simulator
    │   ├── Nav2 Stack (costmap, planner, controller)
    │   ├── SLAM Module
    │   └── RViz Visualization
    ├── gaussmi_relay (ROS 2 bridge)
    │   └── Socket relay to ROS 1
    └── gaussmi_ros1 (ROS 1 Noetic)
        └── GauSS-MI Active Mapping
```

---

Done! Your stack is running simple Nav2 mapping + Gaussian splatting. 🚀
