"""User login management for authentication and session handling"""

import bcrypt
from flask import g, current_app
from flask_login import login_user as flask_login_user
from flask_login import logout_user as flask_logout_user
from datetime import datetime, timezone, timedelta

from data_source.user_queries import get_user_by_email, record_failed_login,
    get_user_failed_attempts_count,
    clear_failed_logins
from domain.entity.user import User

FAILED_ATTEMPT_LIMIT = 10
LOCKOUT_MINUTES = 15


def login_user(email: str, password: str):
    """
    Attempt to authenticate a user by email and password

    Args:
        email (str): User's email address
        password (str): User's password

    Returns:
        User: The authenticated User object if found, else None
    """
    result = get_user_by_email(email)
    if not result:
        return None

    # Get current time
    utc_plus_8 = timezone(timedelta(hours=8))
    now = datetime.now(utc_plus_8)

    # Check if account is locked
    if result.get("locked_until"):
        db_locked_until = result["locked_until"].replace(tzinfo=utc_plus_8)
        if db_locked_until > now:
            lock_time = db_locked_until.strftime("%Y-%m-%d %H:%M:%S")
            current_app.logger.warning(
                f"Locked account login attempt: {email} (locked until {lock_time})"
            )
            return None

    # Check password hash
    stored_hash = result["password"]
    password_valid = bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))

    # If password doesn't match, log failed attempt into DB
    if not password_valid:
        record_failed_login(result["id"]) 
        # Check failed attempts in past 10 minutes
        recent_failures = get_user_failed_attempts_count(result["id"], window_minutes=10)
        locked_until = None
        if recent_failures >= FAILED_ATTEMPT_LIMIT:
            locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
            update_user_lockout(result["id"], locked_until.replace(tzinfo=None))
            current_app.logger.warning(
                f"Account locked: {email} after {recent_failures} failed attempts in 10 minutes"
            )
        current_app.logger.warning(
            f"Failed login for {email} (attempt {recent_failures}/{FAILED_ATTEMPT_LIMIT})"
        )
        return None
    
    # On successful login, clear failed logins and unlock account
    clear_failed_logins(result["id"])
    update_user_lockout(result["id"], None)

    user = User(
        id=result["id"],
        name=result["name"],
        password=result["password"],
        email=result["email"],
        role=result.get("role", "user"),
    )

    flask_login_user(user)
    return user

# Get generate OTP
def verify_user_otp(user, otp_code):
    """
    Verifies the OTP code for the user.
    Args:
        user (User): The user object
        otp_code (str): The OTP code entered by the user
    Returns:
        bool: True if valid, False otherwise
    """
    if not user.otp_secret:
        return False
    totp = pyotp.TOTP(user.otp_secret)
    return totp.verify(otp_code)


def logout_user():
    """Log out the current user using flask_login"""
    flask_logout_user()


def get_user_display_data():
    """
    Retrieve display data for the currently logged-in user

    Returns:
        dict: User display information, or None if no user is logged in
    """
    user = g.get("current_user")
    if not user:
        return None

    return {
        # "id": user.get_id(),  # Uncomment if you want to display user ID
        "name": user.get_name(),
        "email": user.get_email(),
        "role": user.get_role(),
    }
