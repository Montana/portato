#!/usr/bin/env bash
set -euo pipefail

xhost +local:docker >/dev/null 2>&1 || true

UID_GID="$(id -u):$(id -g)"

docker run --rm \
  --name portato-x11 \
  -e DISPLAY="$DISPLAY" \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v "$PWD":/opt/portato \
  -u "$UID_GID" \
  portato:latest \
  portato gui
