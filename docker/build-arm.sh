#!/usr/bin/env bash
set -euo pipefail

echo "Building Portato for ARM64 architecture..."
echo "Using Ubuntu-based image for better ARM64 compatibility"

docker build -t portato:arm64 -f docker/Dockerfile.arm64 .

echo "Build complete! Image tagged as portato:arm64"
echo "Run with: docker run -it portato:arm64"
