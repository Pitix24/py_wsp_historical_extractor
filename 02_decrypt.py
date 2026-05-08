import subprocess
import glob
import os
from pathlib import Path

# 🔑 Pon aquí tu clave de 64 caracteres del backup E2E
KEY = os.environ.get("WA_KEY") or input("Pega tu clave de 64 chars: ").strip()

workdir = Path(".")
# Buscar el archivo msgstore.db.crypt15 más reciente
crypt_files = sorted(glob.glob("dbs/**/msgstore*.crypt15", recursive=True), 
                     key=os.path.getmtime, reverse=True)

if not crypt_files:
    raise FileNotFoundError("No se encontraron archivos .crypt15")

latest = crypt_files[0]
print(f"🔓 Desencriptando: {latest}")

subprocess.run([
    "wadecrypt", latest, "msgstore.db", "--key", KEY
], check=True)

# Desencriptar wa.db también si es necesario (a veces está sin cifrar)
wa_files = glob.glob("dbs/**/wa.db*", recursive=True)
for wa in wa_files:
    if wa.endswith(".crypt15"):
        subprocess.run(["wadecrypt", wa, "wa.db", "--key", KEY], check=True)
    else:
        # Copiar directamente
        import shutil
        shutil.copy(wa, "wa.db")

print("✅ Bases de datos desencriptadas: msgstore.db y wa.db")
