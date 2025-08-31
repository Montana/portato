#!/usr/bin/env bash
set -euo pipefail

if [ $# -eq 0 ]; then
    echo "Usage: $0 YOUR_DOCKERHUB_USERNAME"
    echo "Example: $0 johndoe"
    exit 1
fi

USERNAME=$1
IMAGE_NAME="portato"
TAG="latest"

echo "Building multi-architecture image for Docker Hub..."
echo "Username: $USERNAME"
echo "Image: $USERNAME/$IMAGE_NAME:$TAG"

docker buildx create --name portato-builder --use || true

docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --tag "$USERNAME/$IMAGE_NAME:$TAG" \
    --file docker/Dockerfile.arm64 \
    --push \
    .

echo "Image: $USERNAME/$IMAGE_NAME:$TAG"
echo "Platforms: linux/amd64, linux/arm64"
echo ""
echo "To pull and run:"
echo "  docker pull $USERNAME/$IMAGE_NAME:$TAG"
echo "  docker run --rm $USERNAME/$IMAGE_NAME:$TAG --help"
