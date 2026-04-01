#!/usr/bin/env bash

# System setup script for VM
set -euo pipefail

echo "[1/6] Updating apt and installing base tools..."
sudo apt update
sudo apt install -y build-essential curl git vim ca-certificates gnupg lsb-release tmux
sudo apt install -y python3 python3-pip openssh-server xauth x11-apps mesa-utils

echo "[1b/6] Configuring SSH for X11 forwarding..."
sudo sed -i 's/^#\?X11Forwarding.*/X11Forwarding yes/' /etc/ssh/sshd_config
sudo sed -i 's/^#\?X11UseLocalhost.*/X11UseLocalhost yes/' /etc/ssh/sshd_config
sudo sed -i 's/^#\?AllowTcpForwarding.*/AllowTcpForwarding yes/' /etc/ssh/sshd_config
sudo systemctl enable --now ssh
sudo systemctl restart ssh

echo "[2/6] Installing Docker Engine from Docker official apt repository..."

# Remove distro-provided packages that may conflict with Docker CE.
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do
	if dpkg -s "$pkg" >/dev/null 2>&1; then
		sudo apt remove -y "$pkg"
	fi
done

sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker

if ! getent group docker >/dev/null; then
	sudo groupadd docker
fi
sudo usermod -aG docker "$USER"

echo "[3/6] Installing NVIDIA Container Toolkit (official NVIDIA apt repo)..."
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
	| sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
	| sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
	| sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null

sudo apt update
sudo apt install -y \
	nvidia-container-toolkit \
	nvidia-container-toolkit-base \
	libnvidia-container-tools \
	libnvidia-container1
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

echo "[4/6] Installing lazydocker..."
if ! sudo apt install -y lazydocker; then
	# Fallback to upstream installer if apt package is unavailable.
	curl -fsSL https://raw.githubusercontent.com/jesseduffield/lazydocker/master/scripts/install_update_linux.sh | bash
	if command -v lazydocker >/dev/null 2>&1; then
		sudo mv "$(command -v lazydocker)" /usr/local/bin/lazydocker
		sudo chmod +x /usr/local/bin/lazydocker
	fi
fi

echo "[5/6] Installing and configuring VNC (TigerVNC + XFCE)..."
sudo apt install -y tigervnc-standalone-server tigervnc-common dbus-x11 xfce4 xfce4-goodies

mkdir -p "$HOME/.vnc"
cat > "$HOME/.vnc/xstartup" <<'EOF'
#!/bin/sh
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
exec startxfce4
EOF
chmod +x "$HOME/.vnc/xstartup"

if [[ ! -f "$HOME/.vnc/passwd" ]]; then
	echo "VNC password not set yet. Run 'vncpasswd' after this script finishes."
fi

if [[ ! -f "$HOME/.config/systemd/user/vncserver@.service" ]]; then
	mkdir -p "$HOME/.config/systemd/user"
	cat > "$HOME/.config/systemd/user/vncserver@.service" <<'EOF'
[Unit]
Description=TigerVNC server on display :%i
After=network.target

[Service]
Type=forking
ExecStart=/usr/bin/vncserver :%i -geometry 1920x1080 -depth 24
ExecStop=/usr/bin/vncserver -kill :%i
Restart=on-failure

[Install]
WantedBy=default.target
EOF
fi

echo "[5b/6] Disabling user lingering so VNC stops after logout..."
sudo loginctl disable-linger "$USER" || true

git config --global user.name "Shounak Deshmukh"
git config --global user.email "shounsach@gmail.com"

echo "Setup X11 forwarding"
chmod +x /docker/setup-x11.sh
./docker/setup-x11.sh

echo "[6/6] Done."
echo "Open a new shell (or run: newgrp docker) for docker group changes to apply."
echo "Then run: vncpasswd"
echo "Then start VNC for this login with: systemctl --user daemon-reload && systemctl --user start vncserver@1"
echo "Stop it when done: systemctl --user stop vncserver@1"
echo "For SSH from your laptop use: ssh -L 5901:localhost:5901 <user>@<vm-ip>"
echo "Then connect your VNC client to: localhost:5901"
echo "Verify with: docker --version && nvidia-ctk --version && lazydocker --version"
echo "GPU test (if drivers are installed): docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi"
echo "VNC status: systemctl --user status vncserver@1"
