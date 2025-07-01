from flask import Blueprint, redirect, render_template, url_for, session
from flask_login import login_required, current_user
from domain.control.login_management import get_user_display_data, login_user, logout_user
from domain.entity.forms import LoginForm

login_bp = Blueprint(
    "login", __name__, url_prefix="/", template_folder="../templates/login"
)


@login_bp.route("/")
def root_redirect():
    return redirect(url_for("login.login"))


@login_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("bulletin.bulletin_page"))

    form = LoginForm()
    if form.validate_on_submit():
        # use form data
        user = login_user(form.email.data, form.password.data)
        if user:
            if user.role == "admin":
                return redirect(url_for("admin.bulletin_page"))
            else:
                return redirect(url_for("bulletin.bulletin_page"))
        # invalid credentials
        form.email.errors.append("Invalid email or password.")
    # either GET or validation failed
    return render_template("login/login.html", form=form)


@login_bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.pop('_flashes', None)
    return redirect(url_for("login.login"))
