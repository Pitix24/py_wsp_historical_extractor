# 🔐 Guía de Seguridad

## Principios
- **Menor privilegio**: solo el personal autorizado accede.
- **Defensa en profundidad**: múltiples capas de cifrado.
- **Auditoría**: cada acción queda registrada.

## Cifrado

| Capa | Método |
|------|--------|
| Dispositivo | Cifrado nativo de Android + WhatsApp E2E |
| Extracción local | LUKS/BitLocker en el disco de trabajo |
| Base de datos | TLS en conexión + `encrypted=true` en config |
| Google Drive | rclone crypt (AES-256) + HTTPS |
| Backups | GPG con clave separada |

## Gestión de secretos
- **Clave E2E**: Bitwarden / 1Password con 2FA
- **Contraseña rclone crypt**: sobre sellado físico en caja fuerte
- **Credenciales DB**: variables de entorno, NUNCA en código

## Checklist de seguridad
- [x] Disco local cifrado
- [x] `.env` excluido de Git (verificar .gitignore)
- [x] Conexión DB sobre TLS
- [ ] Acceso a Drive por cuenta dedicada de servicio
- [ ] Logs de acceso centralizados
- [ ] Revisión trimestral de permisos
- [ ] Política de retención definida

## Compliance
- **GDPR/LOPD**: documentar base legal (interés legítimo / contrato)
- **Derecho al olvido**: procedimiento para borrar contacto específico
- **Retención**: máximo 5 años o según ley aplicable
- **Notificación de brechas**: 72h al responsable
