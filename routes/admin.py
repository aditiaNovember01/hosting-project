from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
from flask_login import login_required, current_user
from models import User, Admin
from extensions import db_conn, bcrypt
from functools import wraps
import os
import subprocess

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Silakan login sebagai admin.', 'warning')
            return redirect(url_for('auth.login'))
        if not getattr(current_user, 'is_admin', False):
            flash('Akses ditolak. Hanya admin yang diizinkan.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    users = User.get_all()
    cur = db_conn.connection.cursor()
    cur.execute("SELECT COUNT(*) as total FROM users")
    total_users = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as total FROM users WHERE is_active = 1")
    active_users = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as total FROM terminal_sessions WHERE DATE(started_at) = CURDATE()")
    sessions_today = cur.fetchone()['total']
    cur.close()

    return render_template(
        'admin/dashboard.html',
        users=users,
        total_users=total_users,
        active_users=active_users,
        sessions_today=sessions_today
    )


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        quota_mb = int(request.form.get('quota_mb', 1024))
        domain = request.form.get('domain', '').strip() or None
        custom_home = request.form.get('home_dir', '').strip()

        # Validasi
        if not username or not email or not password:
            flash('Semua field wajib diisi.', 'danger')
            return render_template('admin/create_user.html')

        if len(username) < 3 or len(username) > 20:
            flash('Username harus 3-20 karakter.', 'danger')
            return render_template('admin/create_user.html')

        if not username.isalnum():
            flash('Username hanya boleh huruf dan angka.', 'danger')
            return render_template('admin/create_user.html')

        # Cek duplikat
        existing = User.get_by_username(username)
        if existing:
            flash(f'Username "{username}" sudah digunakan.', 'danger')
            return render_template('admin/create_user.html')

        from flask import current_app
        hosting_root = current_app.config['HOSTING_ROOT']
        linux_user = f'host_{username}'
        # Pakai custom home_dir jika diisi, kalau tidak pakai default
        home_dir = custom_home if custom_home else os.path.join(hosting_root, username)

        try:
            # 1. Buat Linux user jika belum ada
            check = subprocess.run(['id', linux_user], capture_output=True)
            if check.returncode != 0:
                subprocess.run(
                    ['useradd', '-m', '-d', home_dir, '-s', '/bin/bash', linux_user],
                    capture_output=True
                )

            # 2. Set password Linux user
            proc = subprocess.Popen(
                ['chpasswd'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            proc.communicate(input=f'{linux_user}:{password}'.encode())

            # 3. Pastikan home_dir ada dan permission benar
            os.makedirs(home_dir, exist_ok=True)
            subprocess.run(['chown', '-R', f'{linux_user}:www-data', home_dir], capture_output=True)
            subprocess.run(['chmod', '750', home_dir], capture_output=True)

            # 4. Tambah sudoers untuk terminal
            sudoers_line = f'root ALL=({linux_user}) NOPASSWD: /bin/bash\n'
            sudoers_file = '/etc/sudoers.d/sharehosting'
            try:
                with open(sudoers_file, 'r') as f:
                    existing = f.read()
            except FileNotFoundError:
                existing = ''
            if linux_user not in existing:
                with open(sudoers_file, 'a') as f:
                    f.write(sudoers_line)
                subprocess.run(['chmod', '440', sudoers_file])

            # 5. Simpan ke database
            user_id = User.create(
                username=username,
                email=email,
                password=password,
                linux_user=linux_user,
                home_dir=home_dir,
                disk_quota_mb=quota_mb,
                domain=domain
            )

            flash(f'User "{username}" berhasil dibuat! Linux user: {linux_user}, Folder: {home_dir}', 'success')
            return redirect(url_for('admin.dashboard'))

        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return render_template('admin/create_user.html')

    return render_template('admin/create_user.html')


def setup_rbash(linux_user, home_dir):
    """Setup restricted bash untuk user."""
    # Buat direktori bin di home user (hanya berisi command yang diizinkan)
    bin_dir = os.path.join(home_dir, 'bin')
    os.makedirs(bin_dir, exist_ok=True)

    allowed_commands = [
        'git', 'php', 'composer', 'npm', 'node', 'python3', 'pip3',
        'ls', 'pwd', 'mkdir', 'rm', 'cp', 'mv', 'cat', 'touch',
        'grep', 'find', 'echo', 'unzip', 'zip', 'tar', 'curl',
        'wget', 'clear', 'nano', 'vi', 'which', 'env'
    ]

    for cmd in allowed_commands:
        cmd_path = subprocess.run(['which', cmd], capture_output=True, text=True).stdout.strip()
        if cmd_path:
            link_path = os.path.join(bin_dir, cmd)
            if not os.path.exists(link_path):
                try:
                    os.symlink(cmd_path, link_path)
                except Exception:
                    pass

    # Setup .bashrc
    bashrc_content = f"""
# Restricted environment untuk {linux_user}
export HOME={home_dir}
export PATH={bin_dir}:/usr/local/bin:/usr/bin:/bin
export PS1='\\[\\033[01;32m\\]{linux_user}\\[\\033[00m\\]:\\[\\033[01;34m\\]\\w\\[\\033[00m\\]\\$ '
cd {home_dir}

# Disable dangerous commands
alias sudo='echo "sudo tidak diizinkan"'
alias su='echo "su tidak diizinkan"'
"""
    bashrc_path = os.path.join(home_dir, '.bashrc')
    with open(bashrc_path, 'w') as f:
        f.write(bashrc_content)

    subprocess.run(['chown', f'{linux_user}:www-data', bashrc_path])
    subprocess.run(['chmod', '644', bashrc_path])


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    User.toggle_active(user_id)
    flash('Status user berhasil diubah.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.get_by_id(user_id)
    if not user:
        flash('User tidak ditemukan.', 'danger')
        return redirect(url_for('admin.dashboard'))

    try:
        # Hapus Linux user
        subprocess.run(['userdel', '-r', user.linux_user], capture_output=True)

        # Hapus dari sudoers
        sudoers_file = '/etc/sudoers.d/sharehosting'
        try:
            with open(sudoers_file, 'r') as f:
                lines = f.readlines()
            with open(sudoers_file, 'w') as f:
                for line in lines:
                    if user.linux_user not in line:
                        f.write(line)
        except Exception:
            pass

        # Hapus dari DB
        User.delete(user_id)
        flash(f'User "{user.username}" berhasil dihapus.', 'success')
    except Exception as e:
        flash(f'Error menghapus user: {str(e)}', 'danger')

    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/users/<int:user_id>/quota', methods=['POST'])
@login_required
@admin_required
def update_quota(user_id):
    quota_mb = request.form.get('quota_mb', 1024)
    try:
        quota_mb = int(quota_mb)
        User.update_quota(user_id, quota_mb)
        flash('Quota berhasil diperbarui.', 'success')
    except ValueError:
        flash('Quota tidak valid.', 'danger')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/users/<int:user_id>/domain', methods=['POST'])
@login_required
@admin_required
def update_domain(user_id):
    domain = request.form.get('domain', '').strip()
    User.update_domain(user_id, domain or None)
    flash('Domain berhasil diperbarui.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_password(user_id):
    user = User.get_by_id(user_id)
    new_password = request.form.get('new_password', '')
    if not user or not new_password:
        flash('Data tidak valid.', 'danger')
        return redirect(url_for('admin.dashboard'))

    # Update password Linux
    proc = subprocess.Popen(
        ['chpasswd'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    proc.communicate(input=f'{user.linux_user}:{new_password}'.encode())

    # Update password DB
    pw_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
    cur = db_conn.connection.cursor()
    cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (pw_hash, user_id))
    db_conn.connection.commit()
    cur.close()

    flash(f'Password user "{user.username}" berhasil direset.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/logs')
@login_required
@admin_required
def logs():
    cur = db_conn.connection.cursor()
    cur.execute("""
        SELECT ts.*, u.username
        FROM terminal_sessions ts
        JOIN users u ON ts.user_id = u.id
        ORDER BY ts.started_at DESC
        LIMIT 100
    """)
    sessions = cur.fetchall()
    cur.close()
    return render_template('admin/logs.html', sessions=sessions)
