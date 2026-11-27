from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, abort, jsonify
from flask_login import login_required, current_user
import os
import shutil
import zipfile
import mimetypes
from datetime import datetime
from werkzeug.utils import secure_filename

filemanager_bp = Blueprint('filemanager', __name__)


def get_safe_path(user_home, relative_path=''):
    """Pastikan path tidak keluar dari home directory user."""
    base = os.path.realpath(user_home)
    if relative_path:
        target = os.path.realpath(os.path.join(base, relative_path.lstrip('/')))
    else:
        target = base
    # Security check - tidak boleh keluar dari home dir
    if not target.startswith(base):
        return None
    return target


def get_file_info(path):
    """Ambil info file/folder."""
    stat = os.stat(path)
    is_dir = os.path.isdir(path)
    size = stat.st_size if not is_dir else 0
    modified = datetime.fromtimestamp(stat.st_mtime)
    
    # Format size
    if size < 1024:
        size_str = f"{size} B"
    elif size < 1024 * 1024:
        size_str = f"{size/1024:.1f} KB"
    else:
        size_str = f"{size/1024/1024:.1f} MB"

    # Icon berdasarkan ekstensi
    ext = os.path.splitext(path)[1].lower()
    icon_map = {
        '.php': 'fab fa-php text-purple',
        '.py': 'fab fa-python text-warning',
        '.js': 'fab fa-js text-warning',
        '.html': 'fab fa-html5 text-danger',
        '.css': 'fab fa-css3 text-primary',
        '.json': 'fas fa-code text-success',
        '.md': 'fab fa-markdown text-muted',
        '.txt': 'fas fa-file-alt text-muted',
        '.zip': 'fas fa-file-zipper text-warning',
        '.tar': 'fas fa-file-zipper text-warning',
        '.gz': 'fas fa-file-zipper text-warning',
        '.sql': 'fas fa-database text-info',
        '.env': 'fas fa-lock text-danger',
        '.sh': 'fas fa-terminal text-success',
        '.jpg': 'fas fa-image text-pink',
        '.jpeg': 'fas fa-image text-pink',
        '.png': 'fas fa-image text-pink',
        '.gif': 'fas fa-image text-pink',
        '.svg': 'fas fa-image text-pink',
        '.pdf': 'fas fa-file-pdf text-danger',
    }
    
    if is_dir:
        icon = 'fas fa-folder text-warning'
    else:
        icon = icon_map.get(ext, 'fas fa-file text-secondary')

    return {
        'name': os.path.basename(path),
        'path': path,
        'is_dir': is_dir,
        'size': size,
        'size_str': size_str,
        'modified': modified.strftime('%d/%m/%Y %H:%M'),
        'icon': icon,
        'ext': ext
    }


@filemanager_bp.route('/files', defaults={'subpath': ''})
@filemanager_bp.route('/files/<path:subpath>')
@login_required
def index(subpath):
    if getattr(current_user, 'is_admin', False):
        abort(403)

    home_dir = current_user.home_dir
    current_path = get_safe_path(home_dir, subpath)

    if current_path is None:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('filemanager.index'))

    if not os.path.exists(current_path):
        flash('Folder tidak ditemukan.', 'warning')
        return redirect(url_for('filemanager.index'))

    if not os.path.isdir(current_path):
        # Kalau file, langsung download
        return redirect(url_for('filemanager.download', subpath=subpath))

    # List isi direktori
    items = []
    try:
        for name in sorted(os.listdir(current_path)):
            full_path = os.path.join(current_path, name)
            try:
                info = get_file_info(full_path)
                # Relative path dari home dir
                rel = os.path.relpath(full_path, home_dir)
                info['rel_path'] = rel
                items.append(info)
            except Exception:
                pass
    except PermissionError:
        flash('Tidak ada izin untuk membaca folder ini.', 'danger')

    # Sort: folder dulu, lalu file
    items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))

    # Breadcrumb
    rel_current = os.path.relpath(current_path, home_dir)
    breadcrumbs = []
    if rel_current != '.':
        parts = rel_current.replace('\\', '/').split('/')
        for i, part in enumerate(parts):
            crumb_path = '/'.join(parts[:i+1])
            breadcrumbs.append({'name': part, 'path': crumb_path})

    return render_template(
        'filemanager.html',
        items=items,
        current_path=current_path,
        subpath=subpath,
        home_dir=home_dir,
        breadcrumbs=breadcrumbs,
        rel_current=rel_current
    )


@filemanager_bp.route('/files/download/<path:subpath>')
@login_required
def download(subpath):
    home_dir = current_user.home_dir
    file_path = get_safe_path(home_dir, subpath)

    if file_path is None or not os.path.isfile(file_path):
        abort(404)

    return send_file(file_path, as_attachment=True)


@filemanager_bp.route('/files/view/<path:subpath>')
@login_required
def view_file(subpath):
    home_dir = current_user.home_dir
    file_path = get_safe_path(home_dir, subpath)

    if file_path is None or not os.path.isfile(file_path):
        abort(404)

    # Hanya tampilkan file teks
    text_extensions = ['.php', '.py', '.js', '.html', '.css', '.json', '.md',
                       '.txt', '.sh', '.env', '.sql', '.xml', '.yaml', '.yml',
                       '.ini', '.conf', '.log', '.htaccess']
    ext = os.path.splitext(file_path)[1].lower()

    if ext not in text_extensions:
        return redirect(url_for('filemanager.download', subpath=subpath))

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        flash(f'Gagal membaca file: {str(e)}', 'danger')
        parent = os.path.dirname(subpath)
        return redirect(url_for('filemanager.index', subpath=parent))

    # Parent path untuk breadcrumb
    parent_path = os.path.dirname(subpath)
    filename = os.path.basename(subpath)

    return render_template(
        'filemanager_view.html',
        content=content,
        filename=filename,
        subpath=subpath,
        parent_path=parent_path,
        ext=ext
    )


@filemanager_bp.route('/files/edit/<path:subpath>', methods=['GET', 'POST'])
@login_required
def edit_file(subpath):
    home_dir = current_user.home_dir
    file_path = get_safe_path(home_dir, subpath)

    if file_path is None or not os.path.isfile(file_path):
        abort(404)

    if request.method == 'POST':
        content = request.form.get('content', '')
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            flash('File berhasil disimpan.', 'success')
        except Exception as e:
            flash(f'Gagal menyimpan: {str(e)}', 'danger')
        return redirect(url_for('filemanager.edit_file', subpath=subpath))

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        flash(f'Gagal membaca file: {str(e)}', 'danger')
        return redirect(url_for('filemanager.index', subpath=os.path.dirname(subpath)))

    parent_path = os.path.dirname(subpath)
    filename = os.path.basename(subpath)

    return render_template(
        'filemanager_edit.html',
        content=content,
        filename=filename,
        subpath=subpath,
        parent_path=parent_path
    )


@filemanager_bp.route('/files/upload/<path:subpath>', methods=['POST'])
@filemanager_bp.route('/files/upload', defaults={'subpath': ''}, methods=['POST'])
@login_required
def upload(subpath):
    home_dir = current_user.home_dir
    upload_dir = get_safe_path(home_dir, subpath)

    if upload_dir is None or not os.path.isdir(upload_dir):
        flash('Folder tidak valid.', 'danger')
        return redirect(url_for('filemanager.index', subpath=subpath))

    files = request.files.getlist('files')
    uploaded = 0
    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            dest = os.path.join(upload_dir, filename)
            file.save(dest)
            uploaded += 1

    flash(f'{uploaded} file berhasil diupload.', 'success')
    return redirect(url_for('filemanager.index', subpath=subpath))


@filemanager_bp.route('/files/mkdir', methods=['POST'])
@login_required
def mkdir():
    home_dir = current_user.home_dir
    subpath = request.form.get('subpath', '')
    folder_name = request.form.get('folder_name', '').strip()

    if not folder_name:
        flash('Nama folder tidak boleh kosong.', 'danger')
        return redirect(url_for('filemanager.index', subpath=subpath))

    # Filter karakter berbahaya tanpa secure_filename
    forbidden = ['/', '\\', '..', '\0']
    for f in forbidden:
        if f in folder_name:
            flash('Nama folder tidak valid.', 'danger')
            return redirect(url_for('filemanager.index', subpath=subpath))

    new_folder = get_safe_path(home_dir, os.path.join(subpath, folder_name))

    if new_folder is None:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('filemanager.index', subpath=subpath))

    try:
        os.makedirs(new_folder, exist_ok=True)
        flash(f'Folder "{folder_name}" berhasil dibuat.', 'success')
    except Exception as e:
        flash(f'Gagal membuat folder: {str(e)}', 'danger')

    return redirect(url_for('filemanager.index', subpath=subpath))


@filemanager_bp.route('/files/delete', methods=['POST'])
@login_required
def delete():
    home_dir = current_user.home_dir
    subpath = request.form.get('subpath', '')
    target_rel = request.form.get('target', '')
    parent_path = os.path.dirname(target_rel)

    target = get_safe_path(home_dir, target_rel)

    if target is None or not os.path.exists(target):
        flash('File tidak ditemukan.', 'danger')
        return redirect(url_for('filemanager.index', subpath=parent_path))

    # Jangan hapus home dir itu sendiri
    if os.path.realpath(target) == os.path.realpath(home_dir):
        flash('Tidak bisa menghapus root directory.', 'danger')
        return redirect(url_for('filemanager.index'))

    try:
        if os.path.isdir(target):
            shutil.rmtree(target)
        else:
            os.remove(target)
        flash(f'"{os.path.basename(target)}" berhasil dihapus.', 'success')
    except Exception as e:
        flash(f'Gagal menghapus: {str(e)}', 'danger')

    return redirect(url_for('filemanager.index', subpath=parent_path))


@filemanager_bp.route('/files/rename', methods=['POST'])
@login_required
def rename():
    home_dir = current_user.home_dir
    target_rel = request.form.get('target', '')
    new_name = request.form.get('new_name', '').strip()
    parent_path = os.path.dirname(target_rel)

    if not new_name:
        flash('Nama baru tidak boleh kosong.', 'danger')
        return redirect(url_for('filemanager.index', subpath=parent_path))

    # Jangan pakai secure_filename agar .env, .htaccess dll tetap valid
    # Hanya filter karakter berbahaya
    forbidden = ['/', '\\', '..', '\0']
    for f in forbidden:
        if f in new_name:
            flash('Nama file tidak valid.', 'danger')
            return redirect(url_for('filemanager.index', subpath=parent_path))

    target = get_safe_path(home_dir, target_rel)
    new_path = get_safe_path(home_dir, os.path.join(parent_path, new_name))

    if target is None or new_path is None:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('filemanager.index', subpath=parent_path))

    try:
        os.rename(target, new_path)
        flash(f'Berhasil direname menjadi "{new_name}".', 'success')
    except Exception as e:
        flash(f'Gagal rename: {str(e)}', 'danger')

    return redirect(url_for('filemanager.index', subpath=parent_path))


@filemanager_bp.route('/files/newfile', methods=['POST'])
@login_required
def new_file():
    home_dir = current_user.home_dir
    subpath = request.form.get('subpath', '')
    filename = request.form.get('filename', '').strip()

    if not filename:
        flash('Nama file tidak boleh kosong.', 'danger')
        return redirect(url_for('filemanager.index', subpath=subpath))

    # Filter karakter berbahaya tanpa secure_filename
    forbidden = ['/', '\\', '..', '\0']
    for f in forbidden:
        if f in filename:
            flash('Nama file tidak valid.', 'danger')
            return redirect(url_for('filemanager.index', subpath=subpath))

    file_path = get_safe_path(home_dir, os.path.join(subpath, filename))

    if file_path is None:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('filemanager.index', subpath=subpath))

    try:
        with open(file_path, 'w') as f:
            f.write('')
        flash(f'File "{filename}" berhasil dibuat.', 'success')
        rel = os.path.relpath(file_path, home_dir)
        return redirect(url_for('filemanager.edit_file', subpath=rel))
    except Exception as e:
        flash(f'Gagal membuat file: {str(e)}', 'danger')
        return redirect(url_for('filemanager.index', subpath=subpath))


@filemanager_bp.route('/files/bulk-delete', methods=['POST'])
@login_required
def bulk_delete():
    import json
    home_dir = current_user.home_dir
    subpath = request.form.get('subpath', '')
    targets_json = request.form.get('targets', '[]')

    try:
        targets = json.loads(targets_json)
    except Exception:
        flash('Data tidak valid.', 'danger')
        return redirect(url_for('filemanager.index', subpath=subpath))

    deleted = 0
    errors = 0
    for target_rel in targets:
        target = get_safe_path(home_dir, target_rel)
        if target is None or not os.path.exists(target):
            errors += 1
            continue
        if os.path.realpath(target) == os.path.realpath(home_dir):
            errors += 1
            continue
        try:
            if os.path.isdir(target):
                shutil.rmtree(target)
            else:
                os.remove(target)
            deleted += 1
        except Exception:
            errors += 1

    if deleted:
        flash(f'{deleted} item berhasil dihapus.', 'success')
    if errors:
        flash(f'{errors} item gagal dihapus.', 'warning')

    return redirect(url_for('filemanager.index', subpath=subpath))


@filemanager_bp.route('/files/bulk-move', methods=['POST'])
@login_required
def bulk_move():
    import json
    home_dir = current_user.home_dir
    dest_subpath = request.form.get('dest_subpath', '')
    targets_json = request.form.get('targets', '[]')
    operation = request.form.get('operation', 'cut')

    try:
        targets = json.loads(targets_json)
    except Exception:
        flash('Data tidak valid.', 'danger')
        return redirect(url_for('filemanager.index', subpath=dest_subpath))

    dest_dir = get_safe_path(home_dir, dest_subpath)
    if dest_dir is None or not os.path.isdir(dest_dir):
        flash('Folder tujuan tidak valid.', 'danger')
        return redirect(url_for('filemanager.index', subpath=dest_subpath))

    moved = 0
    errors = 0
    for target_rel in targets:
        target = get_safe_path(home_dir, target_rel)
        if target is None or not os.path.exists(target):
            errors += 1
            continue
        if os.path.realpath(target) == os.path.realpath(home_dir):
            errors += 1
            continue

        dest_path = os.path.join(dest_dir, os.path.basename(target))

        # Jangan pindah ke dirinya sendiri
        if os.path.realpath(target) == os.path.realpath(dest_path):
            errors += 1
            continue

        try:
            if operation == 'cut':
                shutil.move(target, dest_path)
            else:
                # copy
                if os.path.isdir(target):
                    shutil.copytree(target, dest_path)
                else:
                    shutil.copy2(target, dest_path)
            moved += 1
        except Exception as e:
            errors += 1

    op_name = 'dipindahkan' if operation == 'cut' else 'disalin'
    if moved:
        flash(f'{moved} item berhasil {op_name}.', 'success')
    if errors:
        flash(f'{errors} item gagal.', 'warning')

    return redirect(url_for('filemanager.index', subpath=dest_subpath))


@filemanager_bp.route('/files/permission', methods=['POST'])
@login_required
def set_permission():
    home_dir = current_user.home_dir
    target_rel = request.form.get('target', '')
    permission = request.form.get('permission', '').strip()
    recursive = request.form.get('recursive', '') == '1'
    parent_path = os.path.dirname(target_rel)

    # Validasi permission
    if not permission or not permission.isdigit() or len(permission) not in [3, 4]:
        flash('Permission tidak valid. Gunakan format octal (contoh: 755).', 'danger')
        return redirect(url_for('filemanager.index', subpath=parent_path))

    # Validasi nilai octal
    try:
        perm_int = int(permission, 8)
    except ValueError:
        flash('Permission tidak valid.', 'danger')
        return redirect(url_for('filemanager.index', subpath=parent_path))

    target = get_safe_path(home_dir, target_rel)
    if target is None or not os.path.exists(target):
        flash('File tidak ditemukan.', 'danger')
        return redirect(url_for('filemanager.index', subpath=parent_path))

    try:
        if recursive and os.path.isdir(target):
            # Terapkan ke semua file di dalam folder
            for root, dirs, files in os.walk(target):
                os.chmod(root, perm_int)
                for f in files:
                    try:
                        os.chmod(os.path.join(root, f), perm_int)
                    except Exception:
                        pass
        else:
            os.chmod(target, perm_int)

        name = os.path.basename(target)
        flash(f'Permission "{name}" berhasil diubah ke {permission}.', 'success')
    except PermissionError:
        flash('Tidak ada izin untuk mengubah permission file ini.', 'danger')
    except Exception as e:
        flash(f'Gagal mengubah permission: {str(e)}', 'danger')

    return redirect(url_for('filemanager.index', subpath=parent_path))
