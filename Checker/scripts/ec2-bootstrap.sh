#!/usr/bin/env bash
# One-time EC2 setup — run once on a fresh Ubuntu instance, then rely on fast CI/CD deploys.
set -euo pipefail

sudo apt-get update -y
sudo apt-get install -y git curl unzip

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER" || true
fi
sudo systemctl enable docker
sudo systemctl start docker

if ! docker compose version >/dev/null 2>&1; then
  sudo apt-get install -y docker-compose-plugin
fi

if ! command -v aws >/dev/null 2>&1; then
  curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip
  unzip -o /tmp/awscliv2.zip -d /tmp
  sudo /tmp/aws/install
  rm -rf /tmp/aws /tmp/awscliv2.zip
fi

echo "Bootstrap complete. Add GHCR_PULL_TOKEN secret for private images, then push to deploy."
