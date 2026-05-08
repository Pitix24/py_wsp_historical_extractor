-- ═══════════════════════════════════════════════════════════════
-- Schema para SQL Server 2019+
-- ═══════════════════════════════════════════════════════════════

IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'whatsapp_business')
    CREATE DATABASE whatsapp_business;
GO

USE whatsapp_business;
GO

-- ─── Tabla: contactos ────────────────────────────────────────
IF OBJECT_ID('contactos', 'U') IS NULL
CREATE TABLE contactos (
    id                   BIGINT IDENTITY(1,1) PRIMARY KEY,
    jid                  NVARCHAR(100) NOT NULL UNIQUE,
    numero               NVARCHAR(30)  NOT NULL,
    nombre_guardado      NVARCHAR(200),
    nombre_whatsapp      NVARCHAR(200),
    estado               NVARCHAR(MAX),
    fecha_primer_mensaje DATETIME2,
    fecha_ultimo_mensaje DATETIME2,
    total_mensajes       INT DEFAULT 0,
    created_at           DATETIME2 DEFAULT SYSUTCDATETIME(),
    updated_at           DATETIME2 DEFAULT SYSUTCDATETIME()
);
GO

CREATE INDEX idx_numero ON contactos(numero);
CREATE INDEX idx_nombre ON contactos(nombre_guardado);
GO

-- ─── Tabla: mensajes ─────────────────────────────────────────
IF OBJECT_ID('mensajes', 'U') IS NULL
CREATE TABLE mensajes (
    id             BIGINT IDENTITY(1,1) PRIMARY KEY,
    wa_id          NVARCHAR(150) NOT NULL UNIQUE,
    contacto_id    BIGINT NOT NULL,
    from_me        BIT NOT NULL DEFAULT 0,
    tipo           NVARCHAR(20) DEFAULT 'text',
    contenido      NVARCHAR(MAX),
    caption        NVARCHAR(MAX),
    timestamp_ms   BIGINT NOT NULL,
    fecha          DATETIME2 NOT NULL,
    tiene_archivo  BIT DEFAULT 0,
    created_at     DATETIME2 DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_mensajes_contactos FOREIGN KEY (contacto_id) 
        REFERENCES contactos(id) ON DELETE CASCADE
);
GO

CREATE INDEX idx_contacto ON mensajes(contacto_id);
CREATE INDEX idx_fecha ON mensajes(fecha);
CREATE INDEX idx_tipo ON mensajes(tipo);
GO

-- ─── Tabla: archivos ─────────────────────────────────────────
IF OBJECT_ID('archivos', 'U') IS NULL
CREATE TABLE archivos (
    id              BIGINT IDENTITY(1,1) PRIMARY KEY,
    mensaje_id      BIGINT NOT NULL,
    contacto_id     BIGINT NOT NULL,
    nombre_original NVARCHAR(500),
    nombre_local    NVARCHAR(500),
    ruta_local      NVARCHAR(MAX),
    ruta_drive      NVARCHAR(MAX),
    mime_type       NVARCHAR(100),
    tamano_bytes    BIGINT,
    hash_sha256     CHAR(64),
    subido_drive    BIT DEFAULT 0,
    fecha_subida    DATETIME2,
    created_at      DATETIME2 DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_archivos_mensajes FOREIGN KEY (mensaje_id) 
        REFERENCES mensajes(id) ON DELETE CASCADE,
    CONSTRAINT FK_archivos_contactos FOREIGN KEY (contacto_id) 
        REFERENCES contactos(id)
);
GO

CREATE INDEX idx_mensaje ON archivos(mensaje_id);
CREATE INDEX idx_contacto_archivo ON archivos(contacto_id);
CREATE INDEX idx_hash ON archivos(hash_sha256);
GO

-- ─── Tabla: extracciones_log ─────────────────────────────────
IF OBJECT_ID('extracciones_log', 'U') IS NULL
CREATE TABLE extracciones_log (
    id               BIGINT IDENTITY(1,1) PRIMARY KEY,
    usuario          NVARCHAR(100),
    tipo             NVARCHAR(20) DEFAULT 'continua',
    inicio           DATETIME2,
    fin              DATETIME2,
    chats_procesados INT,
    mensajes_total   INT,
    archivos_total   INT,
    errores          NVARCHAR(MAX),
    estado           NVARCHAR(20) DEFAULT 'exitoso'
);
GO

-- ─── Vista: resumen por cliente ──────────────────────────────
IF OBJECT_ID('v_resumen_clientes', 'V') IS NOT NULL
    DROP VIEW v_resumen_clientes;
GO

CREATE VIEW v_resumen_clientes AS
SELECT 
    c.id, c.numero,
    COALESCE(c.nombre_guardado, c.nombre_whatsapp, c.numero) AS nombre,
    c.total_mensajes,
    COUNT(DISTINCT a.id) AS total_archivos,
    SUM(CASE WHEN a.mime_type LIKE 'image%'    THEN 1 ELSE 0 END) AS imagenes,
    SUM(CASE WHEN a.mime_type = 'application/pdf' THEN 1 ELSE 0 END) AS pdfs,
    SUM(CASE WHEN a.mime_type LIKE 'audio%'    THEN 1 ELSE 0 END) AS audios,
    SUM(CASE WHEN a.mime_type LIKE 'video%'    THEN 1 ELSE 0 END) AS videos,
    c.fecha_primer_mensaje, c.fecha_ultimo_mensaje
FROM contactos c
LEFT JOIN archivos a ON c.id = a.contacto_id
GROUP BY c.id, c.numero, c.nombre_guardado, c.nombre_whatsapp,
         c.total_mensajes, c.fecha_primer_mensaje, c.fecha_ultimo_mensaje;
GO
