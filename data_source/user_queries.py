import mysql.connector

from data_source.db_connection import get_connection
from datetime import datetime
from flask import current_app

def setotpsecret(otp_secret, user_id):
    """Save OTP secret and enable 2FA for user"""
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE user SET otp_secret=%s, otp_enabled=1 WHERE id=%s",
            (otp_secret, user_id)
        )
        connection.commit()
        cursor.close()
        return True
    except Exception as e:
        current_app.logger.error(f"Error setting OTP secret: {e}")
        return False

def update_user_lockout(
    user_id: int,
    failed_attempts: int,
    last_failed_login: datetime = None,
    locked_until: datetime = None
):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        sql = """
        UPDATE user SET failed_attempts = %s, last_failed_login = %s,locked_until = %s WHERE id = %s"""

        cursor.execute(sql, (
            failed_attempts,
            last_failed_login,
            locked_until,
            user_id
        ))
        connection.commit()
    except Exception as e:
        current_app.logger.error(f"Failed to update lockout fields: {e}")
        raise
    finally:
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
