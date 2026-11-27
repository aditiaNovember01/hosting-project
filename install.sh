#!/bin/bash
# ============================================================
# Install Script - ShareHosting Panel
# Jalankan sebagai root: bash install.sh
# ============================================================

set -e

echo "============================================"
echo "  ShareHosting Panel - Install Script"
echo "============================================"

# Cek root
if [ "$EUID" -ne 0 ]; then
    echo "[ERROR] Jalankan sebagai root (sudo bash install.sh)"
    exit 1
fi

PROJECT_DIR="/www/sharehosting"
HOSTING_ROOT="/www/wwwroot"

echo "[1/8] Update sistem..."
apt-get update -qq

echo "[2/8] Install dependencies..."
apt-get install -y -qq python3 python3-pip python3-venv \
    libmysqlclient-dev pkg-config gcc \
    sudo rbash curl git

echo "[3/8] Buat direktori project..."
mkdir -p "$PROJECT_DIR"
mkdir -p "$HOSTING_ROOT"

echo "[4/8] Copy project files..."
cp -r ./* "$PROJECT_DIR/"

echo "[5/8] Setup Python virtual environment..."
cd "$PROJECT_DIR"
python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "[6/8] Setup file .env..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    
    # Generate random secret key
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/ganti_dengan_random_string_panjang/$SECRET/" "$PROJECT_DIR/.env"
    
    echo ""
    echo "[!] Edit file .env sebelum melanjutkan:"
    echo "    nano $PROJECT_DIR/.env"
    echo ""
    read -p "Tekan Enter setelah edit .env..."
fi

echo "[7/8] Import database..."
read -p "MySQL host [localhost]: " MYSQL_HOST
MYSQL_HOST=${MYSQL_HOST:-localhost}
read -p "MySQL user [root]: " MYSQL_USER
MYSQL_USER=${MYSQL_USER:-root}
read -s -p "MySQL password: " MYSQL_PASS
echo ""

mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASS" < "$PROJECT_DIR/database.sql"
echo "[OK] Database berhasil diimport."

echo "[8/8] Setup sudo untuk panel..."
# Izinkan www-data atau user panel untuk useradd/userdel
cat > /etc/sudoers.d/sharehosting << 'EOF'
# ShareHosting - izin untuk panel
www-data ALL=(ALL) NOPASSWD: /usr/sbin/useradd, /usr/sbin/userdel, /usr/sbin/usermod
www-data ALL=(ALL) NOPASSWD: /usr/bin/chpasswd
www-data ALL=(ALL) NOPASSWD: /bin/chown, /bin/chmod
# Izinkan su menjadi host_* users untuk terminal
www-data ALL=(host_*) NOPASSWD: /bin/bash
EOF
chmod 440 /etc/sudoers.d/sharehosting

echo ""
echo "============================================"
echo "  INSTALASI SELESAI!"
echo "============================================"
echo ""
echo "Langkah selanjutnya:"
echo "  1. cd $PROJECT_DIR"
echo "  2. source venv/bin/activate"
echo "  3. python setup_admin.py    # buat akun admin"
echo "  4. python app.py            # jalankan panel"
echo ""
echo "Panel akan berjalan di: http://SERVER_IP:5000"
echo ""
echo "Untuk production, gunakan Gunicorn + Nginx/Apache di aaPanel."
