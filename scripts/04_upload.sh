#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 04 - Sube los archivos procesados a Google Drive (cifrado)
# ═══════════════════════════════════════════════════════════════
set -e

export $(grep -v '^#' .env | xargs)

# ─── Verificar rclone ────────────────────────────────────────
if ! command -v rclone &> /dev/null; then
    echo "❌ rclone no instalado. Ejecuta setup.sh"
    exit 1
fi

# ─── Verificar configuración de remote ───────────────────────
if ! rclone listremotes | grep -q "^${RCLONE_CRYPT_REMOTE}:"; then
    echo "⚠️  Remote '${RCLONE_CRYPT_REMOTE}' no configurado."
    echo "   Ejecuta: rclone config"
    echo ""
    echo "   Pasos:"
    echo "   1. Crear remote 'gdrive-whatsapp' tipo drive (Google Drive)"
    echo "   2. Crear remote 'gdrive-crypt' tipo crypt"
    echo "      remote: gdrive-whatsapp:${DRIVE_BASE_PATH}_Encrypted"
    exit 1
fi

# ─── Determinar modo ─────────────────────────────────────────
if [ "$DEMO_MODE" = "true" ]; then
    SUBFOLDER="demo_$(date +%Y%m%d_%H%M%S)"
else
    SUBFOLDER="historico_$(date +%Y%m%d)"
fi

DEST="${RCLONE_CRYPT_REMOTE}:${SUBFOLDER}"
SOURCE="${MEDIA_OUTPUT:-./archivos_procesados}"

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  ☁️  SUBIDA A GOOGLE DRIVE (CIFRADA)                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo "  Origen:  $SOURCE"
echo "  Destino: $DEST"
echo ""

# ─── Subir con progreso ──────────────────────────────────────
LOG_FILE="${LOG_DIR:-./logs}/upload_$(date +%Y%m%d_%H%M%S).log"

rclone copy "$SOURCE" "$DEST" \
    --progress \
    --transfers 8 \
    --checkers 16 \
    --drive-chunk-size 64M \
    --log-file="$LOG_FILE" \
    --log-level INFO \
    --stats 30s \
    --retries 5 \
    --low-level-retries 10

# ─── Verificar integridad ────────────────────────────────────
echo ""
echo "🔍 Verificando integridad (one-way check)..."
rclone check "$SOURCE" "$DEST" --one-way 2>&1 | tail -5

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  ✅ SUBIDA COMPLETADA                                     ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo "  📂 Ubicación: $DEST"
echo "  📄 Log: $LOG_FILE"
echo ""
echo "➡️  Siguiente paso: python scripts/05_verify.py"
