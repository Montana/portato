#!/usr/bin/env bash
set -euo pipefail

export DISPLAY=${DISPLAY:-:99}

Xvfb "$DISPLAY" -screen 0 1280x800x24 -ac +extension GLX +render -noreset &
sleep 1

x11vnc -display "$DISPLAY" -shared -forever -passwd "${VNC_PASSWORD:-portato}" -rfbport 5901 -bg

exec portato gui
