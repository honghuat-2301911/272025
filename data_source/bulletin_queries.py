from data_source.db_connection import get_connection


def get_all_bulletin():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM sports_activity")
    bulletin_data = cursor.fetchall()
    cursor.close()
    connection.close()
    return bulletin_data


def get_bulletin_via_name(activity_name: str):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM sports_activity WHERE activity_name LIKE %s",
        (f"%{activity_name}%",),
    )
    bulletin_data = cursor.fetchall()
    cursor.close()
    connection.close()
    return bulletin_data


def get_sports_activity_by_id(activity_id: int):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM sports_activity WHERE id = %s", (activity_id,))
    activity_data = cursor.fetchone()
    cursor.close()
    connection.close()
    return activity_data


def update_sports_activity(activity_id: int, user_id_list_join: str):
    connection = get_connection()
    cursor = connection.cursor()
    query = """
        UPDATE sports_activity
        SET user_id_list_join = %s
        WHERE id = %s
    """
    cursor.execute(query, (user_id_list_join, activity_id))
    connection.commit()
    cursor.close()
    connection.close()


# def insert_new_activity(activity_data):
#     try:
#         connection = get_connection()
#         cursor = connection.cursor()

#         query = """
#         INSERT INTO sports_activity (
#             user_id, activity_name, activity_type, skills_req, date, location, max_pax
#         ) VALUES (%s, %s, %s, %s, %s, %s, %s)
#         """

#         cursor.execute(query, (
#             activity_data['user_id'],
#             activity_data['activity_name'],
#             activity_data['activity_type'],
#             activity_data['skills_req'],
#             activity_data['date'],
#             activity_data['location'],
#             activity_data['max_pax'],
#         ))

#         connection.commit()
#         return True

#     except Exception as e:
#         print("Insert failed:", e)
#         return False

#     finally:
#         if cursor:
#             cursor.close()
#         if connection:
#             connection.close()


def insert_new_activity(activity_data):
    connection = get_connection()
    cursor = connection.cursor()

    query = """
    INSERT INTO sports_activity (
        user_id, activity_name, activity_type, skills_req, date, location, max_pax
    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    cursor.execute(
        query,
        (
            activity_data["user_id"],
            activity_data["activity_name"],
            activity_data["activity_type"],
            activity_data["skills_req"],
            activity_data["date"],
            activity_data["location"],
            activity_data["max_pax"],
        ),
    )

    connection.commit()
    cursor.close()
    connection.close()
    return True


def get_bulletin_by_types(activity_types):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    format_strings = ",".join(["%s"] * len(activity_types))
    query = f"SELECT * FROM sports_activity WHERE activity_type IN ({format_strings})"

    cursor.execute(query, tuple(activity_types))
    data = cursor.fetchall()

    cursor.close()
    connection.close()
    return data


def update_sports_activity_details(
    activity_id,
    activity_name,
    activity_type,
    skills_req,
    date,
    location,
    max_pax,
    user_id_list_join,
):
    connection = get_connection()
    cursor = connection.cursor()
    query = """
        UPDATE sports_activity
        SET activity_name=%s, activity_type=%s, skills_req=%s, date=%s, location=%s, max_pax=%s, user_id_list_join=%s
        WHERE id=%s
    """
    cursor.execute(
        query,
        (
            activity_name,
            activity_type,
            skills_req,
            date,
            location,
            max_pax,
            user_id_list_join,
            activity_id,
        ),
    )
    connection.commit()
    cursor.close()
    connection.close()
    return True
