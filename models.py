from flask_login import UserMixin
from extensions import db_conn, bcrypt


class User(UserMixin):
    def __init__(self, data):
        self.id = data['id']
        self.username = data['username']
        self.email = data['email']
        self.password_hash = data['password_hash']
        self.linux_user = data['linux_user']
        self.home_dir = data['home_dir']
        self.domain = data.get('domain') or '-'
        self.disk_quota_mb = data['disk_quota_mb']
        self.is_active_flag = data['is_active']
        self.is_admin = data['is_admin']
        self.created_at = data['created_at']
        self.last_login = data['last_login']

    def is_active(self):
        return bool(self.is_active_flag)

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    @staticmethod
    def get_by_id(user_id):
        cur = db_conn.connection.cursor()
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        data = cur.fetchone()
        cur.close()
        if data:
            return User(data)
        return None

    @staticmethod
    def get_by_username(username):
        cur = db_conn.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        data = cur.fetchone()
        cur.close()
        if data:
            return User(data)
        return None

    @staticmethod
    def get_all():
        cur = db_conn.connection.cursor()
        cur.execute("SELECT * FROM users ORDER BY created_at DESC")
        rows = cur.fetchall()
        cur.close()
        return [User(r) for r in rows]

    @staticmethod
    def create(username, email, password, linux_user, home_dir, disk_quota_mb=1024, domain=None):
        pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        cur = db_conn.connection.cursor()
        cur.execute(
            """INSERT INTO users (username, email, password_hash, linux_user, home_dir, domain, disk_quota_mb)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (username, email, pw_hash, linux_user, home_dir, domain, disk_quota_mb)
        )
        db_conn.connection.commit()
        new_id = cur.lastrowid
        cur.close()
        return new_id

    @staticmethod
    def update_domain(user_id, domain):
        cur = db_conn.connection.cursor()
        cur.execute("UPDATE users SET domain = %s WHERE id = %s", (domain, user_id))
        db_conn.connection.commit()
        cur.close()

    @staticmethod
    def update_last_login(user_id):
        cur = db_conn.connection.cursor()
        cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))
        db_conn.connection.commit()
        cur.close()

    @staticmethod
    def toggle_active(user_id):
        cur = db_conn.connection.cursor()
        cur.execute("UPDATE users SET is_active = NOT is_active WHERE id = %s", (user_id,))
        db_conn.connection.commit()
        cur.close()

    @staticmethod
    def delete(user_id):
        cur = db_conn.connection.cursor()
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        db_conn.connection.commit()
        cur.close()

    @staticmethod
    def update_quota(user_id, quota_mb):
        cur = db_conn.connection.cursor()
        cur.execute("UPDATE users SET disk_quota_mb = %s WHERE id = %s", (quota_mb, user_id))
        db_conn.connection.commit()
        cur.close()


class Admin(UserMixin):
    def __init__(self, data):
        self.id = 'admin_' + str(data['id'])
        self.real_id = data['id']
        self.username = data['username']
        self.email = data['email']
        self.password_hash = data['password_hash']
        self.is_admin = True

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    @staticmethod
    def get_by_username(username):
        cur = db_conn.connection.cursor()
        cur.execute("SELECT * FROM admins WHERE username = %s", (username,))
        data = cur.fetchone()
        cur.close()
        if data:
            return Admin(data)
        return None

    @staticmethod
    def get_by_id(admin_id):
        cur = db_conn.connection.cursor()
        cur.execute("SELECT * FROM admins WHERE id = %s", (admin_id,))
        data = cur.fetchone()
        cur.close()
        if data:
            return Admin(data)
        return None

    @staticmethod
    def create(username, email, password):
        pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        cur = db_conn.connection.cursor()
        cur.execute(
            "INSERT INTO admins (username, email, password_hash) VALUES (%s, %s, %s)",
            (username, email, pw_hash)
        )
        db_conn.connection.commit()
        cur.close()
