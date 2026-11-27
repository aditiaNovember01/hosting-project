from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_sock import Sock

db_conn = MySQL()
bcrypt = Bcrypt()
login_manager = LoginManager()
sock = Sock()


@login_manager.user_loader
def load_user(user_id):
    from models import User, Admin
    # Admin ID format: 'admin_<id>'
    if str(user_id).startswith('admin_'):
        real_id = str(user_id).replace('admin_', '')
        return Admin.get_by_id(real_id)
    return User.get_by_id(user_id)

