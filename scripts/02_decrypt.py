#!/usr/bin/env python3
"""
02 - Desencripta las bases de datos msgstore.db y wa.db
Usa la clave E2E de 64 caracteres del backup.
"""
import sys
import glob
import shutil
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.config import WA_KEY, WORK_DIR, print_mode

print_mode()

# ─── Localizar última extracción ─────────────────────────────
last_extraction_file = Path(".last_extraction")
if last_extraction_file.exists():
    workdir = Path(last_extraction_file.read_text().strip())
else:
    # Buscar la más reciente
    candidates = sorted(WORK_DIR.glob("extraction_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        print("❌ No se encontró ninguna extracción previa. Ejecuta 01_extract.sh primero.")
        sys.exit(1)
    workdir = candidates[0]

print(f"📂 Trabajando sobre: {workdir}")

# ─── Validar clave ───────────────────────────────────────────
if not WA_KEY or len(WA_KEY) != 64:
    print("❌ WA_KEY debe ser una clave hexadecimal de 64 caracteres.")
    print("   Actívala en WhatsApp: Ajustes → Chats → Copia de seguridad → Cifrado E2E")
    sys.exit(1)

# ─── Localizar archivos cifrados ─────────────────────────────
dbs_dir = workdir / "dbs"
crypt_files = [p for p in dbs_dir.rglob("msgstore*.crypt15") if "-increment-" not in p.name]
crypt_files = sorted(
    crypt_files,
    key=lambda p: p.stat().st_mtime,
    reverse=True
)

if not crypt_files:
    print(f"❌ No se encontraron archivos .crypt15 en {dbs_dir}")
    sys.exit(1)

latest_msgstore = crypt_files[0]
print(f"🔓 Desencriptando: {latest_msgstore.name}")

# ─── Desencriptar msgstore.db ────────────────────────────────
output_msgstore = workdir / "msgstore.db"
result = subprocess.run(
    ["wadecrypt", WA_KEY, str(latest_msgstore), str(output_msgstore)],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print(f"❌ Error al desencriptar: {result.stderr}")
    sys.exit(1)

print(f"   ✅ {output_msgstore.name} ({output_msgstore.stat().st_size / 1024 / 1024:.1f} MB)")

# ─── Copiar/desencriptar wa.db ───────────────────────────────
wa_files = list(dbs_dir.rglob("wa.db*"))
wa_output = workdir / "wa.db"

for wa in wa_files:
    if wa.name.endswith(".crypt15"):
        subprocess.run(
            ["wadecrypt", WA_KEY, str(wa), str(wa_output)],
            check=True
        )
        break
    elif wa.name == "wa.db":
        shutil.copy(wa, wa_output)
        break

if wa_output.exists():
    print(f"   ✅ wa.db ({wa_output.stat().st_size / 1024:.1f} KB)")
else:
    print("⚠️  wa.db no encontrado. Los contactos no tendrán nombres guardados.")

print("\n✅ Desencriptación completa.")
print("➡️  Siguiente paso: python scripts/03_process_mysql.py")
