import os

import bcrypt
import mysql.connector
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

DB_HOST = "127.0.0.1"
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "")


def create_admin_user(email, password, name="admin"):
    # Hash the password securely with bcrypt
    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    # Connect to the MySQL database
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )
    cursor = conn.cursor()

    # Check if the user already exists
    cursor.execute("SELECT id FROM user WHERE email = %s", (email,))
    if cursor.fetchone():
        print(f"User with email '{email}' already exists.")
        cursor.close()
        conn.close()
        return

    # Prepare the SQL INSERT statement
    sql = """
        INSERT INTO user (
            name, password, email, role, profile_picture, locked_until, 
            otp_secret, otp_enabled, current_session_token, email_verified
        )
        VALUES (%s, %s, %s, 'admin', NULL, NULL, NULL, 0, NULL, 1)
    """
    values = (name, hashed_pw, email)

    try:
        cursor.execute(sql, values)
        conn.commit()
        print(f"Admin user '{email}' created successfully!")
    except mysql.connector.Error as err:
        print("Error:", err)
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    print("Create a new admin user")
    email = input("Enter admin email: ").strip()

    while True:
        password = input("Enter admin password (min 8 characters): ").strip()
        if len(password) < 8:
            print("Password must be at least 8 characters long. Please try again.")
        else:
            break

    create_admin_user(email, password)
