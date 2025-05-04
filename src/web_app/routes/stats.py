from datetime import datetime
import uuid

from flask import Blueprint, g, render_template, request

from shared.database.models import DivisionName, Season, Team, TeamMembership
from web_app.services.stats import (
    get_team_details,
    stats_per_season_all,
    stats_per_season_by_division,
)

stats_bp = Blueprint("stats", __name__, template_folder="../templates")


@stats_bp.route("/season_stats")
def season_stats() -> str:
    session = g.db_session

    season_stats = stats_per_season_all(session)

    breadcrumbs = [
        {"name": "Home", "url": "/"},
        {"name": "Season Stats"},
    ]

    return render_template(
        "season_stats.html",
        season_stats=season_stats,
        active_tab="season",
        breadcrumbs=breadcrumbs,
    )


@stats_bp.route("/division_stats")
def division_stats() -> str:
    session = g.db_session

    year = request.args.get("year", type=int)
    division = request.args.get("division", type=str)

    division_stats = stats_per_season_by_division(session, year=year, division=division)

    years = [
        y[0]
        for y in session.query(Season.season_year)
        .distinct()
        .order_by(Season.season_year)
    ]
    # Division-Labels aus Deinem Enum
    divisions = [d.value for d in DivisionName]

    breadcrumbs = [
        {"name": "Home", "url": "/"},
        {"name": "Division Stats"},
    ]

    return render_template(
        "division_stats.html",
        division_stats=division_stats,
        years=years,
        divisions=divisions,
        selected_year=year,
        selected_division=division,
        active_tab="division",
        breadcrumbs=breadcrumbs,
    )


@stats_bp.route("/team_stats")
def team_stats() -> str:
    session = g.db_session

    seasons = (
        session.query(Season.id, Season.season_year).order_by(Season.season_year).all()
    )
    breadcrumbs = [
        {"name": "Home", "url": "/"},
        {"name": "Team Stats"},
    ]
    return render_template(
        "team_stats.html",
        seasons=seasons,
        active_tab="team",
        breadcrumbs=breadcrumbs,
    )


@stats_bp.route("/team_stats/teams")
def team_stats_teams() -> str:
    session = g.db_session
    season_id = request.args.get("season_id", type=uuid.UUID)
    if not season_id:
        return "<option value=''> select season first </option>"
    # Teams mit Mitgliedschaft in dieser Saison
    teams = (
        session.query(Team.id, Team.name)
        .join(TeamMembership, Team.id == TeamMembership.team_id)
        .filter(TeamMembership.season_id == season_id)
        .distinct()
        .order_by(Team.name)
        .all()
    )
    breadcrumbs = [
        {"name": "Home", "url": "/"},
        {"name": "Team Stats"},
    ]
    return render_template(
        "partials/_team_select_options.html",
        teams=teams,
        breadcrumbs=breadcrumbs,
    )


@stats_bp.route("/team_stats/details")
def team_stats_details() -> str:  # noqa: C901
    session = g.db_session
    season_id = request.args.get("season_id", type=uuid.UUID)
    team_id = request.args.get("team_id", type=uuid.UUID)
    if not season_id or not team_id:
        return "<div class='p-4 text-gray-600'>Please select season & team.</div>"
    # 1) Daten holen
    rows = get_team_details(session, team_id, season_id)

    # 2) Aufbereiten
    current_year = datetime.now().year
    players = []
    for row in rows:
        data = dict(row._mapping)  # alle Spalten als Dict
        # confident μ für Singles & Doubles
        mu_s = data["current_mu_singles"] - 3 * data["current_sigma_singles"]
        mu_d = data["current_mu_doubles"] - 3 * data["current_sigma_doubles"]
        # Spezialist basierend auf größerem μ
        specialist = "singles specialist" if mu_s > mu_d else "doubles specialist"
        # Monster-Placeholder, setzen wir später
        data.update(
            {
                "mu_conf_singles": round(mu_s, 2),
                "mu_conf_doubles": round(mu_d, 2),
                "specialist": specialist,
                "is_singles_monster": False,
                "is_doubles_monster": False,
            }
        )
        players.append(data)

    # 3) Monster ermitteln (Maxima)
    if players:
        max_mu_s = max(players, key=lambda p: p["mu_conf_singles"])["mu_conf_singles"]
        max_mu_d = max(players, key=lambda p: p["mu_conf_doubles"])["mu_conf_doubles"]
        for p in players:
            if p["mu_conf_singles"] == max_mu_s:
                p["is_singles_monster"] = True
            if p["mu_conf_doubles"] == max_mu_d:
                p["is_doubles_monster"] = True

    # 4) Specialist ermitteln: Diff = mu_singles - mu_doubles
    for p in players:
        p["diff"] = p["mu_conf_singles"] - p["mu_conf_doubles"]
        # reset specialist flags
        p["is_singles_specialist"] = False
        p["is_doubles_specialist"] = False

    if players:
        # die größte positive Differenz → singles specialist
        max_diff = max(players, key=lambda x: x["diff"])["diff"]
        # die kleinste (negativste) Differenz → doubles specialist
        min_diff = min(players, key=lambda x: x["diff"])["diff"]

        for p in players:
            if p["diff"] == max_diff:
                p["is_singles_specialist"] = True
            if p["diff"] == min_diff:
                p["is_doubles_specialist"] = True

    return render_template(
        "partials/_team_stats_details.html",
        players=players,
        current_year=current_year,
    )
