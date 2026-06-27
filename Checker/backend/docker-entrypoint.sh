#!/bin/sh
# Ensure .env exists (fetch from S3 on EC2) before starting the backend process.
set -e
python -m app.core.env_loader
exec "$@"
