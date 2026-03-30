# RustSplatNav: Autonomous 3D Mapping with ROS 2 and Rust

> **It is a robot that can be dropped into a completely unknown environment and autonomously drive itself around until it has built a mathematically perfect, photorealistic 3D replica of that environment, without a human ever touching a joystick.**

---

## What This Project Does

This project makes a Clearpath Jackal robot explore and map unknown areas entirely on its own. Instead of just driving around randomly to avoid walls, the robot actively looks at its own map, finds the blurry or incomplete areas, and drives there to get a better look.

It combines four main pieces:
- **ROS 2 Jazzy & Gazebo:** The core software and simulation environment for the robot.
- **PINGS:** A mapping tool that uses camera and LiDAR data to build two things at once: a highly detailed 3D visual map, and a flat 2D collision map so the robot doesn't crash.
- **GauSS-MI:** The exploration "brain." It looks at the 3D map, calculates which areas need more data, and picks the next best coordinate for the robot to drive to.
- **Rust (`rclrs`):** The main control program. It grabs the coordinates from the brain and sends them to the robot's driving system.

---

## How We Handle Software Conflicts

The mapping algorithms (PINGS and GauSS-MI) were built by researchers using older software (ROS 1 and CUDA 11.8). Our robot uses the newest software (ROS 2 Jazzy and Ubuntu 24.04). 

To prevent everything from breaking, we use a layered Docker setup. The entire system runs inside a modern ROS 2 Docker container, but the older mapping algorithms are safely locked inside their own isolated Conda environments. This lets the old math run perfectly while still talking to the modern robot.

---

## System Architecture

```text
Gazebo Simulation (Jackal)
       │
       ├─► Camera + LiDAR Data ────────────┐
       │                                   │
       ▼                                   ▼
[ GauSS-MI Brain ]                  [ PINGS Mapper ]
Finds blurry areas                  Builds the 3D map
       │                                   │
       ├─► Next Target Coordinate          ├─► 2D Collision Map
       │                                   │
       ▼                                   ▼
[ Rust Controller ]                 [ Navigation System ]
Tells the robot to move             Stops the robot from crashing
       │                                   │
       └──────────────► [ Nav2 ] ◄─────────┘
                           │
                           ▼
                 Drive Commands to Robot
```

---

## Repository Structure

```text
rust-splat-nav/
│
├── docker/                # Setup files for the container and Conda
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── ros2_ws/               # Main workspace
│   └── src/
│       ├── rust_control/  # Rust control program
│       ├── pings_ros2/    # PINGS mapping code
│       ├── gauss_mi_ros2/ # GauSS-MI exploration code
│       └── launch/        # Startup scripts
│
├── logs/                  # Saved maps and test results
└── README.md
```

---

## System Requirements

- Ubuntu 22.04 or 24.04 (Host computer)
- Docker + Docker Compose
- NVIDIA GPU
- `nvidia-container-toolkit` installed on host

---

## Setup Instructions

### 1. Prepare the VM (required on every brand-new barebones VM)
Any time you create a new barebones VM, run this first before anything else.
On the same VM, you generally only do this one time.

From repo root:
```bash
cd /home/shooty/ros2-nerf-jackal
chmod +x setupvm.bash
./setupvm.bash
newgrp docker
```

Then finish VNC setup:
```bash
vncpasswd
systemctl --user daemon-reload
systemctl --user enable --now vncserver@1
```

If you reboot later, you do not need to rerun `setupvm.bash`.

### 2. Build the Docker Container
```bash
cd docker
docker compose build
```

### 3. SSH from your laptop and open the render tunnel
```bash
ssh -L 5901:localhost:5901 <user>@<vm-ip>
```

Open your VNC client and connect to:
```text
localhost:5901
```

### 4. Start container with GUI forwarding on VNC display
```bash
cd /home/shooty/ros2-nerf-jackal/docker
export DISPLAY=:1
./setup-x11.sh
docker compose up -d
docker exec -it ros2_jackal_nerf bash
```

Inside the container, set up the isolated math environments:
```bash
conda env create -f /workspace/src/pings_ros2/environment.yml
conda env create -f /workspace/src/gauss_mi_ros2/environment.yml
```

---

## Building the Code

Inside the container:
```bash
source /opt/ros/jazzy/setup.bash
cd /workspace
colcon build --symlink-install
```

To build only the Rust controller:
```bash
source /opt/ros/jazzy/setup.bash
source /opt/ros2_rust_ws/install/setup.bash
cd /workspace
colcon build --packages-select rust_control --symlink-install
source /workspace/install/setup.bash
```

---

## Project Phases

**Phase 1 — Basic Setup:** Get the Jackal driving in Gazebo and ensure the Docker container can use the GPU.  
**Phase 2 — Upgrading the Brain:** Rewrite the GauSS-MI code so it works with ROS 2 instead of ROS 1.  
**Phase 3 — Live Mapping:** Connect the PINGS mapper so it updates in real-time as the robot drives, rather than using pre-recorded data.  
**Phase 4 — Rust Integration:** Write the Rust program that acts as the middleman between the brain and the wheels.  
**Phase 5 — Full Autonomy:** Drop the robot into a simulated building and let it map the whole thing by itself.  

---

## Evaluation

To prove this system works better than standard mapping, we will measure:
- **Map Quality:** How clear and realistic the final 3D map looks.
- **Speed:** How fast the robot can fully map the room.
- **Safety:** Making sure the robot never crashes into walls while exploring.

---

## License
MIT

