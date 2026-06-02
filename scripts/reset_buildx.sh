#!/bin/bash
# Fix Docker buildx permission issues (run before docker compose build if you see permission denied).
set -e
sudo chown -R "$USER:$USER" ~/.docker
sudo chmod -R 755 ~/.docker
docker buildx rm default || true
docker buildx create --use
