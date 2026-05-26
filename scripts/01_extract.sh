#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 01 - Extracción de DBs y Media (con manejo robusto de nombres)
# ═══════════════════════════════════════════════════════════════
set -e

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
DB_REMOTE_PATH="/sdcard/Android/media/$PACKAGE/$APP_FOLDER/Databases"
adb pull "$DB_REMOTE_PATH/" "$WORKDIR/dbs/" || {
    echo "❌ Error al extraer databases."
    exit 1
}

# ─── Buscar VCF de Contactos ─────────────────────────────────
echo ""
echo "📇 Buscando archivo de Contactos exportado (.vcf)..."
VCF_PATH=$(adb shell "find /sdcard/Download/ -iname '*.vcf' 2>/dev/null | head -n1" | tr -d '\r')
if [ -n "$VCF_PATH" ]; then
    echo "   Encontrado: $VCF_PATH"
    adb pull "$VCF_PATH" "$WORKDIR/contactos.vcf"
else
    echo "   ⚠️  No se encontró archivo .vcf"
fi

# ─── ✨ NUEVO: Extraer multimedia vía TAR (robusto) ───────────
echo ""
echo "🖼️  Extrayendo multimedia via TAR (método robusto)..."
echo "   Esto evita problemas con nombres raros, emojis y caracteres especiales."
echo ""

MEDIA_REMOTE_PATH="/sdcard/Android/media/$PACKAGE/$APP_FOLDER/Media"
MEDIA_TAR="$WORKDIR/media.tar"

# Empaquetar en el dispositivo y transferir como stream
# exec-out evita que adb interprete el output
adb exec-out "tar -cf - -C '/sdcard/Android/media/$PACKAGE/$APP_FOLDER/' Media 2>/dev/null" > "$MEDIA_TAR" || {
    echo "⚠️  tar retornó error, pero continuamos (puede tener archivos con errores)"
}

# Verificar que el tar tiene contenido
TAR_SIZE=$(stat -c%s "$MEDIA_TAR" 2>/dev/null || stat -f%z "$MEDIA_TAR")
if [ "$TAR_SIZE" -lt 1024 ]; then
    echo "❌ El archivo tar está vacío o casi vacío ($TAR_SIZE bytes)."
    echo "   Probando método alternativo..."
    rm -f "$MEDIA_TAR"
    
    # Fallback: usar find + pull individual con sanitización
    bash scripts/01b_extract_media_fallback.sh "$WORKDIR"
else
    echo "   ✅ TAR creado: $(du -h "$MEDIA_TAR" | cut -f1)"
    
    # Extraer localmente con manejo de errores por archivo
    echo ""
    echo "📂 Extrayendo TAR localmente..."
    cd "$WORKDIR"
    
    # --ignore-failed-read: no abortar si un archivo falla
    # --transform: sanitiza nombres con backslash
    tar -xf media.tar \
        --ignore-failed-read \
        2>> "$WORKDIR/tar_errors.log" || {
        echo "   ⚠️  Algunos archivos no pudieron extraerse (ver tar_errors.log)"
    }
    
    # Eliminar el tar para liberar espacio
    rm -f media.tar
    cd - > /dev/null
fi

# ─── Sanitizar nombres problemáticos (post-proceso) ──────────
echo ""
echo "🧹 Sanitizando nombres de archivos problemáticos..."
python3 scripts/sanitize_filenames.py "$WORKDIR/media"

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

mkdir -p "${WORK_DIR:-./workdir}"
echo "$WORKDIR" > "${WORK_DIR}/.last_extraction"
echo ""
echo "➡️  Siguiente paso: python scripts/02_decrypt.py"