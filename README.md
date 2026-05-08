# 📱 WhatsApp Business Extractor

> Herramienta para extracción, procesamiento y almacenamiento seguro del histórico completo de WhatsApp Business, con sincronización a Google Drive y base de datos relacional (MySQL/MariaDB/SQL Server).

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Internal-red.svg)]()
[![Status](https://img.shields.io/badge/status-production--ready-green.svg)]()

---

## 📋 Tabla de Contenidos

- [Descripción](#descripción)
- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Uso](#uso)
- [Modo DEMO](#modo-demo)
- [Modo Producción](#modo-producción)
- [Estructura de Datos](#estructura-de-datos)
- [Seguridad](#seguridad)
- [FAQ](#faq)

---

## 📖 Descripción

Este proyecto automatiza la extracción completa del histórico de conversaciones de **WhatsApp Business**, incluyendo:

- ✅ Mensajes de texto (todo el historial)
- ✅ Nombres y números de contactos registrados
- ✅ Imágenes, videos, audios y documentos
- ✅ Timestamps y metadata completa
- ✅ Almacenamiento en BD relacional + Google Drive cifrado

Diseñado para escalar a **+2,000 clientes** sin intervención manual.

---

## 🏗️ Arquitectura

```
┌────────────────────┐
│  Dispositivo       │
│  WhatsApp Business │
└─────────┬──────────┘
          │ ADB / USB
          ▼
┌────────────────────┐      ┌───────────────────┐
│  Extracción Local  │─────▶│  Desencriptación  │
│  (msgstore.crypt15)│      │  (wa-crypt-tools) │
└────────────────────┘      └─────────┬─────────┘
                                      │
                                      ▼
                            ┌───────────────────┐
                            │   Procesamiento   │
                            │   Python + DB     │
                            └─────────┬─────────┘
                                      │
                  ┌───────────────────┼──────────────────┐
                  ▼                   ▼                  ▼
          ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
          │ MySQL/MariaDB│   │ Archivos     │   │ Google Drive │
          │ (metadata)   │   │ locales      │   │ (cifrado)    │
          └──────────────┘   └──────────────┘   └──────────────┘
```

---

## ⚙️ Requisitos

### Sistema
- **OS**: Linux (Ubuntu 22.04+ recomendado), macOS, o Windows con WSL2
- **Python**: 3.11 o superior
- **Espacio en disco**: ~100 GB libres para procesamiento temporal

### Software
- `adb` (Android Debug Bridge)
- `rclone` 1.64+
- `mysql-client` o `mariadb-client`
- `git`

### Dispositivo Android (WhatsApp Business)
- WhatsApp Business con **backup E2E cifrado activo**
- **Clave de 64 caracteres** del backup (o contraseña)
- **Depuración USB** habilitada
- Cable USB original

### Cuentas
- Google Drive (se recomienda Google Workspace Pro / Enterprise)
- Base de datos MySQL/MariaDB/SQL Server con permisos de escritura

---

# 🚀 Instalación

## 1. Clonar el repositorio
```bash
git clone https://github.com/tu-org/whatsapp-business-extractor.git
cd whatsapp-business-extractor
```
## 2. Ejecutar el instalador
```bash
chmod +x setup.sh ./setup.sh
```
## 3. Copiar y configurar variables de entorno
```bash
cp .env.example .env nano .env # Editar con tus credenciales
```
## 4. Crear schema en tu BD
```bash
mysql -u root -p < sql/schema_mysql.sql
```
## o para SQL Server:
```bash
sqlcmd -S localhost -U sa -i sql/schema_sqlserver.sql
```
---
## 📱 Uso

### Modo DEMO (con WhatsApp Personal)

Pensado para validar el flujo antes de tocar datos de producción.

```bash
export DEMO_MODE=true
./scripts/01_extract.sh
python scripts/02_decrypt.py
python scripts/03_process_mysql.py
./scripts/04_upload_drive.sh
```
### Ver guía completa en docs/DEMO_GUIDE.md.
## Modo Producción (WhatsApp Business)

```bash
export DEMO_MODE=false
./scripts/01_extract.sh
python scripts/02_decrypt.py
python scripts/03_process_mysql.py
./scripts/04_upload_drive.sh
python scripts/05_verify.py
```

### Ver guía completa en docs/PRODUCTION_GUIDE.md.