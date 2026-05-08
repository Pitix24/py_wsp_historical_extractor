#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# WhatsApp Business Extractor - Setup Script
# ═══════════════════════════════════════════════════════════════

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     WhatsApp Business Extractor - Instalación             ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ─── Detectar OS ─────────────────────────────────────────────
OS="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
fi

echo -e "${GREEN}✓${NC} Sistema operativo detectado: $OS"

# ─── Verificar Python 3.11+ ──────────────────────────────────
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 no encontrado. Instálalo primero.${NC}"
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}✓${NC} Python $PY_VERSION detectado"

# ─── Instalar ADB ────────────────────────────────────────────
if ! command -v adb &> /dev/null; then
    echo -e "${YELLOW}⚠ ADB no encontrado. Instalando...${NC}"
    if [[ "$OS" == "linux" ]]; then
        sudo apt update && sudo apt install -y android-tools-adb
    elif [[ "$OS" == "macos" ]]; then
        brew install android-platform-tools
    fi
fi
echo -e "${GREEN}✓${NC} ADB instalado: $(adb version | head -n1)"

# ─── Instalar rclone ─────────────────────────────────────────
if ! command -v rclone &> /dev/null; then
    echo -e "${YELLOW}⚠ rclone no encontrado. Instalando...${NC}"
    curl https://rclone.org/install.sh | sudo bash
fi
echo -e "${GREEN}✓${NC} rclone instalado: $(rclone version | head -n1)"

# ─── Crear entorno virtual Python ────────────────────────────
if [ ! -d "venv" ]; then
    echo -e "${BLUE}📦 Creando entorno virtual...${NC}"
    python3 -m venv venv
fi

source venv/bin/activate
echo -e "${GREEN}✓${NC} Entorno virtual activado"

# ─── Instalar dependencias Python ────────────────────────────
echo -e "${BLUE}📦 Instalando dependencias Python...${NC}"
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}✓${NC} Dependencias instaladas"

# ─── Crear directorios de trabajo ────────────────────────────
mkdir -p workdir logs archivos_procesados
echo -e "${GREEN}✓${NC} Directorios de trabajo creados"

# ─── Configurar .env ─────────────────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠ Archivo .env creado desde .env.example${NC}"
    echo -e "${YELLOW}  Edítalo antes de ejecutar los scripts: nano .env${NC}"
fi

# ─── Hacer scripts ejecutables ───────────────────────────────
chmod +x scripts/*.sh
echo -e "${GREEN}✓${NC} Scripts marcados como ejecutables"

# ─── Resumen final ───────────────────────────────────────────
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          ✅ INSTALACIÓN COMPLETADA EXITOSAMENTE           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Próximos pasos:${NC}"
echo "  1. Editar .env con tus credenciales:  nano .env"
echo "  2. Configurar rclone con Google Drive: rclone config"
echo "  3. Crear schema en tu base de datos:"
echo "     mysql -u root -p < sql/schema_mysql.sql"
echo "  4. Conectar el dispositivo Android vía USB"
echo "  5. Ejecutar la extracción: ./scripts/01_extract.sh"
echo ""
echo -e "${YELLOW}📘 Documentación:${NC}"
echo "  - Guía DEMO:       docs/DEMO_GUIDE.md"
echo "  - Guía Producción: docs/PRODUCTION_GUIDE.md"
echo "  - Seguridad:       docs/SECURITY.md"
echo ""
