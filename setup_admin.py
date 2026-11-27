"""
Script untuk membuat akun admin pertama.
Jalankan sekali: python setup_admin.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from extensions import bcrypt
from models import Admin

def main():
    app = create_app()
    with app.app_context():
        from extensions import db_conn

        print("=" * 50)
        print("  Setup Admin - ShareHosting Panel")
        print("=" * 50)

        username = input("Admin username: ").strip()
        email = input("Admin email: ").strip()
        password = input("Admin password: ").strip()

        if not username or not email or not password:
            print("[ERROR] Semua field wajib diisi!")
            sys.exit(1)

        # Cek existing
        existing = Admin.get_by_username(username)
        if existing:
            print(f"[ERROR] Admin '{username}' sudah ada!")
            sys.exit(1)

        Admin.create(username, email, password)
        print(f"\n[OK] Admin '{username}' berhasil dibuat!")
        print("     Silakan login di http://localhost:5000/login")

if __name__ == '__main__':
    main()
