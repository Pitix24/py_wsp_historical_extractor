# ─── Clonar e instalar ───
git clone <tu-repo>/whatsapp-business-extractor.git
cd whatsapp-business-extractor
chmod +x setup.sh
./setup.sh

# ─── Configurar ───
cp .env.example .env
nano .env                              # Poner WA_KEY y credenciales DB
rclone config                          # Configurar gdrive-whatsapp y gdrive-crypt
mysql -u root -p < sql/schema_mysql.sql

# ─── Ejecutar pipeline (modo DEMO primero) ───
source venv/bin/activate
./scripts/01_extract.sh
python scripts/02_decrypt.py
python scripts/03_process_mysql.py
./scripts/04_upload_drive.sh
python scripts/05_verify.py