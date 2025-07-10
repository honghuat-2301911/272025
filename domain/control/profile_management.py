import os
import uuid

import bcrypt
from flask import current_app, g
from PIL import Image
from werkzeug.utils import secure_filename

from data_source.bulletin_queries import (
    get_hosted_activities,
    get_joined_activities,
    get_joined_user_names_by_activity_id,
    get_sports_activity_by_id,
    update_sports_activity,
    update_sports_activity_details,
)
from data_source.social_feed_queries import get_posts_by_user_id
from data_source.user_queries import (
    disable_otp_by_user_id,
    get_user_by_id,
    remove_user_profile_picture,
    update_user_profile_by_id,
)
from domain.control.otp_management import generate_otp_for_user, verify_and_enable_otp
from domain.control.social_feed_management import delete_post, edit_post
from domain.entity.social_post import Comment, Post
from domain.entity.sports_activity import SportsActivity
from domain.entity.user import User


class ProfileManagement:
    def update_profile(self, user_id, name, password, profile_picture=None):
        if profile_picture is not None:
            return update_user_profile_by_id(user_id, name, password, profile_picture)
        return update_user_profile_by_id(user_id, name, password)

    def remove_profile_picture(self, user_id):
        return remove_user_profile_picture(user_id)

    def get_joined_user_names(self, activity_id):
        return get_joined_user_names_by_activity_id(activity_id)

    def get_user_profile(self, user_id):
        user_data = get_user_by_id(user_id)
        if not isinstance(user_data, dict):
            return None
        id_val = user_data.get("id")
        if isinstance(id_val, int):
            user_id_val = id_val
        elif isinstance(id_val, str) and id_val.isdigit():
            user_id_val = int(id_val)
        else:
            user_id_val = 0
        # Safely convert database values to proper types
        otp_secret_val = user_data.get("otp_secret")
        if otp_secret_val is not None:
            otp_secret_val = str(otp_secret_val)

        otp_enabled_val = user_data.get("otp_enabled", 0)
        if isinstance(otp_enabled_val, (int, str)):
            otp_enabled_val = bool(int(otp_enabled_val))
        else:
            otp_enabled_val = False

        user = User(
            id=user_id_val,
            name=(
                str(user_data.get("name")) if user_data.get("name") is not None else ""
            ),
            password=(
                str(user_data.get("password"))
                if user_data.get("password") is not None
                else ""
            ),
            email=(
                str(user_data.get("email"))
                if user_data.get("email") is not None
                else ""
            ),
            role=str(user_data.get("role", "user")),
            profile_picture=str(user_data.get("profile_picture", "")),
            otp_secret=otp_secret_val,
            otp_enabled=otp_enabled_val,
        )
        # Store user data in Flask g object
        g.current_user_profile = user
        return user

    def get_user_posts(self, user_id):
        posts = get_posts_by_user_id(user_id)
        post_objs = []
        for post in posts:
            comments = [
                Comment(
                    id=int(c.get("id", 0) or 0),
                    post_id=int(post.get("id", 0) or 0),
                    user=str(c.get("user", "")),
                    content=str(c.get("content", "")),
                    profile_picture=str(c.get("profile_picture", "")),
                )
                for c in post.get("comments", [])
            ]
            # Handle likes being None or empty string
            likes_val = post.get("likes", 0)
            if likes_val in (None, ""):
                likes_val = 0
            else:
                likes_val = int(likes_val)
            post_obj = Post(
                id=int(post.get("id", 0) or 0),
                user=str(post.get("user", "")),
                content=str(post.get("content", "")),
                image_url=str(post.get("image_url", "")),
                likes=likes_val,
                comments=comments,
                like_user_ids=str(post.get("like_user_ids", "")),
            )
            post_objs.append(post_obj)
        # Store user posts in Flask g object
        g.user_posts = post_objs
        return post_objs

    def create_entity_from_row(self, hosted_activities_raw, joined_activities_raw):
        hosted_activities = [
            {
                "id": a["id"],
                "activity_name": a["activity_name"],
                "activity_type": a["activity_type"],
                "skills_req": a["skills_req"],
                "date": a["date"],
                "location": a["location"],
                "max_pax": a["max_pax"],
            }
            for a in hosted_activities_raw
        ]
        joined_only_activities = [
            {
                "id": a["id"],
                "activity_name": a["activity_name"],
                "activity_type": a["activity_type"],
                "skills_req": a["skills_req"],
                "date": a["date"],
                "location": a["location"],
                "max_pax": a["max_pax"],
            }
            for a in joined_activities_raw
        ]
        g.user_hosted_activities = hosted_activities
        g.user_joined_activities = joined_only_activities

    def set_user_activities(self, user_id):
        hosted_activities_raw = get_hosted_activities(user_id)
        joined_activities_raw = get_joined_activities(user_id)
        self.create_entity_from_row(hosted_activities_raw, joined_activities_raw)
        # No return

    def update_profile_full(self, user_id, form):
        name = form.name.data
        password = form.password.data
        remove_picture = form.remove_profile_picture.data

        profile_picture_url = self._handle_profile_picture_upload(form)
        if profile_picture_url is False:
            return False
        if remove_picture:
            profile_picture_url = ""

        hashed_password = self._handle_password(password)
        if hashed_password is False:
            return False

        if hashed_password:
            result = self.update_profile(
                user_id, name, hashed_password, profile_picture_url
            )
        else:
            user_data = get_user_by_id(user_id)
            current_password = (
                user_data["password"]
                if isinstance(user_data, dict) and "password" in user_data
                else ""
            )
            if profile_picture_url is not None:
                result = self.update_profile(
                    user_id, name, current_password, profile_picture_url
                )
            else:
                result = self.update_profile(user_id, name, current_password)

        if result:
            g.updated_profile = {
                "user_id": user_id,
                "name": name,
                "profile_picture_url": profile_picture_url,
            }
        return result

    def _handle_profile_picture_upload(self, form):
        if form.profile_picture.data:
            file = form.profile_picture.data
            try:
                file.seek(0)
                image = Image.open(file)
                image.verify()
                file.seek(0)
            except (UnidentifiedImageError, OSError) as e:
                current_app.logger.warning(
                    f"Uploaded profile picture is not a valid image: {e}"
                )
                return False
            ext = os.path.splitext(secure_filename(file.filename))[1]
            unique_filename = f"{uuid.uuid4().hex}{ext}"
            image_path = os.path.join(
                "presentation", "static", "images", "profile", unique_filename
            )
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            file.save(image_path)
            return f"/static/images/profile/{unique_filename}"
        return None

    def _handle_password(self, password):
        if password:
            try:
                return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
                    "utf-8"
                )
            except Exception:
                return False
        return None

    def edit_activity(self, user_id, activity_id, form):
        activity_data = get_sports_activity_by_id(activity_id)
        if not activity_data:
            return False, "Activity not found."

        if hasattr(activity_data, "get") and callable(activity_data.get):
            activity = SportsActivity(
                id=int(activity_data.get("id", 0)),
                user_id=int(activity_data.get("user_id", 0)),
                activity_name=str(activity_data.get("activity_name", "")),
                activity_type=str(activity_data.get("activity_type", "")),
                skills_req=str(activity_data.get("skills_req", "")),
                date=str(activity_data.get("date", "")),
                location=str(activity_data.get("location", "")),
                max_pax=int(activity_data.get("max_pax", 0)),
                user_id_list_join=str(activity_data.get("user_id_list_join", "")),
            )
        else:
            activity = SportsActivity(
                id=int(getattr(activity_data, "id", 0)),
                user_id=int(getattr(activity_data, "user_id", 0)),
                activity_name=str(getattr(activity_data, "activity_name", "")),
                activity_type=str(getattr(activity_data, "activity_type", "")),
                skills_req=str(getattr(activity_data, "skills_req", "")),
                date=str(getattr(activity_data, "date", "")),
                location=str(getattr(activity_data, "location", "")),
                max_pax=int(getattr(activity_data, "max_pax", 0)),
                user_id_list_join=str(getattr(activity_data, "user_id_list_join", "")),
            )

        if activity.get_user_id() != user_id:
            return False, "You can only edit activities you created."

        if not form.validate_on_submit():
            return False, "Invalid form data."

        # Update fields from form
        activity.activity_name = form.activity_name.data
        activity.activity_type = form.activity_type.data
        activity.skills_req = form.skills_req.data
        activity.date = form.date.data
        activity.location = form.location.data
        activity.max_pax = form.max_pax.data

        result = update_sports_activity_details(
            activity.id,
            activity.activity_name,
            activity.activity_type,
            activity.skills_req,
            activity.date,
            activity.location,
            activity.max_pax,
            activity.user_id_list_join,
        )
        if result:
            g.updated_activity = activity
            return True, "Activity updated successfully."
        return False, "Failed to update activity."

    def edit_post(self, user_id, post_id, form):
        result = edit_post(user_id, post_id, form.content.data, form.remove_image.data)
        if result and result[0]:
            g.updated_post = {
                "user_id": user_id,
                "post_id": post_id,
                "content": form.content.data,
                "remove_image": form.remove_image.data,
            }
        return result

    def leave_activity(self, user_id, activity_id):
        activity = get_sports_activity_by_id(activity_id)
        if not activity:
            return False, "Activity not found."
        if hasattr(activity, "get") and callable(activity.get):
            user_id_list_join = activity.get("user_id_list_join", "") or ""
        else:
            user_id_list_join = getattr(activity, "user_id_list_join", "") or ""
        if not isinstance(user_id_list_join, str):
            user_id_list_join = str(user_id_list_join)
        joined_ids = [
            uid.strip()
            for uid in user_id_list_join.split(",")
            if isinstance(uid, str) and uid.strip()
        ]
        if str(user_id) not in joined_ids:
            return False, "You are not a participant in this activity."
        joined_ids.remove(str(user_id))
        new_join_list = ",".join(joined_ids)
        result = update_sports_activity(activity_id, new_join_list)
        if result:
            g.left_activity = {
                "user_id": user_id,
                "activity_id": activity_id,
                "new_join_list": new_join_list,
            }
            return True, "Successfully left the activity."
        return False, "Failed to leave the activity."

    def delete_post(self, user_id, post_id):
        success = delete_post(user_id, post_id)
        if success:
            g.deleted_post = {"user_id": user_id, "post_id": post_id}
            return True, "Post deleted successfully."
        return False, "Failed to delete post."

    def generate_otp(self, user_id):
        result = generate_otp_for_user(user_id)
        if result:
            g.generated_otp = {"user_id": user_id, "otp": result}
        return result

    def verify_otp(self, user_id, otp_code):
        result = verify_and_enable_otp(user_id, otp_code)
        if result:
            current_app.logger.info(f"User {user_id} enabled 2 factor authentication")
            g.verified_otp = {"user_id": user_id, "otp_code": otp_code}

        return result

    def disable_otp(self, user_id):
        result = disable_otp_by_user_id(user_id)
        if result:
            current_app.logger.warning(
                f"User {user_id} disabled 2 factor authentication"
            )
            g.disabled_otp = {"user_id": user_id}
        return result

    def get_profile_display_data(self):
        """
        Retrieve display data for the current user profile

        Returns:
            dict: User profile display information, or None if no user is logged in
        """
        user = g.get("current_user_profile")
        if not user:
            return None

        return {
            "id": user.get_id(),
            "name": user.get_name(),
            "email": user.get_email(),
            "role": user.get_role(),
            "profile_picture": user.get_profile_picture(),
            "otp_enabled": user.get_otp_enabled(),
        }

    def get_user_posts_display_data(self):
        """
        Retrieve display data for the current user's posts

        Returns:
            list: List of user posts display information, or empty list if no posts
        """
        posts = g.get("user_posts", [])
        if not posts:
            return []

        return [
            {
                "id": post.get_id(),
                "user": post.get_user(),
                "content": post.get_content(),
                "image_url": post.get_image_url(),
                "created_at": post.get_created_at(),
                "likes": post.get_likes(),
                "comments_count": len(post.get_comments()),
                "like_user_ids": post.get_like_user_ids(),
            }
            for post in posts
        ]

    def get_user_activities_display_data(self):
        hosted_activities = g.get("user_hosted_activities", [])
        joined_only_activities = g.get("user_joined_activities", [])
        return hosted_activities, joined_only_activities
