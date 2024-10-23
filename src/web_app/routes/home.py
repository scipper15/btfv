from flask import Blueprint, render_template

home_bp = Blueprint("home", __name__, template_folder="../templates")


@home_bp.route("/")
def home() -> str:
    return render_template(
        "home.html",
    )
