-- ═══════════════════════════════════════════════════════════════
-- Schema para MySQL 8.0+ / MariaDB 10.6+
-- ═══════════════════════════════════════════════════════════════

CREATE DATABASE IF NOT EXISTS whatsapp_business 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS whatsapp_business_demo
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

-- Usuario dedicado (cambia la contraseña)
CREATE USER IF NOT EXISTS 'whatsapp_user'@'%' IDENTIFIED BY 'CHANGE_ME_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON whatsapp_business.* TO 'whatsapp_user'@'%';
GRANT ALL PRIVILEGES ON whatsapp_business_demo.* TO 'whatsapp_user'@'%';
FLUSH PRIVILEGES;

-- ─── Seleccionar BD ──────────────────────────────────────────
USE whatsapp_business;

-- ─── Tabla: contactos ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS contactos (
    id                   BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    jid                  VARCHAR(100) NOT NULL UNIQUE,
    numero               VARCHAR(30)  NOT NULL,
    nombre_guardado      VARCHAR(200),
    nombre_whatsapp      VARCHAR(200),
    estado               TEXT,
    fecha_primer_mensaje DATETIME,
    fecha_ultimo_mensaje DATETIME,
    total_mensajes       INT UNSIGNED DEFAULT 0,
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_numero (numero),
    INDEX idx_nombre (nombre_guardado)
) ENGINE=InnoDB;

-- ─── Tabla: mensajes ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mensajes (
    id             BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    wa_id          VARCHAR(150) NOT NULL UNIQUE,
    contacto_id    BIGINT UNSIGNED NOT NULL,
    from_me        BOOLEAN NOT NULL DEFAULT FALSE,
    tipo           ENUM('text','image','video','audio','document','sticker','location','contact','other') DEFAULT 'text',
    contenido      MEDIUMTEXT,
    caption        TEXT,
    timestamp_ms   BIGINT NOT NULL,
    fecha          DATETIME NOT NULL,
    tiene_archivo  BOOLEAN DEFAULT FALSE,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contacto_id) REFERENCES contactos(id) ON DELETE CASCADE,
    INDEX idx_contacto (contacto_id),
    INDEX idx_fecha (fecha),
    INDEX idx_tipo (tipo),
    FULLTEXT INDEX ft_contenido (contenido)
) ENGINE=InnoDB;

-- ─── Tabla: archivos ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS archivos (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    mensaje_id      BIGINT UNSIGNED NOT NULL,
    contacto_id     BIGINT UNSIGNED NOT NULL,
    nombre_original VARCHAR(500),
    nombre_local    VARCHAR(500),
    ruta_local      TEXT,
    ruta_drive      TEXT,
    mime_type       VARCHAR(100),
    tamano_bytes    BIGINT UNSIGNED,
    hash_sha256     CHAR(64),
    subido_drive    BOOLEAN DEFAULT FALSE,
    fecha_subida    DATETIME,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mensaje_id) REFERENCES mensajes(id) ON DELETE CASCADE,
    FOREIGN KEY (contacto_id) REFERENCES contactos(id) ON DELETE CASCADE,
    INDEX idx_mensaje (mensaje_id),
    INDEX idx_contacto_archivo (contacto_id),
    INDEX idx_hash (hash_sha256),
    INDEX idx_mime (mime_type)
) ENGINE=InnoDB;

-- ─── Tabla: extracciones_log (auditoría) ─────────────────────
CREATE TABLE IF NOT EXISTS extracciones_log (
    id               BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    usuario          VARCHAR(100),
    tipo             ENUM('historico','continua','demo','manual') DEFAULT 'continua',
    inicio           DATETIME,
    fin              DATETIME,
    chats_procesados INT UNSIGNED,
    mensajes_total   INT UNSIGNED,
    archivos_total   INT UNSIGNED,
    errores          TEXT,
    estado           ENUM('exitoso','parcial','fallido') DEFAULT 'exitoso'
) ENGINE=InnoDB;

-- ─── Vista: resumen por cliente ──────────────────────────────
CREATE OR REPLACE VIEW v_resumen_clientes AS
SELECT 
    c.id,
    c.numero,
    COALESCE(c.nombre_guardado, c.nombre_whatsapp, c.numero) AS nombre,
    c.total_mensajes,
    COUNT(DISTINCT a.id) AS total_archivos,
    SUM(CASE WHEN a.mime_type LIKE 'image%'    THEN 1 ELSE 0 END) AS imagenes,
    SUM(CASE WHEN a.mime_type = 'application/pdf' THEN 1 ELSE 0 END) AS pdfs,
    SUM(CASE WHEN a.mime_type LIKE 'audio%'    THEN 1 ELSE 0 END) AS audios,
    SUM(CASE WHEN a.mime_type LIKE 'video%'    THEN 1 ELSE 0 END) AS videos,
    c.fecha_primer_mensaje,
    c.fecha_ultimo_mensaje
FROM contactos c
LEFT JOIN archivos a ON c.id = a.contacto_id
GROUP BY c.id;

-- Aplicar el mismo schema a la BD DEMO
USE whatsapp_business_demo;
-- (Ejecuta manualmente los CREATE TABLE anteriores en esta BD también, 
-- o usa un script que itere sobre ambas bases)
