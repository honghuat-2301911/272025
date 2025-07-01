import os

import bcrypt
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from flask import jsonify, current_app, request

from data_source.bulletin_queries import (
    get_all_bulletin,
    get_connection,
    get_sports_activity_by_id,
    update_sports_activity,
    update_sports_activity_details,
)
from data_source.social_feed_queries import get_posts_by_user
from data_source.user_queries import get_user_by_id
from domain.control import social_feed_management
from domain.control.profile_management import ProfileManagement
from domain.control.social_feed_management import deletePost, editPost
from domain.entity.sports_activity import SportsActivity
from domain.entity.user import User
from domain.control.otp_management import generate_otp_for_user, verify_and_enable_otp

profile_bp = Blueprint(
    "profile_bp",
    __name__,
    template_folder="../templates/profile",
    url_prefix="/profile",
)


@profile_bp.route("/", methods=["GET"])
@login_required
def fetchProfile():
    user_id = int(current_user.get_id())
    user_data = get_user_by_id(user_id)
    user = None
    if isinstance(user_data, dict):
        id_val = user_data.get("id")
        if isinstance(id_val, int):
            user_id_val = id_val
        elif isinstance(id_val, str) and id_val.isdigit():
            user_id_val = int(id_val)
        else:
            user_id_val = 0
        user = User(
            user_id_val,
            str(user_data.get("name")) if user_data.get("name") is not None else "",
            (
                str(user_data.get("password"))
                if user_data.get("password") is not None
                else ""
            ),
            str(user_data.get("email")) if user_data.get("email") is not None else "",
            str(user_data.get("role", "user")),
            str(user_data.get("profile_picture", "")),
            user_data.get("otp_secret"),  # <-- Add this
            bool(int(user_data.get("otp_enabled", 0)))
        )
    user_posts = get_posts_by_user(user.get_name()) if user else []
    user_id_str = str(user.get_id()) if user else ""

    # Fetch all activities and filter for hosted/joined
    all_activities = get_all_bulletin()
    hosted_activities = []
    joined_only_activities = []
    if all_activities:
        for row in all_activities:
            row = dict(row)  # Ensure row is a dict
            activity = SportsActivity(
                id=int(row.get("id", 0)),
                user_id=int(row.get("user_id", 0)),
                activity_name=str(row.get("activity_name", "")),
                activity_type=str(row.get("activity_type", "")),
                skills_req=str(row.get("skills_req", "")),
                date=str(row.get("date", "")),
                location=str(row.get("location", "")),
                max_pax=int(row.get("max_pax", 0)),
                user_id_list_join=row.get("user_id_list_join", None),
            )
            # Hosted: user_id matches current user
            if activity.user_id == user_id:
                hosted_activities.append(activity)
            # Joined: user_id is in join list, but not the host
            else:
                joined_ids = [
                    uid.strip()
                    for uid in (activity.user_id_list_join or "").split(",")
                    if uid.strip()
                ]
                if str(user_id) in joined_ids:
                    joined_only_activities.append(activity)
    return render_template(
        "profile/profile.html",
        user=user,
        posts=user_posts,
        hosted_activities=hosted_activities,
        joined_only_activities=joined_only_activities,
    )


@profile_bp.route("/", methods=["POST"])
@login_required
def editProfile():
    user_id = int(current_user.get_id())
    name = request.form["name"]
    password = request.form["password"]
    profile_manager = ProfileManagement()
    profile_picture_url = None
    remove_picture = request.form.get("remove_profile_picture") == "on"
    # Handle file upload
    if (
        "profile_picture" in request.files
        and request.files["profile_picture"].filename != ""
    ):
        file = request.files["profile_picture"]
        filename = secure_filename(file.filename)
        image_path = os.path.join(
            "presentation", "static", "images", "profile", filename
        )
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        file.save(image_path)
        profile_picture_url = f"/static/images/profile/{filename}"
    elif remove_picture:
        profile_picture_url = ""
    # Password logic
    if password:
        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        if profile_picture_url is not None:
            result = profile_manager.updateProfile(
                user_id, name, hashed_password, profile_picture_url
            )
        else:
            result = profile_manager.updateProfile(user_id, name, hashed_password)
    else:
        user_data = get_user_by_id(user_id)
        current_password = (
            user_data["password"]
            if isinstance(user_data, dict) and "password" in user_data
            else ""
        )
        if profile_picture_url is not None:
            result = profile_manager.updateProfile(
                user_id, name, current_password, profile_picture_url
            )
        else:
            result = profile_manager.updateProfile(user_id, name, current_password)
    return redirect(url_for("profile_bp.fetchProfile"))


@profile_bp.route("/leave_activity/<int:activity_id>", methods=["POST"])
@login_required
def leave_activity(activity_id):
    user_id = str(current_user.get_id())
    activity = get_sports_activity_by_id(activity_id)
    if not activity or not activity.get("user_id_list_join"):
        flash("Activity not found or you are not a participant.", "danger")
        return redirect(url_for("profile_bp.fetchProfile"))
    joined_ids = [
        uid.strip() for uid in activity["user_id_list_join"].split(",") if uid.strip()
    ]
    if user_id in joined_ids:
        joined_ids.remove(user_id)
        new_join_list = ",".join(joined_ids)
        update_sports_activity(activity_id, new_join_list)
        flash("You have left the activity.", "success")
    else:
        flash("You are not a participant in this activity.", "warning")
    return redirect(url_for("profile_bp.fetchProfile") + "#activitiesSection")


@profile_bp.route("/edit_activity/<int:activity_id>", methods=["POST"])
@login_required
def edit_activity(activity_id):
    user_id = int(current_user.get_id())
    activity = get_sports_activity_by_id(activity_id)
    if not activity or int(activity["user_id"]) != user_id:
        flash("You are not authorized to edit this activity.", "danger")
        return redirect(url_for("profile_bp.fetchProfile"))
    # Get new details from form
    activity_name = request.form["activity_name"]
    activity_type = request.form["activity_type"]
    skills_req = request.form["skills_req"]
    date = request.form["date"]
    location = request.form["location"]
    max_pax = request.form["max_pax"]
    user_id_list_join = activity.get("user_id_list_join", "")
    # Update the activity using the data source function
    update_sports_activity_details(
        activity_id,
        activity_name,
        activity_type,
        skills_req,
        date,
        location,
        max_pax,
        user_id_list_join,
    )
    flash("Activity updated successfully.", "success")
    return redirect(url_for("profile_bp.fetchProfile") + "#activitiesSection")


@profile_bp.route("/edit_post/<int:post_id>", methods=["POST"])
@login_required
def edit_post(post_id):
    user_id = int(current_user.get_id())
    updated_content = request.form["content"]
    remove_image = request.form.get("remove_image") == "on"
    success = editPost(user_id, post_id, updated_content, remove_image)
    if success:
        flash("Post updated successfully.", "success")
    else:
        flash("Failed to update post.", "danger")
    return redirect(url_for("profile_bp.fetchProfile") + "#feedSection")


@profile_bp.route("/delete_post/<int:post_id>", methods=["POST"])
@login_required
def delete_post(post_id):
    user_id = int(current_user.get_id())
    success = deletePost(user_id, post_id)
    if success:
        flash("Post deleted successfully.", "success")
    else:
        flash("Failed to delete post.", "danger")
    return redirect(url_for("profile_bp.fetchProfile") + "#feedSection")

@profile_bp.route("/generate_otp", methods=["POST"])
@login_required
def generate_otp():
    try:
        user_id = int(current_user.get_id())
        otp_data, error = generate_otp_for_user(user_id)
        if error:
            return jsonify({'status': 'error', 'message': error}), 400
        return jsonify({'status': 'success', 'qr': otp_data["qr"], 'secret': otp_data["secret"]})
    except Exception as e:
        current_app.logger.error(f"OTP generation error: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to generate OTP setup'}), 500

@profile_bp.route("/verify_otp", methods=["POST"])
@login_required
def verify_otp():
    try:
        user_id = int(current_user.get_id())
        otp_code = request.json.get("otp_code")
        success, error = verify_and_enable_otp(user_id, otp_code)
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': error}), 400
    except Exception as e:
        current_app.logger.error(f"OTP verification error: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to verify OTP'}), 500

@profile_bp.route("/check_otp_status")
@login_required
def check_otp_status():
    user_id = int(current_user.get_id())
    user_data = get_user_by_id(user_id)
    otp_enabled = user_data.get("otp_enabled", False) if user_data else False
    return jsonify({'otp_enabled': bool(otp_enabled)})