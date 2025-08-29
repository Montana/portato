#!/usr/bin/env bash
set -euo pipefail

UID_GID="$(id -u):$(id -g)"
VNC_PASSWORD="${VNC_PASSWORD:-portato}"

docker run --rm \
  --name portato-vnc \
  -p 5901:5901 \
  -e VNC_PASSWORD="${VNC_PASSWORD}" \
  -e DISPLAY=":99" \
  -v "$PWD":/opt/portato \
  -u "$UID_GID" \
  portato:latest \
  /usr/local/bin/headless.sh
