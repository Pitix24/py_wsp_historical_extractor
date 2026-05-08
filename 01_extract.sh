#!/bin/bash
set -e

echo "📱 Verificando conexión con dispositivo..."
adb devices

WORKDIR="./whatsapp_extraction_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$WORKDIR"/{dbs,media,output}
cd "$WORKDIR"

echo "📦 Extrayendo bases de datos cifradas..."
# Las DBs cifradas quedan en la carpeta de backups (accesible sin root)
adb pull /sdcard/Android/media/com.whatsapp.w4b/WhatsApp\ Business/Databases/ ./dbs/

echo "🖼️  Extrayendo toda la carpeta Media (esto puede tardar)..."
adb pull /sdcard/Android/media/com.whatsapp.w4b/WhatsApp\ Business/Media/ ./media/

echo "✅ Extracción completa. Archivos en: $WORKDIR"
echo "➡️  Siguiente paso: ejecutar 02_decrypt.py con tu clave de 64 caracteres"
