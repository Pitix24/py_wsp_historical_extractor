#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# DEMO - Extracción con WhatsApp Personal
# ═══════════════════════════════════════════════════════════════
set -e

# 🔧 ÚNICA DIFERENCIA con el script de producción:
# Package: com.whatsapp (en vez de com.whatsapp.w4b)
# Carpeta: "WhatsApp" (en vez de "WhatsApp Business")

WORKDIR="./demo_whatsapp_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$WORKDIR"/{dbs,media}
cd "$WORKDIR"

echo "📱 Verificando dispositivo..."
adb devices

echo "📦 Extrayendo bases de datos..."
adb pull "/sdcard/Android/media/com.whatsapp/WhatsApp/Databases/" ./dbs/

echo "🖼️  Extrayendo multimedia..."
adb pull "/sdcard/Android/media/com.whatsapp/WhatsApp/Media/" ./media/

echo "✅ Extracción DEMO completa en: $WORKDIR"
