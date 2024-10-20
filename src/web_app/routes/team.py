from uuid import UUID

from flask import Blueprint, render_template

from web_app.services.get_environment import get_db_session
from web_app.services.team import get_team_details

team_bp = Blueprint("team", __name__, template_folder="../templates")


@team_bp.route("/<uuid:team_id>")
def team(team_id: UUID) -> str:
    session = get_db_session()
    team_details = get_team_details(session, team_id)

    return render_template(
        "team.html",
        team_details=team_details,
    )