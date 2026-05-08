# 🏢 Guía de Producción — WhatsApp Business

Para ejecutar el proceso sobre la cuenta real de WhatsApp Business de la organización.

## Pre-requisitos

- [ ] Aprobación firmada del responsable de datos
- [ ] Backup reciente verificado en el dispositivo
- [ ] Clave E2E de 64 caracteres en password manager
- [ ] ~100 GB libres en disco
- [ ] BD MySQL/MariaDB/SQL Server lista con el schema
- [ ] rclone configurado con cifrado

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
./scripts/01_extract.sh # ~10-20 min 
python scripts/02_decrypt.py # ~1 min 
python scripts/03_process_mysql.py # ~30-60 min para 2k chats 
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