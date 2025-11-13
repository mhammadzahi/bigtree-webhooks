#!/bin/bash

# ==== CONFIG ====
BACKUP_ROOT="/home/mohammad/backups"
DB_USER="bt_admin"
DB_PASS="Day@57!ihaz"
DB_NAME="bt_wp"
WEB_DIR="/var/www/bigtree-group"
# ================

# Remove Old Backup
sudo rm -rf $BACKUP_ROOT

# Date and time formatting
BACKUP_DATE=$(date +%d-%m-%Y)
BACKUP_TIME=$(date +%H-%M)

# Folder for today's backups
BACKUP_DIR="$BACKUP_ROOT/$BACKUP_DATE"
mkdir -p "$BACKUP_DIR"

# File names with time
FILES_BACKUP="$BACKUP_DIR/$BACKUP_TIME.tar.gz"
DB_BACKUP="$BACKUP_DIR/$BACKUP_TIME.sql"

# ---- Backup Process ----
echo "[$(date)] Starting BigTree backup..."

# Backup files
echo "Creating file archive: $FILES_BACKUP"
tar -czvf "$FILES_BACKUP" "$WEB_DIR"

# Backup database
echo "Dumping database to: $DB_BACKUP"
mysqldump -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" > "$DB_BACKUP"

echo "[$(date)] Backup completed successfully!"
echo "Files saved in: $BACKUP_DIR"

