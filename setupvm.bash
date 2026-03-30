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

echo "[2/6] Installing Docker engine (docker.io)..."
sudo apt install -y docker.io
sudo systemctl enable --now docker

if ! getent group docker >/dev/null; then
	sudo groupadd docker
fi
sudo usermod -aG docker "$USER"

echo "[3/6] Installing NVIDIA Container Toolkit..."
distribution="$(. /etc/os-release; echo "${ID}${VERSION_ID}")"
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
	| sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL "https://nvidia.github.io/libnvidia-container/${distribution}/libnvidia-container.list" \
	| sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
	| sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null

sudo apt update
sudo apt install -y nvidia-container-toolkit
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

echo "[5b/6] Enabling user lingering so VNC can stay up after SSH logout..."
sudo loginctl enable-linger "$USER"

echo "[6/6] Done."
echo "Open a new shell (or run: newgrp docker) for docker group changes to apply."
echo "Then run: vncpasswd"
echo "Then enable VNC with: systemctl --user daemon-reload && systemctl --user enable --now vncserver@1"
echo "For SSH from your laptop use: ssh -L 5901:localhost:5901 <user>@<vm-ip>"
echo "Then connect your VNC client to: localhost:5901"
echo "Verify with: docker --version && lazydocker --version && systemctl --user status vncserver@1"
