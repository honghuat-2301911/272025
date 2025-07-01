import os
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask_login import LoginManager
from flask_session import Session
from flask_wtf import CSRFProtect

from data_source.user_queries import get_user_by_id
from domain.entity.user import User
from presentation.controller.admin_controller import admin_bp
from presentation.controller.bulletin_controller import bulletin_bp
from presentation.controller.login_controller import login_bp
from presentation.controller.profile_controller import profile_bp
from presentation.controller.register_controller import register_bp
from presentation.controller.social_feed_controller import social_feed_bp

# from data_source.login_queries import init_schema


def create_app():
    app = Flask(
        __name__,
        template_folder="presentation/templates",
        static_folder="presentation/static",
        static_url_path="/static",
    )


    # Configuration for log format and handling

    log_dir = '/app/logs'
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'app.log')
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=200,              
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    ))
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)

    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "")
    app.config["SESSION_TYPE"] = "filesystem"

    # # Only send cookies over HTTPS
    # app.config['SESSION_COOKIE_SECURE']   = True
    # # Prevent JavaScript from reading the cookie
    # app.config['SESSION_COOKIE_HTTPONLY'] = True
    # # Control cross-site sending; options: 'Lax', 'Strict', or 'None'
    # app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # app.config['REMEMBER_COOKIE_SECURE']   = True
    # app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    # app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'

    Session(app)

    login_manager = LoginManager()
    login_manager.login_view = "login.login"
    login_manager.init_app(app)

    # csrf = CSRFProtect(app)

    @login_manager.user_loader
    def load_user(user_id):
        user_data = get_user_by_id(user_id)
        if user_data:
            return User(
                id=user_data["id"],
                name=user_data["name"],
                password=user_data["password"],
                email=user_data["email"],
                role=user_data.get("role", "user"),
                profile_picture=user_data.get("profile_picture", ""),
            )
        return None

    # register page-controller blueprints
    app.register_blueprint(login_bp)
    app.register_blueprint(social_feed_bp)
    app.register_blueprint(register_bp)
    app.register_blueprint(bulletin_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(profile_bp)

    # make sure DB has the required tables
    # init_schema()
    return app


if __name__ == "__main__":
    app = create_app()
    # debug=True is only for local dev!
    app.run(debug=True)
