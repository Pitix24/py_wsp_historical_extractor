-- ═══════════════════════════════════════════════════════════════
-- BASE DE DATOS: whatsapp_business
-- Motor: MySQL 8.0+ / MariaDB 10.6+
-- ═══════════════════════════════════════════════════════════════

CREATE DATABASE IF NOT EXISTS whatsapp_business 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

USE whatsapp_business;

-- Tabla de contactos (clientes)
CREATE TABLE contactos (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    jid             VARCHAR(100) NOT NULL UNIQUE,
    numero          VARCHAR(30) NOT NULL,
    nombre_guardado VARCHAR(200),
    nombre_whatsapp VARCHAR(200),
    estado          TEXT,
    fecha_primer_mensaje DATETIME,
    fecha_ultimo_mensaje DATETIME,
    total_mensajes  INT UNSIGNED DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_numero (numero),
    INDEX idx_nombre (nombre_guardado)
) ENGINE=InnoDB;

-- Tabla de mensajes
CREATE TABLE mensajes (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    wa_id           VARCHAR(100) NOT NULL UNIQUE,  -- ID original de WhatsApp
    contacto_id     BIGINT UNSIGNED NOT NULL,
    from_me         BOOLEAN NOT NULL DEFAULT FALSE,
    tipo            ENUM('text','image','video','audio','document','sticker','location','contact','other') DEFAULT 'text',
    contenido       MEDIUMTEXT,
    caption         TEXT,
    timestamp_ms    BIGINT NOT NULL,
    fecha           DATETIME NOT NULL,
    tiene_archivo   BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contacto_id) REFERENCES contactos(id) ON DELETE CASCADE,
    INDEX idx_contacto (contacto_id),
    INDEX idx_fecha (fecha),
    INDEX idx_tipo (tipo),
    FULLTEXT INDEX ft_contenido (contenido)  -- Búsqueda por texto
) ENGINE=InnoDB;

-- Tabla de archivos multimedia
CREATE TABLE archivos (
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
    INDEX idx_hash (hash_sha256)
) ENGINE=InnoDB;

-- Tabla de log de extracciones (auditoría)
CREATE TABLE extracciones_log (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    usuario         VARCHAR(100),
    tipo            ENUM('historico','continua','manual') DEFAULT 'continua',
    inicio          DATETIME,
    fin             DATETIME,
    chats_procesados INT UNSIGNED,
    mensajes_total  INT UNSIGNED,
    archivos_total  INT UNSIGNED,
    errores         TEXT,
    estado          ENUM('exitoso','parcial','fallido')
) ENGINE=InnoDB;