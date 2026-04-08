# Base ROS2 Jazzy (desktop for GUI tools)
FROM osrf/ros:jazzy-desktop

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/root/.cargo/bin:${PATH}"

# -----------------------
# System dependencies
# -----------------------
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    python3-pip \
    python3-yaml \
    python3-colcon-common-extensions \
    build-essential \
    cmake \
    ninja-build \
    pkg-config \
    libssl-dev \
    libclang-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    python3-vcstool \
    ros-jazzy-example-interfaces \
    ros-jazzy-test-msgs \
    ros-jazzy-test-interface-files \
    ros-jazzy-nav2-bringup \
    ros-jazzy-ros-gz \
    ros-jazzy-clearpath-simulator \
    ros-jazzy-clearpath-desktop \
    ros-jazzy-foxglove-bridge \
    vim \
    nano \
    tmux \
    ranger \
    just \
    eog \
    && rm -rf /var/lib/apt/lists/*

# -----------------------
# Install colcon plugins for Rust
# -----------------------
RUN pip install --break-system-packages colcon-cargo colcon-ros-cargo

# -----------------------
# Install Rust
# -----------------------
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y

# -----------------------
# Install Heavy Python Dependencies First (for better Docker caching)
# (Commented out: Nerfstudio requires an NVIDIA GPU. Uncomment if moving to a GPU machine)
# -----------------------
# RUN pip install --default-timeout=1000 --no-cache-dir --break-system-packages open3d torch torchvision

# -----------------------
# Install Nerfstudio
# (Commented out: Requires NVIDIA GPU for tiny-cuda-nn and training)
# -----------------------
# RUN pip install --default-timeout=1000 --no-cache-dir --break-system-packages nerfstudio


RUN mkdir -p /opt/ros2_rust_ws/src
WORKDIR /opt/ros2_rust_ws

# -----------------------
# Clone ROS2 interface repos for ros2_rust
# -----------------------
# Note: The ros2_rust repo specifically notes we need test-msgs and example-interfaces installed
# via apt (handled above) as a workaround. No need to clone `test_interface_files` yourself for Jazzy.
RUN git clone -b jazzy https://github.com/ros2/common_interfaces.git src/common_interfaces && \
    git clone -b jazzy https://github.com/ros2/example_interfaces.git src/example_interfaces && \
    git clone -b jazzy https://github.com/ros2/rcl_interfaces.git src/rcl_interfaces && \
    git clone -b jazzy https://github.com/ros2/rosidl_core.git src/rosidl_core && \
    git clone -b jazzy https://github.com/ros2/rosidl_defaults.git src/rosidl_defaults && \
    git clone -b jazzy https://github.com/ros2/unique_identifier_msgs.git src/unique_identifier_msgs && \
    git clone https://github.com/ros2-rust/rosidl_rust.git src/rosidl_rust && \
    git clone https://github.com/ros2-rust/examples.git src/examples

# -----------------------
# Build the worksapce for ros2_rust
# -----------------------
RUN bash -c "source /opt/ros/jazzy/setup.sh && colcon build"

# -----------------------
# Prepare your personal workspace
# -----------------------
RUN mkdir -p /workspace/src
WORKDIR /workspace

# -----------------------
# Helper to create GauSS-MI conda env from mounted submodule (optional - user setup)
# Note: Users can set up conda manually if needed by installing miniconda/mambaforge
# -----------------------
# RUN cat <<'EOF' > /usr/local/bin/setup-gaussmi-env
# #!/usr/bin/env bash
# set -euo pipefail
#
# ENV_FILE="/workspace/src/GauSS-MI-ros2/environment.yml"
#
# if [[ ! -f "${ENV_FILE}" ]]; then
#     echo "GauSS-MI env file not found at ${ENV_FILE}." >&2
#     echo "Make sure submodules are initialized and /workspace is mounted." >&2
#     exit 1
# fi
#
# if conda env list | awk '{print $1}' | grep -qx "GauSS-MI"; then
#     echo "Conda env GauSS-MI already exists."
#     exit 0
# fi
#
# echo "Creating GauSS-MI conda environment from ${ENV_FILE} ..."
# conda env create -f "${ENV_FILE}"
# echo "Done. Activate with: conda activate GauSS-MI"
# EOF
#
# RUN chmod +x /usr/local/bin/setup-gaussmi-env

# -----------------------
# Source ROS automatically (Both Jazzy and the Rust underlay)
# -----------------------
RUN echo "source /opt/ros/jazzy/setup.bash" >> /root/.bashrc && \
    echo "source /opt/ros2_rust_ws/install/setup.bash" >> /root/.bashrc && \
    echo "alias cls=clear" >> /root/.bashrc

# -----------------------
# Clearpath Jackal config
# (robot.yaml is mounted at runtime via docker-compose)
# -----------------------
RUN mkdir -p /root/clearpath

# -----------------------
# Install Miniconda for GauSS-MI/PINGS Python environments (at the end, after ROS build)
# -----------------------
RUN wget -qO /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    bash /tmp/miniconda.sh -b -p /opt/conda && \
    rm -f /tmp/miniconda.sh && \
    /opt/conda/bin/conda config --set auto_activate_base false && \
    /opt/conda/bin/conda init bash

# Make conda available in interactive shells without forcing conda python globally.
RUN echo "source /opt/conda/etc/profile.d/conda.sh" >> /root/.bashrc

# -----------------------
# Default command
# -----------------------
CMD ["/bin/bash"]
