# 🏢 Guía de Producción — WhatsApp Business

Para ejecutar el proceso sobre la cuenta real de WhatsApp Business de la organización.

## Pre-requisitos

- [ ] Aprobación firmada del responsable de datos
- [ ] Backup reciente verificado en el dispositivo
- [ ] Clave E2E de 64 caracteres en password manager
- [ ] ~100 GB libres en disco
- [ ] BD MySQL/MariaDB/SQL Server lista con el schema
- [ ] rclone configurado con cifrado

## Extracción de Nombres de Contacto (El problema de wa.db)

Por medidas de seguridad de Android, el archivo `wa.db` (que contiene los nombres de perfil y estados de WhatsApp) se almacena en la ruta protegida `/data/data/com.whatsapp.w4b/databases/`. **No es posible extraerlo por USB (`adb pull`) en un teléfono normal.**

Para obtener los nombres tienes dos opciones viables en equipos de la empresa:

**Opción A: Equipo Rooteado (Recomendado para extracción total)**
Si el equipo tiene Root, puedes extraer el archivo directamente.
1. Conectar por ADB.
2. Ejecutar: `adb shell "su -c 'cp /data/data/com.whatsapp.w4b/databases/wa.db /sdcard/wa.db'"`
3. Ejecutar: `adb pull /sdcard/wa.db ./workdir/dbs/`

**Opción B: Exportar Contactos del Teléfono (VCF)**
Para contactos *guardados* en el teléfono, sin necesidad de Root.
1. Ve a la app **Contactos** del celular.
2. Ve a Ajustes/Administrar contactos -> **Exportar a almacenamiento**.
3. Te generará un archivo `Contactos.vcf` en el celular.
4. Pasa ese archivo a la PC. *(Nota: Pronto agregaremos un script para cruzar este archivo VCF con la base de datos).*

## Configuración Opcional

En tu archivo `.env` o `config/config.py`, puedes configurar ciertas opciones para optimizar el almacenamiento:
- `EXTRACT_STICKERS=false`: (Por defecto) Evita copiar los miles de archivos `.webp` (stickers) al disco y a la nube para ahorrar gigabytes de espacio y tiempo de subida. Los stickers igual quedarán registrados en el archivo `_chat.txt` como `<Adjunto: sticker.webp>`. Cambiar a `true` si deseas guardarlos físicamente.

## Ejecución

```bash
# Modo producción
export DEMO_MODE=false
```
Editar .env con credenciales de PRODUCCIÓN
```bash
nano .env
```
Pipeline completo
```
./scripts/01_extract.ps1 # ~10-20 min 
python scripts/02_decrypt.py # ~1 min 
python scripts/03_process.py # ~30-60 min para 2k chats 
./scripts/04_upload_drive.sh # ~4-12 hrs según volumen 
python scripts/05_verify.py # ~2 min
```

## Post-ejecución

1. Verificar reporte en consola
2. Hacer muestreo manual (10 chats aleatorios)
3. Backup del backup: copia adicional en disco externo cifrado
4. Cerrar sesión del dispositivo de la red
5. Documentar ejecución en el log de cumplimiento

## Contingencias

| Problema | Solución |
|----------|----------|
| ADB no detecta dispositivo | Revocar autorizaciones USB y reautorizar |
| wadecrypt falla | Verificar que la clave de 64 chars sea correcta |
| Error de conexión MySQL | Verificar firewall y credenciales en .env |
| rclone quota exceeded | Esperar 24h o usar cuenta de servicio 