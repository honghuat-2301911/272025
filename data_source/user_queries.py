import mysql.connector

from data_source.db_connection import get_connection
from datetime import datetime
from flask import current_app

def set_otp_secret(otp_secret, user_id):
    try:
        connection = get_connection()
        cursor = connection.cursor(buffered=True)
        cursor.execute(
            "UPDATE user SET otp_secret=%s WHERE id=%s",
            (otp_secret, user_id)
        )
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Exception as e:
        current_app.logger.error(f"Error setting OTP secret: {e}")
        return False

def enable_2fa(user_id):
    try:
        connection = get_connection()
        cursor = connection.cursor(buffered=True)
        cursor.execute(
            "UPDATE user SET otp_enabled=1 WHERE id=%s",
            (user_id,)
        )
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Exception as e:
        current_app.logger.error(f"Error enabling 2FA: {e}")
        return False

# Account Lock out Code
def record_failed_login(user_id):
    """Insert a failed login record for the user."""
    connection = get_connection()
    cursor = connection.cursor()
    now = datetime.now(UTC_PLUS_8).replace(tzinfo=None)
    cursor.execute(
        "INSERT INTO user_failed_login (user_id, failed_at) VALUES (%s, %s)",
        (user_id, now)
    )
    connection.commit()
    cursor.close()
    connection.close()

def get_user_failed_attempts_count(user_id, window_minutes=10):
    """Count failed logins for user in the last window_minutes."""
    connection = get_connection()
    cursor = connection.cursor()
    window_start = datetime.now(UTC_PLUS_8) - timedelta(minutes=window_minutes)
    window_start = window_start.replace(tzinfo=None)
    cursor.execute(
        "SELECT COUNT(*) FROM user_failed_login WHERE user_id=%s AND failed_at >= %s",
        (user_id, window_start)
    )
    count = cursor.fetchone()[0]
    cursor.close()
    connection.close()
    return count

def update_user_lockout(user_id, locked_until):
    """
    Update the locked_until field in the user table.
    Args:
        user_id (int): The user's ID.
        locked_until (datetime or None): The datetime until which the account is locked, or None to unlock.
    """
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE user SET locked_until=%s WHERE id=%s",
            (locked_until, user_id)
        )
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Exception as e:
        current_app.logger.error(f"Error updating locked_until: {e}")
        return False

def clear_failed_logins(user_id):
    """Delete all failed login records for the user."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "DELETE FROM user_failed_login WHERE user_id=%s",
        (user_id,)
    )
    connection.commit()
    cursor.close()
    connection.close()

def get_user_by_email(email: str):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
    user_data = cursor.fetchone()
    cursor.close()
    connection.close()
    return user_data


# def insert_user(user_data: dict) -> bool:
#     """
#     Insert a new user into the database
#     Args:
#         user_data (dict): Dictionary containing user information

#     Returns:
#         bool: True if insertion is successful, False otherwise
#     """
#     try:
#         connection = get_connection()
#         cursor = connection.cursor()
#         query = """
#             INSERT INTO user (name, password, email, skill_lvl, sports_exp, role)
#             VALUES (%s, %s, %s, %s, %s, %s)
#         """
#         cursor.execute(
#             query,
#             (
#                 user_data["name"],
#                 user_data["password"],
#                 user_data["email"],
#                 user_data.get("skill_lvl"),
#                 user_data.get("sports_exp"),
#                 user_data.get("role", "user"),
#             ),
#         )
#         connection.commit()
#         return True
#     except mysql.connector.Error as e:
#         print("Insert failed:", e)
#         return False
#     finally:
#         if cursor:
#             cursor.close()
#         if connection:
#             connection.close()

"""Insert a new user into the database"""


def insert_user(user_data: dict) -> bool:
    try:
        connection = get_connection()
        cursor = connection.cursor()
        query = """
            INSERT INTO user (name, password, email, role, profile_picture)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(
            query,
            (
                user_data["name"],
                user_data["password"],
                user_data["email"],
                user_data.get("role", "user"),
                user_data.get("profile_picture", ""),
            ),
        )
        connection.commit()
        return True
    except Exception as e:
        print("Insert failed:", e)
        return False
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def get_user_by_id(user_id: int):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    connection.close()
    return user_data


def update_user_profile_by_id(
    user_id: int, name: str, password: str, profile_picture: str = None
) -> bool:
    connection = get_connection()
    cursor = connection.cursor()
    try:
        if profile_picture is not None:
            query = "UPDATE user SET name = %s, password = %s, profile_picture = %s WHERE id = %s"
            cursor.execute(query, (name, password, profile_picture, user_id))
        else:
            query = "UPDATE user SET name = %s, password = %s WHERE id = %s"
            cursor.execute(query, (name, password, user_id))
        connection.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print("Update failed:", e)
        return False
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def search_users_by_name(search_term: str, limit: int = 10):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        query = """
            SELECT id, name, email, profile_picture
            FROM user 
            WHERE name LIKE %s 
            ORDER BY name 
            LIMIT %s
        """
        search_pattern = f"%{search_term}%"
        cursor.execute(query, (search_pattern, limit))
        users = cursor.fetchall()
        return users
    except Exception as e:
        print(f"Search failed: {e}")
        return []
    finally:
        cursor.close()
        connection.close()


def remove_user_profile_picture(user_id: int) -> bool:
    connection = get_connection()
    if connection is None:
        print("[DB ERROR] Connection failed in remove_user_profile_picture")
        return False
    cursor = connection.cursor()
    try:
        query = "UPDATE user SET profile_picture = '' WHERE id = %s"
        cursor.execute(query, (user_id,))
        connection.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print("Remove profile picture failed:", e)
        return False
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
