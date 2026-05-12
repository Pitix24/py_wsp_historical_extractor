# ═══════════════════════════════════════════════════════════════
# 01 - Extracción de DBs y Media (PowerShell - Windows)
# ═══════════════════════════════════════════════════════════════

# Cargar variables de .env
$envFile = ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | Where-Object { $_ -notmatch '^\s*#' -and $_ -match '=' } | ForEach-Object {
        $key, $value = $_ -split '=', 2
        [Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim())
    }
}

# Determinar paths según modo
$DEMO_MODE = [Environment]::GetEnvironmentVariable("DEMO_MODE", "Process") -eq "true"

if ($DEMO_MODE) {
    $PACKAGE = "com.whatsapp"
    $APP_FOLDER = "WhatsApp"
    Write-Host "🧪 MODO DEMO - WhatsApp Personal" -ForegroundColor Cyan
} else {
    $PACKAGE = "com.whatsapp.w4b"
    $APP_FOLDER = "WhatsApp Business"
    Write-Host "🏢 MODO PRODUCCIÓN - WhatsApp Business" -ForegroundColor Yellow
}

$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$WORK_DIR = [Environment]::GetEnvironmentVariable("WORK_DIR", "Process") -or "./workdir"
$WORKDIR = Join-Path $WORK_DIR "extraction_$TIMESTAMP"

# Crear directorios
New-Item -ItemType Directory -Path "$WORKDIR/dbs", "$WORKDIR/media" -Force | Out-Null

# ─── Verificar dispositivo ───────────────────────────────────
Write-Host ""
Write-Host "📱 Verificando dispositivo..."
$devices = adb devices
$connected = $devices | Select-String "device$" | Measure-Object | Select-Object -ExpandProperty Count

if ($connected -eq 0) {
    Write-Host "❌ Ningún dispositivo conectado. Verifica el cable USB y la depuración." -ForegroundColor Red
    exit 1
}
Write-Host $devices

# ─── Extraer bases de datos ──────────────────────────────────
Write-Host ""
Write-Host "📦 Extrayendo bases de datos cifradas..."
$DB_REMOTE_PATH = "/sdcard/Android/media/$PACKAGE/$APP_FOLDER/Databases"

try {
    adb pull "$DB_REMOTE_PATH/" "$WORKDIR/dbs/" 2>&1 | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) {
        throw "Error al extraer databases (exit code: $LASTEXITCODE)"
    }
} catch {
    Write-Host "❌ Error al extraer databases: $_" -ForegroundColor Red
    exit 1
}

# ─── Buscar VCF de Contactos ─────────────────────────────────
Write-Host ""
Write-Host "📇 Buscando archivo de Contactos exportado (.vcf)..."
try {
    $VCF_PATH = adb shell "find /sdcard/Download/ -iname '*.vcf' 2>/dev/null | head -n1" 2>$null | ForEach-Object { $_.Trim() }
    
    if ($VCF_PATH) {
        Write-Host "   Encontrado: $VCF_PATH"
        adb pull "$VCF_PATH" "$WORKDIR/contactos.vcf" 2>&1 | Out-Null
    } else {
        Write-Host "   ⚠️  No se encontró archivo .vcf"
    }
} catch {
    Write-Host "   ⚠️  Error buscando VCF: $_"
}

# ─── Extraer multimedia vía TAR (robusto) ───────────
Write-Host ""
Write-Host "🖼️  Extrayendo multimedia vía TAR (método robusto)..."
Write-Host "   Esto evita problemas con nombres raros, emojis y caracteres especiales."
Write-Host ""

$MEDIA_REMOTE_PATH = "/sdcard/Android/media/$PACKAGE/$APP_FOLDER/Media"
$MEDIA_TAR = Join-Path $WORKDIR "media.tar"

# Empaquetar en el dispositivo y transferir como stream
Write-Host "   Creando archive TAR en dispositivo..."
try {
    adb exec-out "tar -cf - -C '/sdcard/Android/media/$PACKAGE/$APP_FOLDER/' Media 2>/dev/null" > $MEDIA_TAR
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ⚠️  tar retornó error, pero continuamos (puede tener archivos con errores)"
    }
} catch {
    Write-Host "   ⚠️  Error creando TAR: $_"
}

# Verificar que el tar tiene contenido
$TAR_SIZE = (Get-Item $MEDIA_TAR -ErrorAction SilentlyContinue).Length
if ($null -eq $TAR_SIZE -or $TAR_SIZE -lt 1024) {
    Write-Host "❌ El archivo tar está vacío o casi vacío ($TAR_SIZE bytes)."
    Write-Host "   Probando método alternativo (adb pull directo)..."
    
    if (Test-Path $MEDIA_TAR) { Remove-Item $MEDIA_TAR -Force }
    
    # Fallback: usar adb pull directo
    try {
        $MEDIA_LOCAL = Join-Path $WORKDIR "Media"
        adb pull "$MEDIA_REMOTE_PATH/" "$MEDIA_LOCAL/" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✅ Media extraída vía adb pull"
        } else {
            Write-Host "   ⚠️  Error en extracción de media (puede continuar el proceso)"
        }
    } catch {
        Write-Host "   ⚠️  Error en método alternativo: $_"
    }
} else {
    $TAR_SIZE_MB = [math]::Round($TAR_SIZE / 1MB, 2)
    Write-Host "   ✅ TAR creado: $TAR_SIZE_MB MB"
    
    # Extraer localmente
    Write-Host ""
    Write-Host "📂 Extrayendo TAR localmente..."
    
    try {
        Push-Location $WORKDIR
        tar -xf media.tar 2>> "tar_errors.log"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "   ⚠️  Algunos archivos no pudieron extraerse (ver tar_errors.log)"
        }
        Pop-Location
        
        # Eliminar el tar para liberar espacio
        Remove-Item $MEDIA_TAR -Force -ErrorAction SilentlyContinue
    } catch {
        Write-Host "   ⚠️  Error extrayendo TAR: $_"
        Pop-Location
    }
}

# ─── Sanitizar nombres problemáticos (post-proceso) ──────────
Write-Host ""
Write-Host "🧹 Sanitizando nombres de archivos problemáticos..."
if (Test-Path "scripts/sanitize_filenames.py") {
    python scripts/sanitize_filenames.py "$WORKDIR/media" 2>&1 | Out-Null
}

# ─── Resumen ─────────────────────────────────────────────────
Write-Host ""
$DB_COUNT = @(Get-ChildItem "$WORKDIR/dbs" -Recurse -File -ErrorAction SilentlyContinue).Count
$MEDIA_COUNT = @(Get-ChildItem "$WORKDIR/media" -Recurse -File -ErrorAction SilentlyContinue).Count
$MEDIA_SIZE = "{0:N0} MB" -f ((Get-ChildItem "$WORKDIR/media" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB)

Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✅ EXTRACCIÓN COMPLETADA                                 ║" -ForegroundColor Green
Write-Host "╠═══════════════════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host ("║  Directorio:      " + $WORKDIR.PadRight(40) + "║") -ForegroundColor Green
Write-Host ("║  Archivos DB:     " + "$DB_COUNT".PadRight(40) + "║") -ForegroundColor Green
Write-Host ("║  Archivos media:  " + "$MEDIA_COUNT".PadRight(40) + "║") -ForegroundColor Green
Write-Host ("║  Tamaño media:    " + $MEDIA_SIZE.PadRight(40) + "║") -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Green

$WORKDIR | Set-Content ".last_extraction" -Force
Write-Host ""
Write-Host "➡️  Siguiente paso: python scripts/02_decrypt.py" -ForegroundColor Cyan
