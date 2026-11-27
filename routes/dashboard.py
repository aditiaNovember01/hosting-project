from flask import Blueprint, render_template, redirect, url_for, flash, session
from flask_login import login_required, current_user
import os
import subprocess

dashboard_bp = Blueprint('dashboard', __name__)


def get_disk_usage(path):
    """Hitung penggunaan disk folder user dalam MB."""
    try:
        result = subprocess.run(
            ['du', '-sm', path],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            size_mb = int(result.stdout.split()[0])
            return size_mb
    except Exception:
        pass
    return 0


@dashboard_bp.route('/dashboard')
@login_required
def index():
    if getattr(current_user, 'is_admin', False) and session.get('role') == 'admin':
        return redirect(url_for('admin.dashboard'))

    home_dir = current_user.home_dir
    disk_used = get_disk_usage(home_dir)
    disk_quota = current_user.disk_quota_mb
    disk_percent = min(int((disk_used / disk_quota) * 100), 100) if disk_quota > 0 else 0

    # Cek apakah home dir ada
    dir_exists = os.path.isdir(home_dir)

    return render_template(
        'dashboard.html',
        user=current_user,
        disk_used=disk_used,
        disk_quota=disk_quota,
        disk_percent=disk_percent,
        dir_exists=dir_exists,
        home_dir=home_dir
    )
