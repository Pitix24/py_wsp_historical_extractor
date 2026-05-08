#!/bin/bash
set -e

REMOTE="gdrive-whatsapp"
REMOTE_PATH="WhatsApp_Business_Backup/historico_$(date +%Y%m%d)"
LOCAL_PATH="./output"

echo "☁️  Subiendo a Google Drive: $REMOTE:$REMOTE_PATH"

rclone copy "$LOCAL_PATH" "$REMOTE:$REMOTE_PATH" \
    --progress \
    --transfers 8 \
    --checkers 16 \
    --drive-chunk-size 64M \
    --log-file=upload.log \
    --log-level INFO \
    --stats 30s

echo "✅ Subida completa. Log en: upload.log"

# Verificar integridad
echo "🔍 Verificando integridad..."
rclone check "$LOCAL_PATH" "$REMOTE:$REMOTE_PATH" --one-way
