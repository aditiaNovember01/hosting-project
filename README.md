# ShareHosting Panel

Panel shared hosting berbasis Flask untuk membagi server dengan isolasi per user.

## Fitur
- Login user & admin terpisah
- Terminal browser (xterm.js + WebSocket + PTY)
- Isolasi direktori per user (chroot-style via rbash)
- Admin panel: kelola user, quota, reset password, log sesi
- MySQL database
- Dukungan: `git`, `php artisan`, `composer`, `npm`, `python`, `spark`, dll

## Struktur Direktori
```
/www/sharehosting/     ← project panel
/www/wwwroot/
  ├── user1/           ← home dir user1
  ├── user2/           ← home dir user2
  └── ...
```

## Instalasi di Server (Ubuntu/aaPanel)

### 1. Upload project ke server
```bash
# Di aaPanel, upload ke /www/sharehosting/
# atau via terminal:
git clone <repo> /www/sharehosting
```

### 2. Jalankan installer
```bash
cd /www/sharehosting
bash install.sh
```

### 3. Edit konfigurasi
```bash
nano /www/sharehosting/.env
```
Isi dengan:
```env
SECRET_KEY=random_string_panjang
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=password_mysql_anda
MYSQL_DB=sharehosting
HOSTING_ROOT=/www/wwwroot
```

### 4. Import database
```bash
mysql -u root -p < database.sql
```

### 5. Buat akun admin
```bash
cd /www/sharehosting
source venv/bin/activate
python setup_admin.py
```

### 6. Jalankan panel

**Mode development:**
```bash
python app.py
```

**Mode production (systemd):**
```bash
cp sharehosting.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable sharehosting
systemctl start sharehosting
```

## Konfigurasi Domain di aaPanel

1. Buka aaPanel → Website → Add site
2. Domain: `panel.yourdomain.com`
3. PHP Version: **Pure Static** atau **Reverse Proxy**
4. Tambah reverse proxy ke `http://127.0.0.1:5000`

**Config Nginx (di aaPanel → Site Config):**
```nginx
location / {
    proxy_pass http://127.0.0.1:5000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_read_timeout 86400;
}
```

> **`proxy_read_timeout 86400`** penting agar WebSocket terminal tidak terputus!

## Keamanan
- Setiap user berjalan sebagai Linux user terpisah (`host_username`)
- Shell dibatasi ke `/bin/rbash` (restricted bash)
- Hanya command yang di-whitelist yang bisa dijalankan
- User tidak bisa keluar dari home directory mereka
- Sudo diblokir di dalam terminal user

## Akses Panel
- URL: `http://SERVER_IP:5000`
- Login Admin: pilih tab "Admin" di halaman login
- Login User: pilih tab "User"
