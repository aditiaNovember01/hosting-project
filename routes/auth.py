from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from models import User, Admin
from extensions import db_conn

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/', methods=['GET'])
def index():
    if current_user.is_authenticated:
        if getattr(current_user, 'is_admin', False):
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('dashboard.index'))
    return render_template('landing.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        login_as = request.form.get('login_as', 'user')  # 'user' or 'admin'

        if login_as == 'admin':
            admin = Admin.get_by_username(username)
            if admin and admin.check_password(password):
                login_user(admin, remember=False)
                session['role'] = 'admin'
                flash('Selamat datang, Admin!', 'success')
                return redirect(url_for('admin.dashboard'))
            else:
                flash('Username atau password admin salah.', 'danger')
        else:
            user = User.get_by_username(username)
            if user and user.check_password(password):
                if not user.is_active_flag:
                    flash('Akun Anda dinonaktifkan. Hubungi administrator.', 'warning')
                    return render_template('login.html')
                login_user(user, remember=False)
                session['role'] = 'user'
                User.update_last_login(user.id)
                flash(f'Selamat datang, {user.username}!', 'success')
                return redirect(url_for('dashboard.index'))
            else:
                flash('Username atau password salah.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('auth.login'))
