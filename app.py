import logging
import os
import traceback
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, session, url_for
from flask_limiter import Limiter
from flask_limiter.errors import RateLimitExceeded
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, current_user
from flask_session import Session
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
from itsdangerous import URLSafeTimedSerializer
from werkzeug.exceptions import HTTPException

from data_source.user_queries import get_user_by_id, get_user_session_token
from domain.entity.user import User
from presentation.controller.admin_controller import admin_bp
from presentation.controller.bulletin_controller import bulletin_bp
from presentation.controller.login_controller import login_bp
from presentation.controller.profile_controller import profile_bp
from presentation.controller.register_controller import register_bp
from presentation.controller.social_feed_controller import social_feed_bp


class LevelFilter(logging.Filter):
    def __init__(self, level):
        self.level = level

    def filter(self, record):
        return record.levelno == self.level


def setup_logging(app, error_log_file, warning_log_file, info_log_file):
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    )

    # Error handler
    error_handler = RotatingFileHandler(
        error_log_file, maxBytes=10 * 1024 * 1024, backupCount=200, encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    error_handler.addFilter(LevelFilter(logging.ERROR))

    # Warning handler
    warning_handler = RotatingFileHandler(
        warning_log_file, maxBytes=10 * 1024 * 1024, backupCount=200, encoding="utf-8"
    )
    warning_handler.setLevel(logging.WARNING)
    warning_handler.setFormatter(formatter)
    warning_handler.addFilter(LevelFilter(logging.WARNING))

    # Info handler
    info_handler = RotatingFileHandler(
        info_log_file, maxBytes=10 * 1024 * 1024, backupCount=200, encoding="utf-8"
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)
    info_handler.addFilter(LevelFilter(logging.INFO))

    # Remove default handlers
    app.logger.handlers.clear()

    # Add all handlers
    app.logger.addHandler(error_handler)
    app.logger.addHandler(warning_handler)
    app.logger.addHandler(info_handler)
    app.logger.setLevel(logging.INFO)


def create_app():
    load_dotenv()

    app = Flask(
        __name__,
        template_folder="presentation/templates",
        static_folder="presentation/static",
        static_url_path="/static",
    )

    # Configuration for log format and handling

    log_dir = "/app/logs"

    os.makedirs(log_dir, exist_ok=True)

    error_log_file = os.path.join(log_dir, "error.log")
    warning_log_file = os.path.join(log_dir, "warning.log")
    info_log_file = os.path.join(log_dir, "info.log")

    setup_logging(app, error_log_file, warning_log_file, info_log_file)

    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "")
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
        minutes=30
    )  # Browser cookie timeout

    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    Session(app)

    login_manager = LoginManager()
    login_manager.login_view = "login.login"
    login_manager.init_app(app)
    login_manager.session_protection = (
        "strong"  # Check the user's IP address and User-Agent on every request.
    )
    # Log the user out if either changes (to help prevent session hijacking).

    csrf = CSRFProtect(app)

    limiter = Limiter(
        app=app, key_func=get_remote_address, default_limits=["10 per second"]
    )

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

    # --- SESSION TIMEOUT HANDLER ---
    IDLE_TIMEOUT = timedelta(seconds=15 * 60)  # 15 minutes
    ABSOLUTE_TIMEOUT = timedelta(seconds=30 * 60)  # 30 minutes

    @app.before_request
    def enforce_session_timeouts():

        LOGIN_VIEW = "login.login"
        if not session.get("created_at"):
            return  # Not logged in or session not set yet
        now = datetime.now(timezone.utc)
        created_at = session.get("created_at")
        last_activity = session.get("last_activity")
        # Convert from string if needed
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        if isinstance(last_activity, str):
            last_activity = datetime.fromisoformat(last_activity)
        # Absolute timeout
        if now - created_at > ABSOLUTE_TIMEOUT:
            session.clear()  # Clear session
            flash("Session expired. Please log in again.", "warning")
            return redirect(url_for(LOGIN_VIEW))
        # Idle timeout
        if now - last_activity > IDLE_TIMEOUT:
            session.clear()  # Clear session
            flash("Session expired due to inactivity. Please log in again.", "warning")
            return redirect(url_for(LOGIN_VIEW))

        if hasattr(current_user, "is_authenticated") and current_user.is_authenticated:
            user_token = get_user_session_token(current_user.id)
            if session.get("session_token") != user_token:
                session.clear()
                flash(
                    "You have been logged out because your account was accessed from another device.",
                    "warning",
                )
                return redirect(url_for(LOGIN_VIEW))
        # Update last activity
        session["last_activity"] = now.isoformat()

    # Configuration for email verification
    app.config["SERIALIZER"] = URLSafeTimedSerializer(app.config["SECRET_KEY"])

    @app.errorhandler(RateLimitExceeded)
    def ratelimit_handler(e):
        ip = get_remote_address()
        app.logger.warning(f"Rate limit exceeded by IP: {ip}")
        return (
            render_template(
                "error/error.html",
                error_code=429,
                error_message="Too many requests. Please wait and try again.",
            ),
            429,
        )

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        # Default values
        code = 500
        message = str(e)
        exception_type = type(e).__name__
        tb = traceback.format_exc()

        # If the exception is an HTTPException, extract details
        if isinstance(e, HTTPException):
            code = e.code
            message = e.description

        # Log the error with traceback
        app.logger.error(f"Exception occurred: {exception_type}: {message}\n{tb}")

        return render_template("error/csrf-error.html"), 400

    @app.errorhandler(Exception)
    def handle_exception(e):
        # Default values
        code = 500
        message = str(e)
        exception_type = type(e).__name__
        tb = traceback.format_exc()

        # If the exception is an HTTPException, extract details
        if isinstance(e, HTTPException):
            code = e.code
            message = e.description

        # Log the error with traceback
        app.logger.error(f"Exception occurred: {exception_type}: {message}\n{tb}")

        return (
            render_template(
                "error/error.html",
                error_code=code,
                error_message="We're sorry, but an unexpected error has occurred.",
            ),
            code,
        )

    # make sure DB has the required tables
    # init_schema()
    return app


if __name__ == "__main__":
    app = create_app()
    # debug=True is only for local dev!
    # app.run(debug=True)
