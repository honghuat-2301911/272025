"""Controller for social feed routes and logic

Handles displaying the feed, creating posts, and adding comments
"""

from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    url_for,
    jsonify,
    flash
)
from flask_login import login_required, current_user

from domain.control.social_feed_management import (
    get_all_posts_control, get_featured_posts_control, create_post_control,
    create_comment_control, like_post_control, unlike_post_control, get_post_by_id_control,
    get_posts_by_user_id_control
)

from data_source.user_queries import search_users_by_name, get_user_by_id
import functools

social_feed_bp = Blueprint("social_feed", __name__, url_prefix="/feed")

def user_required(func):
    """
    Decorator to ensure the current_user is logged in AND has role 'user'.
    Admins (or anyone else) will be redirected away.Add commentMore actions
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.role != 'user':
            return redirect(url_for("admin.bulletin_page"))
        return func(*args, **kwargs)
    return wrapper


"""Render the main social feed page with all posts"""


@social_feed_bp.route("/", methods=["GET"])
@login_required
@user_required
def feed():
    posts = get_all_posts_control()
    featured_posts = get_featured_posts_control()
    return render_template(
        "socialfeed/social_feed.html", posts=posts, featured_posts=featured_posts
    )


"""Handle creation of a new post, including optional image upload"""


@social_feed_bp.route("/create", methods=["POST"])
@login_required
@user_required
def create_post():
    if not current_user.is_authenticated:
        return redirect(url_for("login.login"))

    user_id = int(current_user.get_id())
    content = request.form["content"]
    image_file = request.files.get("image") if "image" in request.files else None

    create_post_control(user_id, content, image_file)
    return redirect(url_for("social_feed.feed"))


"""Handle creation of a new comment for a specific post"""


@social_feed_bp.route("/comment/<int:post_id>", methods=["POST"])
@login_required
@user_required
def create_comment(post_id):
    if not current_user.is_authenticated:
        return redirect(url_for("login.login"))

    user_id = int(current_user.get_id())
    content = request.form["comment"]
    create_comment_control(post_id, user_id, content)
    return redirect(url_for("social_feed.feed"))


@social_feed_bp.route("/like/<int:post_id>", methods=["POST"])
@login_required
@user_required
def like_post(post_id):
    success = like_post_control(post_id)
    return {"success": success}


@social_feed_bp.route("/unlike/<int:post_id>", methods=["POST"])
@login_required
@user_required
def unlike_post(post_id):
    success = unlike_post_control(post_id)
    return {"success": success}


"""Render the social feed page filtered to show only a specific post"""


@social_feed_bp.route("/post/<int:post_id>", methods=["GET"])
@login_required
@user_required
def view_post(post_id):
    all_posts = get_all_posts_control()
    featured_posts = get_featured_posts_control()
    target_post = get_post_by_id_control(post_id)

    if target_post:
        # Filter to show only the target post
        filtered_posts = [post for post in all_posts if post.id == post_id]
        return render_template(
            "socialfeed/social_feed.html",
            posts=filtered_posts,
            featured_posts=featured_posts,
            filtered_post_id=post_id,
        )
    else:
        # If post not found, redirect to main feed
        return redirect(url_for("social_feed.feed"))


"""Search for users by name for autocomplete functionality"""


@social_feed_bp.route("/search-users", methods=["GET"])
@login_required
@user_required
def search_users():
    search_term = request.args.get("q", "")
    if len(search_term) < 2:
        return jsonify([])

    users = search_users_by_name(search_term, limit=10)
    # Format users for dropdown
    user_list = []
    for user in users:
        user_list.append(
            {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "profile_picture": user.get("profile_picture", ""),
            }
        )

    return jsonify(user_list)


"""Render the social feed page filtered to show only posts by a specific user"""


@social_feed_bp.route("/user/<int:user_id>", methods=["GET"])
@login_required
@user_required
def view_user_posts(user_id):
    filtered_posts = get_posts_by_user_id_control(user_id)
    featured_posts = get_featured_posts_control()
    # Get user name and profile picture from DB
    user_name = None
    user_profile_picture = None
    user_data = get_user_by_id(user_id)
    if user_data:
        user_name = user_data.get("name")
        user_profile_picture = user_data.get("profile_picture", "")
    return render_template(
        "socialfeed/social_feed.html",
        posts=filtered_posts,
        featured_posts=featured_posts,
        filtered_user_id=user_id,
        filtered_user_name=user_name,
        filtered_user_profile_picture=user_profile_picture,
    )
