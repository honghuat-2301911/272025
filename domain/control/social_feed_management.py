import os

from flask import current_app, g
from werkzeug.utils import secure_filename

from data_source.social_feed_queries import add_comment, add_post, decrement_like
from data_source.social_feed_queries import delete_post as ds_delete_post
from data_source.social_feed_queries import (
    get_all_posts,
    get_featured_posts,
    get_post_by_id,
    get_posts_by_user_id,
    increment_like,
    update_post,
)
from domain.entity.social_post import Comment, Post

"""Check if the uploaded file has an allowed image extension """


def allowed_file(filename):

    return "." in filename and filename.rsplit(".", 1)[1].lower() in {
        "png",
        "jpg",
        "jpeg",
        "gif",
    }


"""Convert database rows to Post entities using actual DB field names """


def create_entity_from_row(result):

    post_list = []

    for row in result:
        # Convert comments to Comment entities
        comments = []
        for comment_data in row.get("comments", []):
            comment = Comment(
                id=comment_data["id"],
                post_id=row["id"],
                user=comment_data.get("user", ""),
                content=comment_data.get("content", ""),
                created_at="",  # No created_at in current schema
            )
            comments.append(comment)

        # Create Post entity using only DB field names
        post = Post(
            id=row["id"],
            user=row.get("user_name", ""),
            content=row.get("caption", ""),
            image_url=row.get("image_path", ""),
            created_at="",  # No created_at in current schema
            likes=row.get("like_count", 0) or 0,
            comments=comments,
        )
        # Attach profile_picture to the post object
        post.profile_picture = row.get("profile_picture", "")
        post_list.append(post)

    g.post_list = post_list
    return post_list


def get_all_posts_control():
    """Get all posts for display in the social feed

    Returns:
        list: List of Post entities
    """
    result = get_all_posts()
    if not result:
        return []

    post_list = create_entity_from_row(result)
    return post_list


"""Get featured posts (top 5 by likes) for display"""


def get_featured_posts_control():

    result = get_featured_posts()
    if not result:
        return []

    # Convert raw DB data to Post entities
    featured_list = []
    for row in result:
        # Create Post entity using only DB field names
        post = Post(
            id=row["id"],
            user=row.get("user_name", ""),
            content=row.get("caption", ""),
            image_url=row.get("image_path", ""),
            created_at="",  # No created_at in current schema
            likes=row.get("like_count", 0) or 0,
            comments=[],  # Featured posts don't need comments
        )
        # Attach profile_picture to the post object
        post.profile_picture = row.get("profile_picture", "")
        featured_list.append(post)

    return featured_list


"""Get a specific post by ID"""


def get_post_by_id_control(post_id):
    result = get_post_by_id(post_id)
    if not result:
        return None

    # Convert raw DB data to Post entity
    row = result[0] if isinstance(result, list) else result

    # Get comments for this post
    comments = []
    for comment_data in row.get("comments", []):
        comment = Comment(
            id=comment_data["id"],
            post_id=row["id"],
            user=comment_data.get("user", ""),
            content=comment_data.get("content", ""),
            created_at="",  # No created_at in current schema
        )
        comments.append(comment)

    # Create Post entity using only DB field names
    post = Post(
        id=row["id"],
        user=row.get("user_name", ""),
        content=row.get("caption", ""),
        image_url=row.get("image_path", ""),
        created_at="",  # No created_at in current schema
        likes=row.get("like_count", 0) or 0,
        comments=comments,
    )
    # Attach profile_picture to the post object
    post.profile_picture = row.get("profile_picture", "")

    return post


"""Handle creation of a new post with optional image upload"""


def create_post_control(user_id, content, image_file=None):
    image_url = None

    if image_file and image_file.filename:
        if allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            upload_folder = current_app.config.get(
                "UPLOAD_FOLDER", "presentation/static/images/social"
            )
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, filename)
            image_file.save(filepath)
            image_url = f"/static/images/social/{filename}"

    return add_post(user_id, content, image_url)


"""Handle creation of a new comment on a post"""


def create_comment_control(post_id, user_id, content):

    return add_comment(post_id, user_id, content)


def like_post_control(post_id):
    return increment_like(post_id)


def unlike_post_control(post_id):
    return decrement_like(post_id)


"""Get formatted display data for posts"""


def get_posts_display_data():
    post_list = g.get("post_list")
    if not post_list:
        return []

    display_data = []
    for post in post_list:
        display_data.append(
            {
                "id": post.id,
                "user": post.user,
                "content": post.content,
                "image_url": post.image_url,
                "likes": post.likes,
                "comments": [
                    {"id": comment.id, "user": comment.user, "content": comment.content}
                    for comment in post.comments
                ],
            }
        )

    return display_data


def editPost(
    userId: int, postId: int, updatedContent: str, removeImage: bool = False
) -> bool:
    post = get_post_by_id(postId)
    if not post or int(post["user_id"]) != userId:
        return False

    image_filename = post.get("image_path")
    # Remove image if requested
    if removeImage and image_filename:
        image_path = os.path.join(
            "presentation", "static", "uploads", os.path.basename(image_filename)
        )
        if os.path.exists(image_path):
            os.remove(image_path)
        image_filename = None

    # Update post in DB
    return update_post(postId, updatedContent, image_filename)


def deletePost(userId: int, postId: int) -> bool:
    post = get_post_by_id(postId)
    if not post or int(post["user_id"]) != userId:
        return False
    image_filename = post.get("image_path")
    if image_filename:
        image_path = os.path.join(
            "presentation", "static", "uploads", os.path.basename(image_filename)
        )
        if os.path.exists(image_path):
            os.remove(image_path)
    return ds_delete_post(postId)


"""Get all posts by a specific user ID"""


def get_posts_by_user_id_control(user_id):

    result = get_posts_by_user_id(user_id)
    if not result:
        return []

    post_list = create_entity_from_row(result)
    return post_list
