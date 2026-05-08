import sqlite3
import pymysql  # pip install pymysql cryptography
import hashlib
import os
import shutil
from pathlib import Path
from datetime import datetime, timezone
from tqdm import tqdm

# ═══════════════════════════════════════════════════════════════
# DETECCIÓN DE MODO (PRODUCCIÓN VS DEMO)
# ═══════════════════════════════════════════════════════════════
# Si existe el archivo "demo_extract.sh", estamos en modo DEMO
# Si no, en modo PRODUCCIÓN

DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"

if DEMO_MODE:
    print("🧪 MODO DEMO: Usando WhatsApp Personal")
    PACKAGE = "com.whatsapp"
    APP_FOLDER = "WhatsApp"
    DB_NAME = "whatsapp_business_demo"  # DB separada para no mezclar
else:
    print("🏢 MODO PRODUCCIÓN: Usando WhatsApp Business")
    PACKAGE = "com.whatsapp.w4b"
    APP_FOLDER = "WhatsApp Business"
    DB_NAME = "whatsapp_business"

MEDIA_PATH = f"/sdcard/Android/media/{PACKAGE}/{APP_FOLDER}/Media/"
DB_PATH = f"/sdcard/Android/media/{PACKAGE}/{APP_FOLDER}/Databases/"

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════
MYSQL_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", 3306)),
    "user": os.environ.get("DB_USER", "whatsapp_user"),
    "password": os.environ.get("DB_PASS"),
    "database": "whatsapp_business",
    "charset": "utf8mb4"
}

MSGSTORE = "msgstore.db"       # SQLite extraído de WhatsApp
WA_DB = "wa.db"
MEDIA_SRC = Path("./media")
ARCHIVOS_OUTPUT = Path("./archivos_procesados")
ARCHIVOS_OUTPUT.mkdir(exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# CONEXIONES
# ═══════════════════════════════════════════════════════════════
print("🔌 Conectando a MySQL/MariaDB...")
mysql_conn = pymysql.connect(**MYSQL_CONFIG)
mysql_cur = mysql_conn.cursor(pymysql.cursors.DictCursor)

wa_sqlite = sqlite3.connect(WA_DB)
wa_sqlite.row_factory = sqlite3.Row
msg_sqlite = sqlite3.connect(MSGSTORE)
msg_sqlite.row_factory = sqlite3.Row

# ═══════════════════════════════════════════════════════════════
# UTILIDADES
# ═══════════════════════════════════════════════════════════════
def ts_to_datetime(ts_ms):
    if not ts_ms:
        return None
    return datetime.fromtimestamp(ts_ms/1000, tz=timezone.utc)

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

# ═══════════════════════════════════════════════════════════════
# 1. REGISTRAR INICIO DE EXTRACCIÓN (AUDITORÍA)
# ═══════════════════════════════════════════════════════════════
mysql_cur.execute("""
    INSERT INTO extracciones_log (usuario, tipo, inicio, estado)
    VALUES (%s, %s, %s, %s)
""", (os.environ.get("USER", "system"), "historico", datetime.now(), "exitoso"))
extraccion_id = mysql_cur.lastrowid
mysql_conn.commit()

# ═══════════════════════════════════════════════════════════════
# 2. INSERTAR CONTACTOS (UPSERT)
# ═══════════════════════════════════════════════════════════════
print("📇 Importando contactos...")
contactos_map = {}  # jid -> contacto_id

for row in wa_sqlite.execute("""
    SELECT jid, display_name, wa_name, number, status 
    FROM wa_contacts 
    WHERE jid LIKE '%@s.whatsapp.net'
"""):
    mysql_cur.execute("""
        INSERT INTO contactos (jid, numero, nombre_guardado, nombre_whatsapp, estado)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            nombre_guardado = VALUES(nombre_guardado),
            nombre_whatsapp = VALUES(nombre_whatsapp),
            estado = VALUES(estado)
    """, (
        row["jid"],
        row["number"] or row["jid"].split("@")[0],
        row["display_name"],
        row["wa_name"],
        row["status"]
    ))
    mysql_cur.execute("SELECT id FROM contactos WHERE jid = %s", (row["jid"],))
    contactos_map[row["jid"]] = mysql_cur.fetchone()["id"]

mysql_conn.commit()
print(f"   ✅ {len(contactos_map)} contactos importados")

# ═══════════════════════════════════════════════════════════════
# 3. PROCESAR MENSAJES EN BATCH (BULK INSERT)
# ═══════════════════════════════════════════════════════════════
print("💬 Importando mensajes...")

chats = msg_sqlite.execute("""
    SELECT c._id, j.raw_string as jid
    FROM chat c
    JOIN jid j ON c.jid_row_id = j._id
    WHERE j.raw_string LIKE '%@s.whatsapp.net'
""").fetchall()

stats = {"mensajes": 0, "archivos": 0, "errores": 0}

for chat in tqdm(chats, desc="Chats"):
    jid = chat["jid"]
    chat_id = chat["_id"]
    contacto_id = contactos_map.get(jid)
    
    if not contacto_id:
        # Contacto no estaba en wa.db (número sin guardar), crearlo
        numero = jid.split("@")[0]
        mysql_cur.execute("""
            INSERT IGNORE INTO contactos (jid, numero) VALUES (%s, %s)
        """, (jid, numero))
        mysql_cur.execute("SELECT id FROM contactos WHERE jid = %s", (jid,))
        contacto_id = mysql_cur.fetchone()["id"]
        contactos_map[jid] = contacto_id
    
    mensajes = msg_sqlite.execute("""
        SELECT m._id, m.from_me, m.timestamp, m.text_data, m.message_type,
               mm.file_path, mm.mime_type, mm.media_name, mm.file_size, mm.media_caption
        FROM message m
        LEFT JOIN message_media mm ON m._id = mm.message_row_id
        WHERE m.chat_row_id = ?
        ORDER BY m.timestamp ASC
    """, (chat_id,)).fetchall()
    
    # Bulk insert de mensajes
    batch_mensajes = []
    for m in mensajes:
        tipo = "text"
        if m["mime_type"]:
            if "image" in m["mime_type"]: tipo = "image"
            elif "video" in m["mime_type"]: tipo = "video"
            elif "audio" in m["mime_type"]: tipo = "audio"
            elif m["mime_type"]: tipo = "document"
        
        wa_msg_id = f"{jid}_{m['_id']}"  # ID único compuesto
        batch_mensajes.append((
            wa_msg_id, contacto_id, bool(m["from_me"]), tipo,
            m["text_data"] or "", m["media_caption"],
            m["timestamp"], ts_to_datetime(m["timestamp"]),
            bool(m["file_path"])
        ))
    
    if batch_mensajes:
        mysql_cur.executemany("""
            INSERT IGNORE INTO mensajes 
            (wa_id, contacto_id, from_me, tipo, contenido, caption, 
             timestamp_ms, fecha, tiene_archivo)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, batch_mensajes)
        stats["mensajes"] += len(batch_mensajes)
    
    # Procesar archivos multimedia
    for m in mensajes:
        if not m["file_path"]:
            continue
        wa_msg_id = f"{jid}_{m['_id']}"
        
        # Buscar archivo físico
        src_path = MEDIA_SRC / m["file_path"].replace("Media/", "WhatsApp Business/Media/")
        if not src_path.exists():
            matches = list(MEDIA_SRC.rglob(os.path.basename(m["file_path"])))
            src_path = matches[0] if matches else None
        
        if src_path and src_path.exists():
            # Copiar a estructura por contacto
            dest_dir = ARCHIVOS_OUTPUT / str(contacto_id)
            dest_dir.mkdir(exist_ok=True)
            dest_path = dest_dir / src_path.name
            if not dest_path.exists():
                shutil.copy2(src_path, dest_path)
            
            # Registrar en DB
            mysql_cur.execute("SELECT id FROM mensajes WHERE wa_id = %s", (wa_msg_id,))
            msg_row = mysql_cur.fetchone()
            if msg_row:
                mysql_cur.execute("""
                    INSERT IGNORE INTO archivos 
                    (mensaje_id, contacto_id, nombre_original, nombre_local,
                     ruta_local, mime_type, tamano_bytes, hash_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    msg_row["id"], contacto_id,
                    m["media_name"] or src_path.name,
                    dest_path.name, str(dest_path),
                    m["mime_type"], m["file_size"],
                    sha256_file(dest_path)
                ))
                stats["archivos"] += 1
    
    mysql_conn.commit()  # Commit por chat para no perder progreso

# ═══════════════════════════════════════════════════════════════
# 4. ACTUALIZAR ESTADÍSTICAS POR CONTACTO
# ═══════════════════════════════════════════════════════════════
print("📊 Calculando estadísticas...")
mysql_cur.execute("""
    UPDATE contactos c
    SET 
        total_mensajes = (SELECT COUNT(*) FROM mensajes WHERE contacto_id = c.id),
        fecha_primer_mensaje = (SELECT MIN(fecha) FROM mensajes WHERE contacto_id = c.id),
        fecha_ultimo_mensaje = (SELECT MAX(fecha) FROM mensajes WHERE contacto_id = c.id)
""")

# Cerrar log de auditoría
mysql_cur.execute("""
    UPDATE extracciones_log 
    SET fin = %s, chats_procesados = %s, mensajes_total = %s, archivos_total = %s
    WHERE id = %s
""", (datetime.now(), len(chats), stats["mensajes"], stats["archivos"], extraccion_id))

mysql_conn.commit()
mysql_conn.close()

print(f"""
╔══════════════════════════════════════════════════════╗
║  ✅ PROCESAMIENTO COMPLETO                           ║
╠══════════════════════════════════════════════════════╣
║  Chats procesados:    {len(chats):>10}                  ║
║  Mensajes totales:    {stats['mensajes']:>10}                  ║
║  Archivos copiados:   {stats['archivos']:>10}                  ║
║  Errores:             {stats['errores']:>10}                  ║
╚══════════════════════════════════════════════════════╝

📂 Resultado en: {ARCHIVOS_OUTPUT}
""")
