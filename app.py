from flask import Flask
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_sock import Sock
from extensions import db_conn, bcrypt, login_manager, sock
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Init extensions
    db_conn.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    sock.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Silakan login terlebih dahulu.'
    login_manager.login_message_category = 'warning'

    # Register blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.terminal import terminal_bp
    from routes.admin import admin_bp
    from routes.filemanager import filemanager_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(terminal_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(filemanager_bp)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)
