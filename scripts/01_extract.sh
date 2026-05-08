#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 01 - Extracción de DBs y Media desde el dispositivo Android
# ═══════════════════════════════════════════════════════════════
set -e

# Cargar variables de entorno
export $(grep -v '^#' .env | xargs)

# Determinar paths según modo
if [ "$DEMO_MODE" = "true" ]; then
    PACKAGE="com.whatsapp"
    APP_FOLDER="WhatsApp"
    echo "🧪 MODO DEMO - WhatsApp Personal"
else
    PACKAGE="com.whatsapp.w4b"
    APP_FOLDER="WhatsApp Business"
    echo "🏢 MODO PRODUCCIÓN - WhatsApp Business"
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
WORKDIR="${WORK_DIR:-./workdir}/extraction_${TIMESTAMP}"
mkdir -p "$WORKDIR"/{dbs,media}

# ─── Verificar dispositivo ───────────────────────────────────
echo ""
echo "📱 Verificando dispositivo..."
if ! adb devices | grep -q "device$"; then
    echo "❌ Ningún dispositivo conectado. Verifica el cable USB y la depuración."
    exit 1
fi
adb devices

# ─── Extraer bases de datos ──────────────────────────────────
echo ""
echo "📦 Extrayendo bases de datos cifradas..."
adb pull "/sdcard/Android/media/${PACKAGE}/${APP_FOLDER}/Databases/" "$WORKDIR/dbs/" || {
    echo "❌ Error al extraer databases. Verifica que WhatsApp tenga backup activo."
    exit 1
}

# ─── Extraer multimedia ──────────────────────────────────────
echo ""
echo "🖼️  Extrayendo multimedia (esto puede tardar varios minutos)..."
adb pull "/sdcard/Android/media/${PACKAGE}/${APP_FOLDER}/Media/" "$WORKDIR/media/" || {
    echo "⚠️  Advertencia: algunos archivos de media no se pudieron extraer"
}

# ─── Resumen ─────────────────────────────────────────────────
DB_COUNT=$(find "$WORKDIR/dbs" -type f 2>/dev/null | wc -l)
MEDIA_COUNT=$(find "$WORKDIR/media" -type f 2>/dev/null | wc -l)
MEDIA_SIZE=$(du -sh "$WORKDIR/media" 2>/dev/null | cut -f1)

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  ✅ EXTRACCIÓN COMPLETADA                                 ║"
echo "╠═══════════════════════════════════════════════════════════╣"
printf "║  Directorio:      %-40s║\n" "$WORKDIR"
printf "║  Archivos DB:     %-40s║\n" "$DB_COUNT"
printf "║  Archivos media:  %-40s║\n" "$MEDIA_COUNT"
printf "║  Tamaño media:    %-40s║\n" "$MEDIA_SIZE"
echo "╚═══════════════════════════════════════════════════════════╝"

# Guardar path para el siguiente script
echo "$WORKDIR" > .last_extraction
echo ""
echo "➡️  Siguiente paso: python scripts/02_decrypt.py"