"""User login management for authentication and session handling"""

import bcrypt
from flask import g, current_app
from flask_login import login_user as flask_login_user
from flask_login import logout_user as flask_logout_user
from datetime import datetime, timezone, timedelta

from data_source.user_queries import get_user_by_email, update_user_lockout
from domain.entity.user import User

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 10


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
    

    # Check if account is locked
    utc_plus_8 = timezone(timedelta(hours=8))
    now = datetime.now(utc_plus_8)

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

    if not password_valid:
        # Update failed attempt count
        new_attempts = result.get("failed_attempts", 0) + 1
        locked_until = None
        
        # Lock account if threshold reached
        if new_attempts >= MAX_FAILED_ATTEMPTS:
            locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
            current_app.logger.warning(
                f"Account locked: {email} after {new_attempts} failed attempts"
            )
        
        # Update database
        update_user_lockout(
            user_id=result["id"],
            failed_attempts=new_attempts,
            last_failed_login=now.replace(tzinfo=None),
            locked_until=locked_until.replace(tzinfo=None) if locked_until else None
        )
        
        current_app.logger.warning(
            f"Failed login for {email} (attempt {new_attempts}/{MAX_FAILED_ATTEMPTS})"
        )
        return None

    # Reset lockout after successful login
    update_user_lockout(
        user_id=result["id"],
        failed_attempts=0,
        locked_until=None
    )

    user = User(
        id=result["id"],
        name=result["name"],
        password=result["password"],
        email=result["email"],
        role=result.get("role", "user"),
    )

    flask_login_user(user)
    return user


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
