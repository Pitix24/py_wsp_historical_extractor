-- ═══════════════════════════════════════════════════════════════
-- Consultas de validación post-importación
-- Ejecutar para verificar integridad y explorar la data
-- ═══════════════════════════════════════════════════════════════

USE whatsapp_business_demo;  -- o whatsapp_business

-- 1. Conteo general
SELECT 
    (SELECT COUNT(*) FROM contactos) AS contactos,
    (SELECT COUNT(*) FROM mensajes)  AS mensajes,
    (SELECT COUNT(*) FROM archivos)  AS archivos;

-- 2. Resumen por cliente
SELECT * FROM v_resumen_clientes
ORDER BY total_mensajes DESC
LIMIT 10;

-- 3. Buscar por texto (palabras clave de pagos)
SELECT c.nombre_guardado, c.numero, m.fecha, 
       SUBSTRING(m.contenido, 1, 200) AS preview
FROM mensajes m
JOIN contactos c ON m.contacto_id = c.id
WHERE MATCH(m.contenido) AGAINST('factura pago comprobante transferencia' IN BOOLEAN MODE)
ORDER BY m.fecha DESC
LIMIT 50;

-- 4. Todos los PDFs de un cliente
SELECT a.nombre_original, a.ruta_local, m.fecha
FROM archivos a
JOIN mensajes m ON a.mensaje_id = m.id
JOIN contactos c ON a.contacto_id = c.id
WHERE c.numero = '5491123456789'
  AND a.mime_type = 'application/pdf'
ORDER BY m.fecha DESC;

-- 5. Archivos grandes (>10 MB)
SELECT c.nombre_guardado, a.nombre_original, 
       ROUND(a.tamano_bytes/1024/1024, 2) AS mb,
       a.mime_type
FROM archivos a
JOIN contactos c ON a.contacto_id = c.id
WHERE a.tamano_bytes > 10*1024*1024
ORDER BY a.tamano_bytes DESC;

-- 6. Actividad por mes
SELECT 
    DATE_FORMAT(fecha, '%Y-%m') AS mes,
    COUNT(*) AS mensajes,
    COUNT(DISTINCT contacto_id) AS clientes_activos
FROM mensajes
GROUP BY mes
ORDER BY mes DESC;

-- 7. Log de extracciones
SELECT * FROM extracciones_log ORDER BY inicio DESC LIMIT 10;

-- 8. Detectar duplicados por hash (archivos idénticos)
SELECT hash_sha256, COUNT(*) AS copias, 
       GROUP_CONCAT(nombre_original) AS nombres
FROM archivos
WHERE hash_sha256 IS NOT NULL
GROUP BY hash_sha256
HAVING copias > 1
ORDER BY copias DESC;
