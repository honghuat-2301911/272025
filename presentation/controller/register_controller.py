import bcrypt
from flask import Blueprint, current_app, flash, redirect, render_template, url_for

from domain.control.register import (
    register_user,
    send_verification_email,
    update_verification_status,
)
from domain.entity.forms import RegisterForm, SubmitVerifyEmailForm

register_bp = Blueprint(
    "register", __name__, url_prefix="/", template_folder="../templates/"
)


@register_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # Prepare user data
        hashed = bcrypt.hashpw(
            form.password.data.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        user_data = {
            "name": form.name.data,
            "email": form.email.data,
            "password": hashed,
            "role": "user",
        }

        if register_user(user_data):
            current_app.logger.info(
                f"A user signed up with the email {form.email.data}"
            )
            send_verification_email(form.email.data)
            return render_template("register/verify_email.html", email=form.email.data)

        flash("Something went wrong. Please try again.", "error")
        return redirect(url_for("register.register"))

    # If GET or validation failed, render form with errors
    return render_template("register/register.html", form=form)


@register_bp.route("/verify/<token>", methods=["GET"])
def verify_email(token):
    verify_email_form = SubmitVerifyEmailForm()
    return render_template(
        "register/verify_button.html", token=token, verify_email_form=verify_email_form
    )


@register_bp.route("/verify", methods=["POST"])
def verify_email_post():
    verify_email_form = SubmitVerifyEmailForm()
    if verify_email_form.validate_on_submit():
        token = verify_email_form.token.data
        if not token:
            flash("Verification failed: Missing token.", "danger")
            return redirect(url_for("login.login"))
        success, result = update_verification_status(token)
        if success:
            flash("Your email has been verified! You can now log in.", "success")
        else:
            flash(result or "Invalid or expired token.", "danger")
    else:
        flash("Invalid form submission.", "danger")
    return redirect(url_for("login.login"))
