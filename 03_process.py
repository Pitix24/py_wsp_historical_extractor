import sqlite3
import json
import os
import shutil
import re
from pathlib import Path
from tqdm import tqdm

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════
MSGSTORE = "msgstore.db"
WA_DB = "wa.db"
MEDIA_SRC = Path("./media")
OUTPUT = Path("./output")
OUTPUT.mkdir(exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# UTILIDADES
# ═══════════════════════════════════════════════════════════════
def sanitize(name: str, maxlen: int = 50) -> str:
    """Limpia un nombre para usarlo como carpeta."""
    if not name:
        return "SinNombre"
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', name)
    return cleaned.strip()[:maxlen] or "SinNombre"

def ts_to_iso(ts_ms: int) -> str:
    """Convierte timestamp WhatsApp (ms) a ISO."""
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts_ms/1000, tz=timezone.utc).isoformat()

# ═══════════════════════════════════════════════════════════════
# 1. CARGAR CONTACTOS
# ═══════════════════════════════════════════════════════════════
print("📇 Cargando contactos desde wa.db...")
contactos = {}
with sqlite3.connect(WA_DB) as conn:
    conn.row_factory = sqlite3.Row
    for row in conn.execute("""
        SELECT jid, display_name, wa_name, number, status 
        FROM wa_contacts
    """):
        contactos[row["jid"]] = {
            "nombre_guardado": row["display_name"],
            "nombre_whatsapp": row["wa_name"],
            "numero": row["number"] or row["jid"].split("@")[0],
            "estado": row["status"]
        }
print(f"   ✅ {len(contactos)} contactos cargados")

# ═══════════════════════════════════════════════════════════════
# 2. PROCESAR CHATS
# ═══════════════════════════════════════════════════════════════
print("\n💬 Procesando mensajes...")
conn = sqlite3.connect(MSGSTORE)
conn.row_factory = sqlite3.Row

# Obtener todos los chats individuales (excluye grupos si no los necesitas)
chats = conn.execute("""
    SELECT c._id, c.jid_row_id, j.raw_string as jid
    FROM chat c
    JOIN jid j ON c.jid_row_id = j._id
    WHERE j.raw_string LIKE '%@s.whatsapp.net'
""").fetchall()

print(f"   📊 Total de chats individuales: {len(chats)}")

# Estadísticas globales
stats = {
    "chats_procesados": 0,
    "mensajes_totales": 0,
    "archivos_copiados": 0,
    "archivos_faltantes": 0,
    "errores": []
}

# ═══════════════════════════════════════════════════════════════
# 3. ITERAR SOBRE CADA CHAT
# ═══════════════════════════════════════════════════════════════
for chat in tqdm(chats, desc="Procesando chats"):
    jid = chat["jid"]
    chat_id = chat["_id"]
    
    contacto = contactos.get(jid, {
        "nombre_guardado": None,
        "nombre_whatsapp": None,
        "numero": jid.split("@")[0],
        "estado": None
    })
    
    nombre_mostrar = (contacto["nombre_guardado"] 
                      or contacto["nombre_whatsapp"] 
                      or contacto["numero"])
    
    # Carpeta destino: NumeroTelefono_NombreCliente
    folder_name = f"{contacto['numero']}_{sanitize(nombre_mostrar)}"
    chat_folder = OUTPUT / folder_name
    media_folder = chat_folder / "archivos"
    chat_folder.mkdir(exist_ok=True)
    media_folder.mkdir(exist_ok=True)
    
    # Query completo de mensajes + media
    try:
        mensajes = conn.execute("""
            SELECT 
                m._id,
                m.from_me,
                m.timestamp,
                m.text_data,
                m.message_type,
                mm.file_path,
                mm.mime_type,
                mm.media_name,
                mm.file_size,
                mm.media_caption
            FROM message m
            LEFT JOIN message_media mm ON m._id = mm.message_row_id
            WHERE m.chat_row_id = ?
            ORDER BY m.timestamp ASC
        """, (chat_id,)).fetchall()
    except sqlite3.OperationalError as e:
        stats["errores"].append(f"{jid}: {e}")
        continue
    
    conversacion = []
    
    for msg in mensajes:
        item = {
            "id": msg["_id"],
            "de_mi": bool(msg["from_me"]),
            "timestamp_ms": msg["timestamp"],
            "fecha_iso": ts_to_iso(msg["timestamp"]) if msg["timestamp"] else None,
            "tipo": msg["message_type"],
            "texto": msg["text_data"] or "",
            "caption": msg["media_caption"],
            "archivo": None
        }
        
        # Copiar archivo multimedia al folder del cliente
        if msg["file_path"]:
            src_path = MEDIA_SRC / msg["file_path"].replace(
                "Media/", "WhatsApp Business/Media/"
            )
            # Fallback: buscar solo por nombre de archivo
            if not src_path.exists():
                fname = os.path.basename(msg["file_path"])
                matches = list(MEDIA_SRC.rglob(fname))
                src_path = matches[0] if matches else None
            
            if src_path and src_path.exists():
                dst_name = os.path.basename(str(src_path))
                dst_path = media_folder / dst_name
                if not dst_path.exists():
                    shutil.copy2(src_path, dst_path)
                item["archivo"] = {
                    "nombre": dst_name,
                    "mime": msg["mime_type"],
                    "tamaño_bytes": msg["file_size"]
                }
                stats["archivos_copiados"] += 1
            else:
                item["archivo"] = {"faltante": True, "ruta_original": msg["file_path"]}
                stats["archivos_faltantes"] += 1
        
        conversacion.append(item)
    
    # ═══ Guardar archivos de salida ═══
    
    # 1. JSON estructurado (para procesamiento)
    with open(chat_folder / "conversacion.json", "w", encoding="utf-8") as f:
        json.dump({
            "contacto": contacto,
            "jid": jid,
            "total_mensajes": len(conversacion),
            "primer_mensaje": conversacion[0]["fecha_iso"] if conversacion else None,
            "ultimo_mensaje": conversacion[-1]["fecha_iso"] if conversacion else None,
            "mensajes": conversacion
        }, f, ensure_ascii=False, indent=2)
    
    # 2. TXT legible (para revisión humana rápida)
    with open(chat_folder / "conversacion.txt", "w", encoding="utf-8") as f:
        f.write(f"═══ {nombre_mostrar} ({contacto['numero']}) ═══\n")
        f.write(f"Total mensajes: {len(conversacion)}\n\n")
        for m in conversacion:
            quien = "YO" if m["de_mi"] else nombre_mostrar
            fecha = m["fecha_iso"] or "?"
            f.write(f"[{fecha}] {quien}: {m['texto']}")
            if m["archivo"] and not m["archivo"].get("faltante"):
                f.write(f"  📎 {m['archivo']['nombre']}")
            f.write("\n")
    
    stats["chats_procesados"] += 1
    stats["mensajes_totales"] += len(conversacion)

conn.close()

# ═══════════════════════════════════════════════════════════════
# 4. REPORTE FINAL
# ═══════════════════════════════════════════════════════════════
reporte = {
    "fecha_extraccion": "2026-05-08",
    **stats
}
with open(OUTPUT / "_REPORTE.json", "w", encoding="utf-8") as f:
    json.dump(reporte, f, ensure_ascii=False, indent=2)

print(f"""
╔══════════════════════════════════════════════════════╗
║  ✅ PROCESAMIENTO COMPLETO                           ║
╠══════════════════════════════════════════════════════╣
║  Chats procesados:    {stats['chats_procesados']:>10}                  ║
║  Mensajes totales:    {stats['mensajes_totales']:>10}                  ║
║  Archivos copiados:   {stats['archivos_copiados']:>10}                  ║
║  Archivos faltantes:  {stats['archivos_faltantes']:>10}                  ║
║  Errores:             {len(stats['errores']):>10}                  ║
╚══════════════════════════════════════════════════════╝

📂 Resultado en: {OUTPUT.absolute()}
""")
