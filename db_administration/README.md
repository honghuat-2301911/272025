# Admin User Creation Script

This Python script lets you securely create a new admin user in your MySQL application database. The script loads credentials from your `.env` file, ensures password safety, and prevents duplicate admin emails.

## Features

- Interactive prompts for admin email and password.
- Password must be at least 8 characters.
- Passwords are securely hashed using bcrypt.
- Checks for duplicate email before creating the user.
- Uses environment variables for database credentials.

## Prerequisites

- Python 3.6 or higher
- MySQL server (running and accessible on `127.0.0.1:3306`)
- `.env` file with your DB credentials in the same directory as the script

## Installation

1. Install the required Python packages with:

   ```bash
   pip install -r requirements.txt
   ```

2. Run the script with:
    ```bash
   python3 add_admin.py
    ```