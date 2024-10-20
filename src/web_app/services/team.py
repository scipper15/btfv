from typing import Any
import uuid
from uuid import UUID

from sqlalchemy import Numeric, Row, and_, case, cast, func
from sqlalchemy.orm import Session, aliased

from shared.database.models import (
    Association,
    Division,
    DivisionName,
    Match,
    MatchParticipant,
    Player,
    Season,
    Team,
    TeamMembership,
)


def get_all_team_members_with_stats(session: Session, team_id: UUID) -> dict[Any, Any]:
    # Subquery to calculate win percentage for each player
    win_percentage_subquery = (
        session.query(
            MatchParticipant.player_id,
            (
                func.sum(
                    case(
                        (
                            MatchParticipant.mu_after_combined
                            > MatchParticipant.mu_before_combined,
                            1,
                        ),
                        else_=0,
                    )
                )
                / cast(func.count(MatchParticipant.match_id), Numeric)
                * 100
            ).label("win_percentage"),
        )
        .group_by(MatchParticipant.player_id)
        .subquery()
    )

    # Query team members and join with their stats
    team_members = (
        session.query(
            Player,
            win_percentage_subquery.c.win_percentage,
            Team.name.label("team_name"),
            Division.name.label("division_name"),
            Division.region.label("region"),
        )
        .join(TeamMembership, TeamMembership.player_id == Player.id)
        .join(Team, TeamMembership.team_id == Team.id)
        .join(Division, Team.division_id == Division.id)
        .outerjoin(
            win_percentage_subquery, win_percentage_subquery.c.player_id == Player.id
        )
        .filter(TeamMembership.team_id == team_id)
        .order_by(Player.current_mu_combined.desc())  # Sorting by combined rating
        .all()
    )

    # Return the team and player info
    return {
        "team_name": team_members[0].team_name if team_members else None,
        "division_name": team_members[0].division_name if team_members else None,
        "region": team_members[0].region if team_members else None,
        "team_members": [
            {
                "name": member.Player.name,
                "category": member.Player.category.value
                if member.Player.category
                else "Unbekannt",
                "current_mu_combined": member.Player.current_mu_combined,
                "current_sigma_combined": member.Player.current_sigma_combined,
                "current_mu_singles": member.Player.current_mu_singles,
                "current_sigma_singles": member.Player.current_sigma_singles,
                "current_mu_doubles": member.Player.current_mu_doubles,
                "current_sigma_doubles": member.Player.current_sigma_doubles,
                "win_percentage": member.win_percentage
                or 0.0,  # Default to 0 if no matches
                "national_id": member.Player.national_id,
                "international_id": member.Player.international_id,
                "DTFB_from_id": member.Player.DTFB_from_id,
                "image_file_name": member.Player.image_file_name,
            }
            for member in team_members
        ],
    }


def get_team_details(session: Session, team_id: uuid.UUID) -> Any:
    """Get all players respective player information of a team."""
    # Aliases for self-joins or complex relationships
    PlayerAlias = aliased(Player)
    MatchAlias = aliased(Match)
    MatchParticipantAlias = aliased(MatchParticipant)
    DivisionAlias = aliased(Division)
    SeasonAlias = aliased(Season)

    # Subquery to get the latest season the team played in
    latest_season_subquery = (
        session.query(TeamMembership.season_id)
        .join(Team, TeamMembership.team_id == Team.id)
        .join(SeasonAlias, TeamMembership.season_id == SeasonAlias.id)
        .filter(Team.id == team_id)
        .order_by(SeasonAlias.season_year.desc())
        .limit(1)
        .subquery()
    )

    # Subquery to get the last match each player played
    last_match_subquery = (
        session.query(
            MatchParticipantAlias.player_id,
            func.max(MatchAlias.date).label("last_match_date"),
        )
        .join(MatchAlias, MatchParticipantAlias.match_id == MatchAlias.id)
        .group_by(MatchParticipantAlias.player_id)
        .subquery()
    )

    # Main query to get players, team info, division, season, and last match details
    query = (
        session.query(
            PlayerAlias.name,
            PlayerAlias.image_file_name,
            PlayerAlias.current_mu_combined,
            PlayerAlias.current_sigma_combined,
            PlayerAlias.current_mu_singles,
            PlayerAlias.current_sigma_singles,
            PlayerAlias.current_mu_doubles,
            PlayerAlias.current_sigma_doubles,
            Team.name.label("team_name"),
            DivisionAlias.name.label("division_name"),
            SeasonAlias.season_year.label("season_year"),
            last_match_subquery.c.last_match_date,
            # Calculate latest mu_after_doubles - 3 * sigma_after_doubles
            (
                MatchParticipantAlias.mu_after_doubles
                - 3 * MatchParticipantAlias.sigma_after_doubles
            ).label("doubles_performance"),
        )
        .join(TeamMembership, PlayerAlias.id == TeamMembership.player_id)
        .join(Team, TeamMembership.team_id == Team.id)
        .join(DivisionAlias, Team.division_id == DivisionAlias.id)
        .join(SeasonAlias, TeamMembership.season_id == SeasonAlias.id)
        .outerjoin(
            MatchParticipantAlias, MatchParticipantAlias.player_id == PlayerAlias.id
        )
        .outerjoin(
            last_match_subquery, last_match_subquery.c.player_id == PlayerAlias.id
        )
        .filter(Team.id == team_id)
        .filter(TeamMembership.season_id == latest_season_subquery)
        .group_by(
            PlayerAlias.id,
            Team.id,
            DivisionAlias.id,
            SeasonAlias.id,
            last_match_subquery.c.last_match_date,
            MatchParticipantAlias.mu_after_doubles,
            MatchParticipantAlias.sigma_after_doubles,
        )
        .order_by(last_match_subquery.c.last_match_date.desc())
    ).all()

    return query


def get_latest_team_membership(
    session: Session, player_id: str, season_year: int | None
) -> Row[tuple[UUID, UUID, str, DivisionName, str, UUID, int, str]] | None:
    """Get logo, team and division data for a player in a particular year.

    Returns the latest team data if no season_year is provided.
    """
    query = (
        session.query(
            Player.id.label("player_id"),
            TeamMembership.id.label("team_id"),
            Team.name.label("team_name"),
            Division.name.label("division_name"),
            Division.region.label("region"),
            TeamMembership.season_id.label("season_id"),
            Season.season_year.label("season_year"),
            Association.logo_file_name.label("logo_file_name"),
        )
        .join(TeamMembership, Player.id == TeamMembership.player_id)
        .join(Team, TeamMembership.team_id == Team.id)
        .join(Division, Team.division_id == Division.id)
        .join(Season, Division.season_id == Season.id)
        .join(Association, Team.association_id == Association.id)
    )
    if season_year:
        query = query.where(
            and_(
                Player.id == player_id,
                Season.season_year == season_year,
            )
        )
    else:
        query = query.where(Player.id == player_id)

    return query.first()
