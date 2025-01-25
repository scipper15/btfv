from flask import Blueprint, render_template

faq_bp = Blueprint("faq", __name__, template_folder="../templates")


@faq_bp.route("/faq")
def faq() -> str:
    breadcrumbs = [
        {"name": "Home", "url": "/"},
        {"name": "Frequently Asked Questions", "url": None},
    ]

    return render_template(
        "faq.html",
        breadcrumbs=breadcrumbs,
    )
