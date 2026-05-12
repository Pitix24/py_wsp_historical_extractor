#!/usr/bin/env python3
"""
Sanitiza nombres de archivos con caracteres problemáticos:
- Backslashes literales
- Emojis
- Saltos de línea
- Caracteres de control
"""
import sys
import re
from pathlib import Path

def sanitize_filename(name: str) -> str:
    """Limpia un nombre de archivo de caracteres problemáticos."""
    # Remover saltos de línea y tabs
    name = re.sub(r'[\r\n\t]+', '_', name)
    
    # Reemplazar backslashes literales con guion bajo
    name = name.replace('\\', '_')
    
    # Remover emojis y caracteres no ASCII problemáticos (opcional)
    # Mantenemos caracteres latinos pero removemos emojis
    name = re.sub(r'[\U0001F000-\U0001FFFF\U00002600-\U000027BF]', '', name)
    
    # Remover caracteres de control
    name = re.sub(r'[\x00-\x1f\x7f]', '', name)
    
    # Colapsar espacios múltiples
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Limitar longitud
    if len(name) > 200:
        parts = name.rsplit('.', 1)
        if len(parts) == 2:
            name = parts[0][:195] + '.' + parts[1]
        else:
            name = name[:200]
    
    return name or "archivo_sin_nombre"


def sanitize_directory(root: Path, dry_run=False):
    """Recorre recursivamente y renombra archivos/carpetas problemáticos."""
    renamed = 0
    errors = 0
    
    # Procesar de abajo hacia arriba para no romper rutas
    all_paths = sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True)
    
    for path in all_paths:
        try:
            old_name = path.name
            new_name = sanitize_filename(old_name)
            
            if old_name != new_name:
                new_path = path.parent / new_name
                
                # Evitar colisiones
                counter = 1
                while new_path.exists() and new_path != path:
                    stem = Path(new_name).stem
                    suffix = Path(new_name).suffix
                    new_path = path.parent / f"{stem}_{counter}{suffix}"
                    counter += 1
                
                if dry_run:
                    print(f"  [DRY] {old_name!r} → {new_name!r}")
                else:
                    path.rename(new_path)
                    print(f"  ✓ {old_name[:50]!r} → {new_name[:50]!r}")
                renamed += 1
        except Exception as e:
            print(f"  ✗ Error con {path}: {e}")
            errors += 1
    
    return renamed, errors


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python sanitize_filenames.py <directorio> [--dry-run]")
        sys.exit(1)
    
    root = Path(sys.argv[1])
    dry_run = "--dry-run" in sys.argv
    
    if not root.exists():
        print(f"❌ No existe: {root}")
        sys.exit(1)
    
    print(f"🧹 Sanitizando: {root}")
    if dry_run:
        print("   (modo DRY-RUN, no se hacen cambios)")
    
    renamed, errors = sanitize_directory(root, dry_run)
    
    print(f"\n✅ Completado: {renamed} renombrados, {errors} errores")
