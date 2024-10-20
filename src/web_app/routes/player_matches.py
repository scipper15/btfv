from uuid import UUID

from flask import Blueprint, render_template, request, url_for

from web_app.services.get_environment import get_db_session
from web_app.services.player import (
    get_last_match_date,
    get_latest_player_ratings,
    get_most_recent_season,
    get_player_match_data,
    get_player_seasons,
)
from web_app.services.team import get_latest_team_membership

player_bp = Blueprint("player", __name__, template_folder="../templates")


@player_bp.route("/<uuid:player_id>")
def player(player_id: UUID) -> str:
    session = get_db_session()

    # Retrieve query parameters
    year_to_show = request.args.get("year")
    if year_to_show is not None:
        try:
            year_to_show = int(year_to_show)  # type: ignore
        except ValueError:
            year_to_show = None

    base_url = url_for("player.player", player_id=player_id)
    current_season = get_most_recent_season(session)
    player = get_latest_player_ratings(session, player_id, year_to_show)  # type: ignore
    last_played_match_date = get_last_match_date(session, player.id, year_to_show)  # type: ignore
    seasons = get_player_seasons(
        session, player_id
    )  # list of all seasons a player played in
    player_info = get_latest_team_membership(
        session,
        player_id,  # type: ignore
        year_to_show,  # type: ignore
    )
    matches = get_player_match_data(session, player.name, year_to_show)  # type: ignore

    breadcrumbs = [
        {"name": "Home", "url": "/"},
        {"name": "Rankings", "url": "/ranking"},
        {
            "name": "All Players Rankings",
            "url": url_for("ranking.show_ranking", year=[current_season]),
        },
        {"name": player.name, "url": None},  # type: ignore
    ]

    return render_template(
        "player_matches.html",
        seasons=seasons,
        last_played_match_date=last_played_match_date,
        player_id=player_id,
        player=player,
        player_info=player_info,
        matches=matches,
        current_season=current_season,
        year_to_show=year_to_show,
        base_url=base_url,
        breadcrumbs=breadcrumbs,
    )
