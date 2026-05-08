# 🧪 Guía DEMO — WhatsApp Personal

Esta guía te lleva paso a paso a ejecutar una demo completa usando **tu propio dispositivo con WhatsApp Personal**, para validar el flujo antes de tocar datos de producción.

## 1. Preparar el dispositivo

1. Abre WhatsApp (personal) en tu celular Android.
2. Ve a **Ajustes → Chats → Copia de seguridad**.
3. Activa **Copia de seguridad cifrada de extremo a extremo**.
4. Elige **"Usar clave de 64 caracteres"** y **GUÁRDALA**.
5. Pulsa **"Copiar ahora"** para generar un backup reciente.
6. Activa **Opciones de desarrollador** y **Depuración USB**.

## 2. Preparar datos de prueba

Pide a 3-4 contactos que durante 2-3 días te envíen:
- Mensajes de texto variados
- 2-3 imágenes
- 1-2 PDFs
- 1-2 audios
- 1 video corto

Esto simula el flujo de clientes de pagos.

## 3. Ejecutar la demo

```bash
# Configurar en modo DEMO
echo "DEMO_MODE=true" > .env.demo
source .env.demo
```

Editar .env con la clave de 64 caracteres
```bash
nano .env
```
Ejecutar pipeline completo
```bash
./scripts/01_extract.sh python scripts/02_decrypt.py python scripts/03_process_mysql.py ./scripts/04_upload_drive.sh python scripts/05_verify.py
```

## 4. Verificar resultados

```sql
USE whatsapp_business_demo;
```