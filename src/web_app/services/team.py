from typing import Any
from uuid import UUID

from sqlalchemy import Numeric, Row, and_, case, cast, func
from sqlalchemy.orm import Session

from shared.database.models import (
    Association,
    Division,
    DivisionName,
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


def get_latest_team_membership(
    session: Session, player_id: str, season_year: int | None
) -> Row[tuple[UUID, UUID, str, DivisionName, str, UUID, int, str]] | None:
    """Get logo, team, and division data for a player in a particular year.

    Returns the latest team data if no season_year is provided.
    """
    # Subquery to get the latest team membership (max season year) for the player
    latest_team_membership_subquery = (
        session.query(
            TeamMembership.player_id,
            func.max(Season.season_year).label("latest_season_year"),
        )
        .join(Season, TeamMembership.season_id == Season.id)
        .filter(TeamMembership.player_id == player_id)
        .group_by(TeamMembership.player_id)
        .subquery()
    )

    # Main query to get the details, joining with the subquery
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
        .join(Season, TeamMembership.season_id == Season.id)
        .join(Association, Team.association_id == Association.id)
    )

    if season_year:
        # If specific season_year is provided, filter by that year
        query = query.filter(
            and_(
                Player.id == player_id,
                Season.season_year == season_year,
            )
        )
    else:
        # If no season_year is provided, use the latest season year from the subquery
        query = query.join(
            latest_team_membership_subquery,
            and_(
                Player.id == latest_team_membership_subquery.c.player_id,
                Season.season_year
                == latest_team_membership_subquery.c.latest_season_year,
            ),
        )

    return query.first()
