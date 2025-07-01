"""User registration control logic and business rules"""

from data_source.user_queries import get_user_by_email, insert_user


def register_user(user_data: dict) -> bool:
    # TODO: Implement register function
    existing_user = get_user_by_email(user_data["email"])
    if existing_user:
        print("User already exists with this email.")
        return False
    return insert_user(user_data)
