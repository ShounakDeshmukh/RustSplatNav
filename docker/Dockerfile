# Base ROS2 Jazzy (desktop for GUI tools)
FROM osrf/ros:jazzy-desktop

ENV DEBIAN_FRONTEND=noninteractive

# Force HTTPS apt sources to avoid signature issues through HTTP interception/proxies.
RUN set -eux; \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i \
            -e 's|http://archive.ubuntu.com|https://archive.ubuntu.com|g' \
            -e 's|http://security.ubuntu.com|https://security.ubuntu.com|g' \
            /etc/apt/sources.list; \
    fi; \
    if [ -d /etc/apt/sources.list.d ]; then \
        find /etc/apt/sources.list.d -type f \( -name '*.list' -o -name '*.sources' \) -print0 | \
            xargs -0 -r sed -i \
                -e 's|http://packages.ros.org/ros2/ubuntu|https://packages.ros.org/ros2/ubuntu|g' \
                -e 's|http://archive.ubuntu.com|https://archive.ubuntu.com|g' \
                -e 's|http://security.ubuntu.com|https://security.ubuntu.com|g'; \
    fi

# -----------------------
# System dependencies
# -----------------------
RUN apt-get update && apt-get install -y \
    curl \
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
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Repair occasional FastRTPS/FastCDR ABI mismatches seen by gz sim.
# This is a reinstall of already-required ROS middleware packages, not new features.
RUN apt-get update && apt-get install -y --reinstall --no-install-recommends \
    ros-jazzy-fastcdr \
    ros-jazzy-fastrtps \
    ros-jazzy-rmw-fastrtps-cpp \
    ros-jazzy-rmw-fastrtps-shared-cpp \
    ros-jazzy-rosidl-typesupport-fastrtps-cpp \
    ros-jazzy-controller-manager-msgs \
    && apt-get clean && rm -rf /var/lib/apt/lists/* && ldconfig

# -----------------------
# Prepare your personal workspace
# -----------------------
RUN mkdir -p /workspace/src
WORKDIR /workspace

# -----------------------
# Source ROS automatically
# -----------------------
RUN echo "source /opt/ros/jazzy/setup.bash" >> /root/.bashrc && \
    echo "alias cls=clear" >> /root/.bashrc

# -----------------------
# Clearpath Jackal config
# (robot.yaml is mounted at runtime via docker-compose)
# -----------------------
RUN mkdir -p /root/clearpath

# -----------------------
# Default command
# -----------------------
CMD ["/bin/bash"]
