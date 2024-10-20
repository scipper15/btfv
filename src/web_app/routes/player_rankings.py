from flask import Blueprint, render_template, request, url_for

from web_app.services.get_environment import get_db_session
from web_app.services.player import (
    get_most_recent_season,
    get_player_ranking,
    get_seasons,
)

ranking_bp = Blueprint("ranking", __name__)


@ranking_bp.route("/")
def show_ranking() -> str:
    """Renders the ranking table based on the selected season or all-time.

    Query Parameters:
        year (int, optional): The season year to filter players by.
        eternal (bool, optional): If True, retrieves all-time rankings.
                                  Overrides 'year' if set.

    Returns:
        Rendered HTML template with player rankings.
    """
    session = get_db_session()

    # Retrieve query parameters
    year_to_show = request.args.get("year")
    if year_to_show is not None:
        try:
            year_to_show = int(year_to_show)  # type: ignore
        except ValueError:
            year_to_show = None

    base_url = url_for("ranking.show_ranking")
    current_season = get_most_recent_season(session)

    # Fetch player rankings based on year_to_show
    player_ranking = get_player_ranking(session, year_to_show)  # type: ignore

    # Fetch all available seasons for the dropdown
    seasons = get_seasons(session=session)

    breadcrumbs = [
        {"name": "Home", "url": "/"},
        {"name": "Rankings", "url": "/"},  # Current page
        {"name": "All Players Rankings", "url": None},  # Current page
    ]

    return render_template(
        "player_rankings.html",
        seasons=seasons,
        players=player_ranking,
        current_season=current_season,
        year_to_show=year_to_show,
        base_url=base_url,
        breadcrumbs=breadcrumbs,
    )
