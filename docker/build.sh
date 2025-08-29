#!/usr/bin/env bash
set -euo pipefail
docker build -t portato:latest -f docker/Dockerfile .
