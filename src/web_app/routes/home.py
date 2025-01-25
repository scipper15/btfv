from datetime import datetime

from flask import Blueprint, render_template

home_bp = Blueprint("home", __name__, template_folder="../templates")


@home_bp.route("/")
def home() -> str:
    breadcrumbs = [
        {"name": "Home", "url": "/"},
    ]

    return render_template(
        "home.html",
        breadcrumbs=breadcrumbs,
    )


@home_bp.context_processor
def inject_now() -> dict[str, str | int]:
    return {"now": datetime.now().year}
