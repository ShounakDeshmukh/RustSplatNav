#!/usr/bin/env bash
# Setup X11 auth for Docker containers (works for local desktops and SSH+VNC sessions).

set -euo pipefail

XAUTH_FILE="/tmp/.docker.xauth"

if [[ -z "${DISPLAY:-}" ]]; then
    echo "Error: DISPLAY is not set."
    echo "If you are on SSH + VNC, run: export DISPLAY=:1"
    exit 1
fi

if ! command -v xauth >/dev/null 2>&1; then
    echo "Error: xauth is not installed. Install it first: sudo apt install -y xauth"
    exit 1
fi

touch "$XAUTH_FILE"
chmod 600 "$XAUTH_FILE"

# Rebuild container auth from the active X cookie so root in the container can connect.
if xauth nlist "$DISPLAY" | sed -e 's/^..../ffff/' | xauth -f "$XAUTH_FILE" nmerge - >/dev/null 2>&1; then
    :
else
    echo "Warning: could not extract Xauthority cookie for DISPLAY=$DISPLAY"
fi

# Prefer least-privilege local access for the container's root user.
if command -v xhost >/dev/null 2>&1; then
    xhost +SI:localuser:root >/dev/null 2>&1 || true
fi

echo "DISPLAY=$DISPLAY"
echo "XAUTH file ready: $XAUTH_FILE"
echo "You can now run: docker compose up -d"
