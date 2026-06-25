#!/bin/bash
# Backup MySQL database for YAML & Terraform AI Validator

set -e

BACKUP_DIR="${BACKUP_DIR:-/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql"

mkdir -p "$BACKUP_DIR"

echo "Starting backup to $BACKUP_FILE..."

mysqldump \
  -h "${MYSQL_HOST:-mysql}" \
  -P "${MYSQL_PORT:-3306}" \
  -u "${MYSQL_USER:-validator}" \
  -p"${MYSQL_PASSWORD:-validator_secret}" \
  "${MYSQL_DATABASE:-yaml_terraform_validator}" \
  > "$BACKUP_FILE"

echo "Backup completed: $BACKUP_FILE"
echo "Size: $(du -h "$BACKUP_FILE" | cut -f1)"
