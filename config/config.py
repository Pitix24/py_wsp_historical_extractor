"""
Configuración central del extractor.
Carga variables de entorno desde .env y expone constantes tipadas.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════════════════════
# MODO DE OPERACIÓN
# ═══════════════════════════════════════════════════════════════
DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() == "true"

if DEMO_MODE:
    PACKAGE = "com.whatsapp"
    APP_FOLDER = "WhatsApp"
    DB_NAME_DEFAULT = "whatsapp_business_demo"
    MODE_LABEL = "🧪 DEMO (WhatsApp Personal)"
else:
    PACKAGE = "com.whatsapp.w4b"
    APP_FOLDER = "WhatsApp Business"
    DB_NAME_DEFAULT = "whatsapp_business"
    MODE_LABEL = "🏢 PRODUCCIÓN (WhatsApp Business)"

# ═══════════════════════════════════════════════════════════════
# RUTAS ANDROID
# ═══════════════════════════════════════════════════════════════
ANDROID_DB_PATH = f"/sdcard/Android/media/{PACKAGE}/{APP_FOLDER}/Databases/"
ANDROID_MEDIA_PATH = f"/sdcard/Android/media/{PACKAGE}/{APP_FOLDER}/Media/"

# ═══════════════════════════════════════════════════════════════
# RUTAS LOCALES
# ═══════════════════════════════════════════════════════════════
WORK_DIR = Path(os.environ.get("WORK_DIR", "./workdir"))
MEDIA_OUTPUT = Path(os.environ.get("MEDIA_OUTPUT", "./archivos_procesados"))
LOG_DIR = Path(os.environ.get("LOG_DIR", "./logs"))

for d in [WORK_DIR, MEDIA_OUTPUT, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# BASE DE DATOS
# ═══════════════════════════════════════════════════════════════
DB_ENGINE = os.environ.get("DB_ENGINE", "mysql").lower()
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", 3306)),
    "user": os.environ.get("DB_USER", "whatsapp_user"),
    "password": os.environ.get("DB_PASS", ""),
    "database": os.environ.get("DB_NAME", DB_NAME_DEFAULT),
}

# ═══════════════════════════════════════════════════════════════
# CREDENCIALES WHATSAPP
# ═══════════════════════════════════════════════════════════════
WA_KEY = os.environ.get("WA_KEY", "")

# ═══════════════════════════════════════════════════════════════
# GOOGLE DRIVE
# ═══════════════════════════════════════════════════════════════
RCLONE_REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive-whatsapp")
RCLONE_CRYPT_REMOTE = os.environ.get("RCLONE_CRYPT_REMOTE", "gdrive-crypt")
DRIVE_BASE_PATH = os.environ.get("DRIVE_BASE_PATH", "WhatsApp_Business_Backup")

# ═══════════════════════════════════════════════════════════════
# PREFERENCIAS DE EXTRACCIÓN
# ═══════════════════════════════════════════════════════════════
EXTRACT_STICKERS = os.environ.get("EXTRACT_STICKERS", "false").lower() == "true"

# ═══════════════════════════════════════════════════════════════
# AUDITORÍA
# ═══════════════════════════════════════════════════════════════
AUDIT_USER = os.environ.get("AUDIT_USER", os.environ.get("USER", "unknown"))


def print_mode():
    print(f"\n{'=' * 60}")
    print(f"  MODO: {MODE_LABEL}")
    print(f"  DB:   {DB_ENGINE} @ {DB_CONFIG['host']}/{DB_CONFIG['database']}")
    print(f"  USER: {AUDIT_USER}")
    print(f"{'=' * 60}\n")