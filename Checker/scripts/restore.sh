#!/bin/bash
# Restore MySQL database from backup file

set -e

BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup_file.sql>"
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: $BACKUP_FILE"
  exit 1
fi

echo "Restoring from $BACKUP_FILE..."

mysql \
  -h "${MYSQL_HOST:-mysql}" \
  -P "${MYSQL_PORT:-3306}" \
  -u "${MYSQL_USER:-validator}" \
  -p"${MYSQL_PASSWORD:-validator_secret}" \
  "${MYSQL_DATABASE:-yaml_terraform_validator}" \
  < "$BACKUP_FILE"

echo "Restore completed successfully"
