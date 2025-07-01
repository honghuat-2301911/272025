from flask import Blueprint, redirect, render_template, session, url_for, request, flash
from domain.control.bulletin_management import *
from domain.control.admin_management import *
from domain.control.social_feed_management import *
from flask_login import login_required, current_user
import functools

# Create a blueprint for the admin page
admin_bp = Blueprint(
    "admin", __name__, url_prefix="/admin", template_folder="../templates"
)


def admin_required(func):
    """
    Custom decorator to check if the current user is authenticated and is an admin.
    This decorator should only be used to protect admin routes.
    """

    @functools.wraps(func)
    def admin_check(*args, **kwargs):
        # Check if the user is logged in and is an admin
        if current_user.role != 'admin':
            # Redirect to a different page if not admin
            return redirect(url_for("bulletin.bulletin_page"))
        return func(
            *args, **kwargs
        )  # Call the original function if authenticated as admin

    return admin_check  # Return the wrapped function


@admin_bp.route("/bulletin", methods=["GET", "POST"])
@login_required
@admin_required
def bulletin_page():
    query = request.form.get("query") if request.method == "POST" else None
    if query:
        result = search_bulletin(query)
    else:
        result = get_bulletin_listing()
    if not result:
        return render_template(
            "admin/bulletin.html", bulletin_list=[], error="No activities found."
        )
    bulletin_list = get_bulletin_display_data()
    return render_template("admin/bulletin.html", bulletin_list=bulletin_list)


@admin_bp.route("/delete_activity", methods=["POST"])
@login_required
@admin_required
def delete_activity():
    activity_id = request.form.get("activity_id")
    if not activity_id:
        flash("Activity ID is required.", "error")
        return redirect(url_for("admin.bulletin_page"))

    success = remove_sports_activity(activity_id)
    if success:
        flash("Activity deleted successfully.", "success")
    else:
        flash(
            "Failed to delete the activity. It may not exist or you may not have permission.",
            "error",
        )

    return redirect(url_for("admin.bulletin_page"))


@admin_bp.route("/feed", methods=["GET", "POST"])
@login_required
@admin_required
def feed_page():
    posts = get_all_posts_control()
    return render_template("admin/social_feed.html", posts=posts)


@admin_bp.route("/delete_post", methods=["POST"])
@login_required
@admin_required
def delete_post():
    post_id = request.form.get("post_id", type=int)
    success = remove_social_post(post_id)
    if success:
        flash("Post deleted successfully.", "success")
    else:
        flash("Failed to delete the post. It may not exist or you may not have permission.", "error")
    return redirect(url_for("admin.feed_page"))




