from flask import Blueprint, render_template, session
from flask_login import login_required, current_user
from flask_sock import Sock
from extensions import sock
import os
import pty
import select
import termios
import struct
import fcntl
import subprocess
import json
import threading

terminal_bp = Blueprint('terminal', __name__)

# Simpan active PTY sessions
active_sessions = {}


def set_winsize(fd, row, col, xpix=0, ypix=0):
    """Set ukuran terminal window."""
    winsize = struct.pack('HHHH', row, col, xpix, ypix)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


def create_chroot_shell(user, home_dir):
    """
    Buat shell process yang terisolasi ke home_dir user.
    Menggunakan su + chroot atau direct subprocess dengan env terbatas.
    """
    # Environment terbatas untuk user
    env = {
        'HOME': home_dir,
        'USER': user.linux_user,
        'LOGNAME': user.linux_user,
        'SHELL': '/bin/bash',
        'TERM': 'xterm-256color',
        'PATH': '/usr/local/bin:/usr/bin:/bin:/usr/local/php/bin:/usr/local/composer',
        'PWD': home_dir,
        'LANG': 'en_US.UTF-8',
    }

    # Buat shell dengan chdir ke home_dir dan batasi akses
    # Gunakan su sebagai linux user jika user ada di sistem
    cmd = [
        'sudo', '-u', user.linux_user,
        '-H', '--',
        '/bin/bash', '--login'
    ]

    return cmd, env, home_dir


@terminal_bp.route('/terminal')
@login_required
def terminal():
    if getattr(current_user, 'is_admin', False):
        return "Admin tidak perlu terminal user.", 403
    return render_template('terminal.html', user=current_user)


@sock.route('/ws/terminal')
def terminal_ws(ws):
    """WebSocket handler untuk terminal."""
    from flask_login import current_user

    if not current_user.is_authenticated:
        ws.send(json.dumps({'type': 'error', 'data': 'Tidak terotorisasi'}))
        return

    user = current_user
    home_dir = user.home_dir

    # Pastikan home_dir ada
    if not os.path.isdir(home_dir):
        try:
            os.makedirs(home_dir, exist_ok=True)
            subprocess.run(['chown', f'{user.linux_user}:{user.linux_user}', home_dir])
        except Exception as e:
            ws.send(json.dumps({'type': 'error', 'data': f'Gagal membuat direktori: {str(e)}'}))
            return

    # Buat PTY
    master_fd, slave_fd = pty.openpty()

    env = {
        'HOME': home_dir,
        'USER': user.linux_user,
        'LOGNAME': user.linux_user,
        'SHELL': '/bin/bash',
        'TERM': 'xterm-256color',
        'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
        'PWD': home_dir,
        'LANG': 'en_US.UTF-8',
    }

    try:
        process = subprocess.Popen(
            ['sudo', '-u', user.linux_user, '-H', '--', '/bin/bash', '--login'],
            preexec_fn=os.setsid,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
            cwd=home_dir,
            close_fds=True
        )
    except Exception as e:
        ws.send(json.dumps({'type': 'error', 'data': f'Gagal membuka terminal: {str(e)}'}))
        os.close(master_fd)
        os.close(slave_fd)
        return

    os.close(slave_fd)
    session_id = str(process.pid)
    active_sessions[session_id] = process

    def read_output():
        """Baca output dari PTY dan kirim ke WebSocket."""
        try:
            while True:
                r, _, _ = select.select([master_fd], [], [], 0.1)
                if r:
                    try:
                        data = os.read(master_fd, 1024)
                        if not data:
                            break
                        ws.send(json.dumps({
                            'type': 'output',
                            'data': data.decode('utf-8', errors='replace')
                        }))
                    except OSError:
                        break
                # Cek apakah proses masih jalan
                if process.poll() is not None:
                    ws.send(json.dumps({'type': 'exit', 'data': 'Terminal session ended'}))
                    break
        except Exception:
            pass
        finally:
            try:
                os.close(master_fd)
            except Exception:
                pass

    read_thread = threading.Thread(target=read_output, daemon=True)
    read_thread.start()

    try:
        while True:
            message = ws.receive(timeout=30)
            if message is None:
                break

            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue

            if data.get('type') == 'input':
                try:
                    os.write(master_fd, data['data'].encode('utf-8'))
                except OSError:
                    break

            elif data.get('type') == 'resize':
                try:
                    set_winsize(master_fd, data.get('rows', 24), data.get('cols', 80))
                except Exception:
                    pass

            elif data.get('type') == 'ping':
                ws.send(json.dumps({'type': 'pong'}))

    except Exception:
        pass
    finally:
        try:
            process.terminate()
        except Exception:
            pass
        if session_id in active_sessions:
            del active_sessions[session_id]
