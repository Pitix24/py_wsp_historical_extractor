#!/usr/bin/env python3
"""
03 - Procesa las DBs desencriptadas y carga los datos en MySQL/MariaDB/SQL Server.
Copia los archivos multimedia a la estructura organizada por contacto.
"""
import sys
import os
import sqlite3
import hashlib
import shutil
import traceback
import pyodbc
import pymysql
from pathlib import Path
from datetime import datetime, timezone

from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.config import (
    DB_ENGINE, DB_CONFIG, WORK_DIR, MEDIA_OUTPUT, AUDIT_USER,
    DEMO_MODE, APP_FOLDER, EXTRACT_STICKERS, print_mode
)

print_mode()

# ═══════════════════════════════════════════════════════════════
# ADAPTADOR DE BASE DE DATOS
# ═══════════════════════════════════════════════════════════════
class DBAdapter:
    """Wrapper para abstraer MySQL/MariaDB vs SQL Server."""
    
    def __init__(self, engine, config):
        self.engine = engine
        if engine in ("mysql", "mariadb"):
            import pymysql
            self.conn = pymysql.connect(
                **config,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor
            )
            self.ph = "%s"  # placeholder
            self.on_dup = "ON DUPLICATE KEY UPDATE"
            self.insert_ignore = "INSERT IGNORE"
        elif engine == "sqlserver":
            import pyodbc
            driver = os.environ.get("DB_DRIVER", "ODBC Driver 18 for SQL Server")
            cs = (
                f"DRIVER={{{driver}}};SERVER={config['host']},{config['port']};"
                f"DATABASE={config['database']};UID={config['user']};PWD={config['password']};"
                f"TrustServerCertificate=yes"
            )
            self.conn = pyodbc.connect(cs)
            self.ph = "?"
            self.on_dup = None
            self.insert_ignore = "INSERT"
        else:
            raise ValueError(f"Engine no soportado: {engine}")
    
    def cursor(self):
        return self.conn.cursor()
    
    def commit(self):
        self.conn.commit()
    
    def close(self):
        self.conn.close()


# ═══════════════════════════════════════════════════════════════
# UTILIDADES
# ═══════════════════════════════════════════════════════════════
def ts_to_datetime(ts_ms):
    if not ts_ms:
        return None
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).replace(tzinfo=None)

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def detect_tipo(mime_type, message_type):
    if not mime_type:
        return "text"
    m = mime_type.lower()
    if "image" in m: return "image"
    if "video" in m: return "video"
    if "audio" in m: return "audio"
    if "sticker" in m: return "sticker"
    return "document"


# ═══════════════════════════════════════════════════════════════
# LOCALIZAR ÚLTIMA EXTRACCIÓN
# ═══════════════════════════════════════════════════════════════
last_extraction_file = WORK_DIR / ".last_extraction"
if last_extraction_file.exists():
    workdir = Path(last_extraction_file.read_text().strip())
else:
    candidates = sorted(WORK_DIR.glob("extraction_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        print("❌ No se encontró extracción previa.")
        sys.exit(1)
    workdir = candidates[0]

MSGSTORE = workdir / "msgstore.db"
WA_DB = workdir / "wa.db"
MEDIA_SRC = workdir / "media"

if not MSGSTORE.exists():
    print(f"❌ No existe {MSGSTORE}. Ejecuta 02_decrypt.py primero.")
    sys.exit(1)

print(f"📂 Procesando: {workdir}")

# ═══════════════════════════════════════════════════════════════
# CONEXIONES
# ═══════════════════════════════════════════════════════════════
print(f"🔌 Conectando a {DB_ENGINE}...")
db = DBAdapter(DB_ENGINE, DB_CONFIG)
cur = db.cursor()

wa_conn = sqlite3.connect(str(WA_DB)) if WA_DB.exists() else None
if wa_conn:
    wa_conn.row_factory = sqlite3.Row

msg_conn = sqlite3.connect(str(MSGSTORE))
msg_conn.row_factory = sqlite3.Row

# ═══════════════════════════════════════════════════════════════
# 1. REGISTRAR LOG DE EXTRACCIÓN
# ═══════════════════════════════════════════════════════════════
tipo_extraccion = "demo" if DEMO_MODE else "historico"
cur.execute(
    f"INSERT INTO extracciones_log (usuario, tipo, inicio, estado) "
    f"VALUES ({db.ph}, {db.ph}, {db.ph}, {db.ph})",
    (AUDIT_USER, tipo_extraccion, datetime.now(), "exitoso")
)
db.commit()

cur.execute("SELECT MAX(id) as id FROM extracciones_log")
row = cur.fetchone()
extraccion_id = row["id"] if isinstance(row, dict) else row[0]

# ═══════════════════════════════════════════════════════════════
# 2. IMPORTAR CONTACTOS
# ═══════════════════════════════════════════════════════════════
print("📇 Importando contactos...")
contactos_map = {}

if wa_conn:
    for row in wa_conn.execute("""
        SELECT jid, display_name, wa_name, number, status 
        FROM wa_contacts 
        WHERE jid LIKE '%@s.whatsapp.net'
    """):
        numero = row["number"] or row["jid"].split("@")[0]
        
        if DB_ENGINE in ("mysql", "mariadb"):
            cur.execute(f"""
                INSERT INTO contactos (jid, numero, nombre_guardado, nombre_whatsapp, estado)
                VALUES ({db.ph}, {db.ph}, {db.ph}, {db.ph}, {db.ph})
                ON DUPLICATE KEY UPDATE
                    nombre_guardado = VALUES(nombre_guardado),
                    nombre_whatsapp = VALUES(nombre_whatsapp),
                    estado = VALUES(estado)
            """, (row["jid"], numero, row["display_name"], row["wa_name"], row["status"]))
        else:  # SQL Server
            cur.execute(f"""
                MERGE contactos AS target
                USING (SELECT {db.ph} AS jid) AS src ON target.jid = src.jid
                WHEN MATCHED THEN UPDATE SET 
                    nombre_guardado = {db.ph}, nombre_whatsapp = {db.ph}, estado = {db.ph}
                WHEN NOT MATCHED THEN INSERT (jid, numero, nombre_guardado, nombre_whatsapp, estado)
                    VALUES ({db.ph}, {db.ph}, {db.ph}, {db.ph}, {db.ph});
            """, (row["jid"], row["display_name"], row["wa_name"], row["status"],
                  row["jid"], numero, row["display_name"], row["wa_name"], row["status"]))
        
        cur.execute(f"SELECT id FROM contactos WHERE jid = {db.ph}", (row["jid"],))
        result = cur.fetchone()
        cid = result["id"] if isinstance(result, dict) else result[0]
        contactos_map[row["jid"]] = {"id": cid, "nombre": row["display_name"] or row["wa_name"], "numero": numero}
    
    db.commit()

print(f"   ✅ {len(contactos_map)} contactos importados desde wa.db")

# ─── Procesar VCF (si existe) ───
vcf_files = list((workdir / "dbs").glob("*.vcf"))
if not vcf_files:
    vcf_files = list(workdir.glob("*.vcf"))
vcf_contacts = {}
if vcf_files:
    import re
    print(f"📇 Procesando archivo VCF: {vcf_files[0].name}")
    try:
        with open(vcf_files[0], "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            current_name = None
            for line in lines:
                line = line.strip()
                if line.startswith("FN:"):
                    current_name = line[3:]
                elif line.startswith("TEL"):
                    # Extraer solo los números
                    tel = re.sub(r'\D', '', line.split(":", 1)[-1])
                    if tel and current_name:
                        if tel.startswith("00"): tel = tel[2:]
                        # WhatsApp Peruano: 519...
                        if len(tel) == 9 and tel.startswith("9"): tel = "51" + tel
                        vcf_contacts[tel] = current_name
    except Exception as e:
        print(f"⚠️  Error procesando VCF: {e}")

# ═══════════════════════════════════════════════════════════════
# 3. PROCESAR MENSAJES
# ═══════════════════════════════════════════════════════════════
print("💬 Procesando chats...")

chats = msg_conn.execute("""
    SELECT c._id, j.raw_string as jid
    FROM chat c
    JOIN jid j ON c.jid_row_id = j._id
    WHERE j.raw_string LIKE '%@s.whatsapp.net'
""").fetchall()

stats = {"mensajes": 0, "archivos": 0, "faltantes": 0, "errores": 0}

for chat in tqdm(chats, desc="Chats", unit="chat"):
    try:
        jid = chat["jid"]
        chat_id = chat["_id"]
        
        # Asegurar que existe el contacto
        if jid not in contactos_map:
            numero = jid.split("@")[0]
            nombre_vcf = vcf_contacts.get(numero)
            
            cur.execute(
                f"{db.insert_ignore} INTO contactos (jid, numero, nombre_guardado) VALUES ({db.ph}, {db.ph}, {db.ph})",
                (jid, numero, nombre_vcf)
            )
            
            # Actualizar si tenemos nombre nuevo del VCF y la DB lo tiene en NULL
            if nombre_vcf:
                cur.execute(f"UPDATE contactos SET nombre_guardado = {db.ph} WHERE jid = {db.ph} AND nombre_guardado IS NULL", (nombre_vcf, jid))
            
            cur.execute(f"SELECT id, nombre_guardado, nombre_whatsapp FROM contactos WHERE jid = {db.ph}", (jid,))
            r = cur.fetchone()
            
            cid = r["id"] if isinstance(r, dict) else r[0]
            db_nombre = r["nombre_guardado"] if isinstance(r, dict) else r[1]
            db_wa_name = r["nombre_whatsapp"] if isinstance(r, dict) else r[2]
            
            contactos_map[jid] = {"id": cid, "nombre": db_nombre or db_wa_name, "numero": numero}
        
        contacto_info = contactos_map[jid]
        contacto_id = contacto_info["id"]
        
        # Query mensajes + media
        mensajes = msg_conn.execute("""
            SELECT m._id, m.from_me, m.timestamp, m.text_data, m.message_type,
                   mm.file_path, mm.mime_type, mm.media_name, mm.file_size, mm.media_caption
            FROM message m
            LEFT JOIN message_media mm ON m._id = mm.message_row_id
            WHERE m.chat_row_id = ?
            ORDER BY m.timestamp ASC
        """, (chat_id,)).fetchall()
        
        # ─── Insertar mensajes y Exportar a TXT ───
        batch = []
        import re
        nombre_carpeta = contacto_info["nombre"] or contacto_info["numero"]
        nombre_carpeta = re.sub(r'[\\/*?:"<>|]', "", str(nombre_carpeta)).strip()
        dest_dir = MEDIA_OUTPUT / nombre_carpeta
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        chat_txt_path = dest_dir / "_chat.txt"
        chat_lines = []

        for m in mensajes:
            tipo = detect_tipo(m["mime_type"], m["message_type"])
            wa_msg_id = f"{jid}_{m['_id']}"
            dt = ts_to_datetime(m["timestamp"])
            
            # Formato de exportación estilo WhatsApp
            dt_str = dt.strftime("%d/%m/%Y %H:%M") if dt else "Fecha desconocida"
            emisor = "Tú" if m["from_me"] else (contacto_info["nombre"] or contacto_info["numero"])
            texto_msg = m["text_data"] or ""
            if m["file_path"]:
                fname = os.path.basename(m["file_path"])
                adjunto = f"<Adjunto: {fname}>"
                texto_msg = f"{adjunto} {m['media_caption']}" if m["media_caption"] else adjunto
            # Reemplazar saltos de línea literales para mantener el log ordenado
            texto_msg = texto_msg.replace("\n", " ")
            chat_lines.append(f"[{dt_str}] {emisor}: {texto_msg}")
            
            batch.append((
                wa_msg_id, contacto_id, bool(m["from_me"]), tipo,
                m["text_data"] or "", m["media_caption"],
                m["timestamp"], dt,
                bool(m["file_path"])
            ))
            
        if chat_lines:
            with open(chat_txt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(chat_lines))
        
        if batch:
            query = f"""
                {db.insert_ignore} INTO mensajes 
                (wa_id, contacto_id, from_me, tipo, contenido, caption, 
                 timestamp_ms, fecha, tiene_archivo)
                VALUES ({','.join([db.ph]*9)})
            """
            cur.executemany(query, batch)
            stats["mensajes"] += len(batch)
        
        # ─── Procesar archivos multimedia ───
        for m in mensajes:
            if not m["file_path"]:
                continue
            wa_msg_id = f"{jid}_{m['_id']}"
            
            # Buscar archivo físico
            src_candidates = [
                MEDIA_SRC / m["file_path"].replace("Media/", f"{APP_FOLDER}/Media/"),
                MEDIA_SRC / m["file_path"],
            ]
            src_path = next((p for p in src_candidates if p.exists()), None)
            
            if not src_path:
                # Búsqueda recursiva por nombre
                fname = os.path.basename(m["file_path"])
                matches = list(MEDIA_SRC.rglob(fname))
                src_path = matches[0] if matches else None
            
            if src_path and src_path.exists():
                tipo_media = detect_tipo(m["mime_type"], m["message_type"])
                if tipo_media == "sticker" and not EXTRACT_STICKERS:
                    continue
                
                dest_path = dest_dir / src_path.name
                
                if not dest_path.exists():
                    shutil.copy2(src_path, dest_path)
                
                # Obtener ID del mensaje insertado
                cur.execute(f"SELECT id FROM mensajes WHERE wa_id = {db.ph}", (wa_msg_id,))
                msg_row = cur.fetchone()
                msg_id = msg_row["id"] if isinstance(msg_row, dict) else (msg_row[0] if msg_row else None)
                
                if msg_id:
                    cur.execute(f"""
                        {db.insert_ignore} INTO archivos 
                        (mensaje_id, contacto_id, nombre_original, nombre_local,
                         ruta_local, mime_type, tamano_bytes, hash_sha256)
                        VALUES ({','.join([db.ph]*8)})
                    """, (
                        msg_id, contacto_id,
                        m["media_name"] or src_path.name,
                        dest_path.name, str(dest_path),
                        m["mime_type"], m["file_size"],
                        sha256_file(dest_path)
                    ))
                    stats["archivos"] += 1
            else:
                stats["faltantes"] += 1
        
        db.commit()
    
    except Exception as e:
        stats["errores"] += 1
        print(f"\n⚠️  Error en chat {chat['jid']}: {e}")
        traceback.print_exc()

# ═══════════════════════════════════════════════════════════════
# 4. ACTUALIZAR ESTADÍSTICAS
# ═══════════════════════════════════════════════════════════════
print("\n📊 Actualizando estadísticas por contacto...")
cur.execute("""
    UPDATE contactos SET
        total_mensajes = (SELECT COUNT(*) FROM mensajes WHERE contacto_id = contactos.id),
        fecha_primer_mensaje = (SELECT MIN(fecha) FROM mensajes WHERE contacto_id = contactos.id),
        fecha_ultimo_mensaje = (SELECT MAX(fecha) FROM mensajes WHERE contacto_id = contactos.id)
""")

# Cerrar log
cur.execute(f"""
    UPDATE extracciones_log 
    SET fin = {db.ph}, chats_procesados = {db.ph}, 
        mensajes_total = {db.ph}, archivos_total = {db.ph}
    WHERE id = {db.ph}
""", (datetime.now(), len(chats), stats["mensajes"], stats["archivos"], extraccion_id))

db.commit()
db.close()

# ═══════════════════════════════════════════════════════════════
# REPORTE FINAL
# ═══════════════════════════════════════════════════════════════
print(f"""
╔═══════════════════════════════════════════════════════════╗
║  ✅ PROCESAMIENTO COMPLETADO                              ║
╠═══════════════════════════════════════════════════════════╣
║  Chats procesados:   {len(chats):>10}                             ║
║  Mensajes totales:   {stats['mensajes']:>10}                             ║
║  Archivos copiados:  {stats['archivos']:>10}                             ║
║  Archivos faltantes: {stats['faltantes']:>10}                             ║
║  Errores:            {stats['errores']:>10}                             ║
╚═══════════════════════════════════════════════════════════╝

📂 Archivos en: {MEDIA_OUTPUT.absolute()}
🗄️  BD:          {DB_CONFIG['database']}
""")
print("➡️  Siguiente paso: ./scripts/04_upload_drive.sh")
