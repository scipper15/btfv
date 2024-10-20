from flask import Blueprint, render_template

from web_app.services.get_environment import get_db_session

home_bp = Blueprint("home", __name__, template_folder="../templates")


@home_bp.route("/")
def home() -> str:
    session = get_db_session()

    return render_template(
        "home.html",
    )
