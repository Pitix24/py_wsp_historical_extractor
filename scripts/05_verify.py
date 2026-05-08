#!/usr/bin/env python3
"""
05 - Verifica la integridad de los datos importados.
Genera un reporte de consistencia entre BD, archivos locales y Drive.
"""
import sys
import subprocess
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.config import (
    DB_ENGINE, DB_CONFIG, MEDIA_OUTPUT, 
    RCLONE_CRYPT_REMOTE, print_mode
)

print_mode()

# ═══════════════════════════════════════════════════════════════
# 1. VERIFICAR BASE DE DATOS
# ═══════════════════════════════════════════════════════════════
print("🗄️  Verificando base de datos...")

if DB_ENGINE in ("mysql", "mariadb"):
    import pymysql
    conn = pymysql.connect(**DB_CONFIG, charset="utf8mb4",
                           cursorclass=pymysql.cursors.DictCursor)
else:
    import pyodbc, os
    driver = os.environ.get("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    cs = (f"DRIVER={{{driver}}};SERVER={DB_CONFIG['host']},{DB_CONFIG['port']};"
          f"DATABASE={DB_CONFIG['database']};UID={DB_CONFIG['user']};"
          f"PWD={DB_CONFIG['password']};TrustServerCertificate=yes")
    conn = pyodbc.connect(cs)

cur = conn.cursor()

# Conteos
queries = {
    "Contactos":       "SELECT COUNT(*) AS c FROM contactos",
    "Mensajes":        "SELECT COUNT(*) AS c FROM mensajes",
    "Archivos en BD":  "SELECT COUNT(*) AS c FROM archivos",
    "Chats con media": "SELECT COUNT(DISTINCT contacto_id) AS c FROM archivos",
}

results = {}
for name, q in queries.items():
    cur.execute(q)
    row = cur.fetchone()
    val = row["c"] if isinstance(row, dict) else row[0]
    results[name] = val

# Distribución por tipo
cur.execute("SELECT tipo, COUNT(*) as c FROM mensajes GROUP BY tipo")
tipos = {r["tipo"] if isinstance(r, dict) else r[0]: 
         r["c"] if isinstance(r, dict) else r[1] for r in cur.fetchall()}

# Top 5 contactos
cur.execute("""
    SELECT nombre_guardado, numero, total_mensajes 
    FROM contactos 
    ORDER BY total_mensajes DESC 
    LIMIT 5
""")
top = cur.fetchall()

conn.close()

# ═══════════════════════════════════════════════════════════════
# 2. VERIFICAR ARCHIVOS LOCALES
# ═══════════════════════════════════════════════════════════════
print("📂 Verificando archivos locales...")

local_files = list(MEDIA_OUTPUT.rglob("*"))
local_count = sum(1 for f in local_files if f.is_file())
local_size_mb = sum(f.stat().st_size for f in local_files if f.is_file()) / 1024 / 1024

# Distribución por extensión
ext_counter = Counter(f.suffix.lower() for f in local_files if f.is_file())

# ═══════════════════════════════════════════════════════════════
# 3. VERIFICAR GOOGLE DRIVE (vía rclone)
# ═══════════════════════════════════════════════════════════════
print("☁️  Verificando Google Drive...")
try:
    result = subprocess.run(
        ["rclone", "size", f"{RCLONE_CRYPT_REMOTE}:"],
        capture_output=True, text=True, timeout=60
    )
    drive_info = result.stdout if result.returncode == 0 else "No disponible"
except Exception as e:
    drive_info = f"Error: {e}"

# ═══════════════════════════════════════════════════════════════
# REPORTE
# ═══════════════════════════════════════════════════════════════
print(f"""
╔═══════════════════════════════════════════════════════════╗
║            📊 REPORTE DE VERIFICACIÓN                     ║
╚═══════════════════════════════════════════════════════════╝

🗄️  BASE DE DATOS ({DB_ENGINE})
""")
for k, v in results.items():
    print(f"   {k:<20} {v:>10,}")

print(f"\n📝 DISTRIBUCIÓN DE MENSAJES POR TIPO")
for tipo, count in sorted(tipos.items(), key=lambda x: -x[1]):
    print(f"   {tipo:<15} {count:>10,}")

print(f"\n🏆 TOP 5 CLIENTES CON MÁS MENSAJES")
for row in top:
    nombre = row["nombre_guardado"] if isinstance(row, dict) else row[0]
    numero = row["numero"] if isinstance(row, dict) else row[1]
    total = row["total_mensajes"] if isinstance(row, dict) else row[2]
    print(f"   {(nombre or 'Sin nombre')[:30]:<30} {numero:<15} {total:>8,}")

print(f"\n📂 ARCHIVOS LOCALES")
print(f"   Total archivos:    {local_count:>10,}")
print(f"   Tamaño total:      {local_size_mb:>10.1f} MB")
print(f"\n   Top extensiones:")
for ext, count in ext_counter.most_common(5):
    print(f"   {ext or '(sin ext)':<10} {count:>10,}")

print(f"\n☁️  GOOGLE DRIVE")
print(f"   {drive_info}")

# Alertas
print(f"\n⚠️  ALERTAS")
if results["Archivos en BD"] != local_count:
    print(f"   ⚠️  Discrepancia: {results['Archivos en BD']} archivos en BD vs {local_count} locales")
else:
    print(f"   ✅ BD y archivos locales coinciden")

print()
