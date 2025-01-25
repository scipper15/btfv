# type: ignore
from uuid import UUID

from flask import Blueprint, g, render_template, request, url_for

from web_app.services.data_preparation.mu_over_time import (
    prepare_match_data,
)
from web_app.services.graph_creation.mu_over_time import (
    create_player_performance_graph,
)
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
    # Retrieve query parameters
    year_to_show = request.args.get("year")
    if year_to_show is not None:
        try:
            year_to_show = int(year_to_show)
        except ValueError:
            year_to_show = None

    session = g.db_session
    base_url = url_for("player.player", player_id=player_id)
    current_season = get_most_recent_season(session)
    player = get_latest_player_ratings(session, player_id, year_to_show)
    last_played_match_date = get_last_match_date(session, player.id, year_to_show)
    seasons = get_player_seasons(
        session, player_id
    )  # list of all seasons a player played in
    player_info = get_latest_team_membership(
        session,
        player_id,
        year_to_show,
    )
    matches = get_player_match_data(session, player.name, year_to_show)

    # Prepare data for the plot
    match_data = prepare_match_data(matches, player.name)

    # Generate the Bokeh plot
    script, div = create_player_performance_graph(match_data)

    breadcrumbs = [
        {"name": "Home", "url": "/"},
        {
            "name": "Players Ranking",
            "url": url_for("ranking.show_ranking", year=[current_season]),
        },
        {"name": player.name, "url": None},
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
        bokeh_script=script,
        bokeh_div=div,
    )
