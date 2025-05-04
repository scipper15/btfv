from collections import defaultdict
from datetime import datetime
from typing import Any, DefaultDict
import uuid

from sqlalchemy import and_, case, desc, extract, func, or_
from sqlalchemy.orm import Session, aliased

from shared.database.models import (
    Match,
    MatchParticipant,
    Player,
    Season,
    Team,
    TeamMembership,
)


def get_last_match_date(
    session: Session, player_id: uuid.UUID, season_year: int | None
) -> datetime:
    """Date of the last match a player played."""
    # Base query selecting match dates and joining MatchParticipant
    query = (
        session.query(Match.date)
        .join(MatchParticipant, MatchParticipant.match_id == Match.id)
        .filter(MatchParticipant.player_id == player_id)
    )

    if season_year is not None:
        query = (
            query.join(Season, Match.season_id == Season.id)
            .filter(Season.season_year == season_year)
            .order_by(Match.date.desc())
            .limit(1)
        )
    else:
        query = query.order_by(Match.date.desc()).limit(1)

    return query.scalar()


def get_player_seasons(session: Session, player_id: uuid.UUID) -> list[Season]:
    """List of all seasons a player played in."""
    stmt = (
        session.query(Season)
        .join(Match, Match.season_id == Season.id)
        .join(MatchParticipant, MatchParticipant.match_id == Match.id)
        .filter(MatchParticipant.player_id == player_id)
        .distinct()  # Ensure seasons are distinct
        .order_by(Season.season_year.desc())
    )
    return stmt.all()


def get_seasons(session: Session) -> list[Season]:
    """Get a list of all seasons."""
    return session.query(Season).order_by(Season.season_year.desc()).all()


def get_most_recent_season(session: Session) -> int:
    """Get the most recent season in the database."""
    most_recent_season = session.query(func.max(Season.season_year)).scalar()
    return most_recent_season


def get_player_by_id(session: Session, player_id: uuid.UUID) -> Player | None:
    """Get a player by ID."""
    player = session.query(Player).filter_by(id=player_id).first()
    return player if player else None


def get_latest_player_ratings(
    session: Session, player_id: uuid.UUID, season_year: int | None
) -> Any | None:
    """Query to get the latest player stats.

    (mu_after_combined, sigma_after_combined, calculated mu_confident, and additional
    player information (name, category, national_id, international_id, image_file_name).

    If season_year is provided, filter by that season; otherwise, get the latest values.
    """
    # Base query with necessary joins
    query = (
        session.query(
            Player.id,
            Player.name,
            Player.category,
            Player.national_id,
            Player.international_id,
            Player.image_file_name,
            MatchParticipant.mu_after_combined,
            MatchParticipant.sigma_after_combined,
            (
                MatchParticipant.mu_after_combined
                - 3 * MatchParticipant.sigma_after_combined
            ).label("mu_confident"),
            Match.global_match_nr,
        )
        .join(MatchParticipant, MatchParticipant.player_id == Player.id)
        .join(Match, MatchParticipant.match_id == Match.id)
        .group_by(
            Player.id,
            MatchParticipant.mu_after_combined,
            MatchParticipant.sigma_after_combined,
            Match.global_match_nr,
        )
    )

    query = query.filter(Player.id == player_id)

    if season_year is not None:
        query = query.join(Season, Match.season_id == Season.id)
        query = query.filter(Season.season_year == season_year)

    query = query.order_by(Match.global_match_nr.desc())

    # Limit to the latest match
    result = query.first()

    if result:
        return result
    return None


def get_player_ranking(
    session: Session, season_year: int | None
) -> list[dict[str, str | float | None]]:
    """Retrieves a list of players ordered by their confident_mu_combined.

    If year

    Args:
        session (Session): The SQLAlchemy session object.
        season_year (Optional[int]): The season year to filter players by. If None,
                                     'All Time' ranking is fetched.
        eternal (bool): If True, includes all players irrespective of season. If False,
                        includes only players who participated in the specified season.

    Returns:
        List[Dict]: A list of dictionaries containing player ranking information.
    """
    player_rankings = []

    if not season_year:
        # ------------------------
        # Eternal (All Time) Ranking
        # ------------------------

        # Subquery to get the latest Season Year per player
        latest_season_subquery = (
            session.query(
                TeamMembership.player_id,
                func.max(Season.season_year).label("latest_season_year"),
            )
            .join(Season, TeamMembership.season_id == Season.id)
            .group_by(TeamMembership.player_id)
            .subquery()
        )

        # Main query for All Time Ranking
        query = (
            session.query(
                Player.image_file_name,
                Player.id.label("player_id"),
                Player.name.label("player_name"),
                (Player.current_mu_combined - 3 * Player.current_sigma_combined).label(
                    "confident_mu_combined"
                ),
                (Player.current_mu_singles - 3 * Player.current_sigma_singles).label(
                    "confident_mu_singles"
                ),
                (Player.current_mu_doubles - 3 * Player.current_sigma_doubles).label(
                    "confident_mu_doubles"
                ),
                Player.current_mu_combined,
                Player.current_sigma_combined,
                Player.current_mu_singles,
                Player.current_sigma_singles,
                Player.current_mu_doubles,
                Player.current_sigma_doubles,
                TeamMembership.team_id,
                Team.name.label("team_name"),
                func.max(Match.date).label("last_match_date"),
                func.count(MatchParticipant.match_id).label("total_matches"),
                func.sum(
                    case(
                        (
                            (Match.who_won == "home")
                            & (MatchParticipant.team_side == "home"),
                            1,
                        ),
                        (
                            (Match.who_won == "away")
                            & (MatchParticipant.team_side == "away"),
                            1,
                        ),
                        else_=0,
                    )
                ).label("matches_won"),
            )
            .select_from(Player)  # Ensure Player is the primary table
            .join(TeamMembership, TeamMembership.player_id == Player.id)
            .join(Season, TeamMembership.season_id == Season.id)
            .join(
                latest_season_subquery,
                and_(
                    TeamMembership.player_id == latest_season_subquery.c.player_id,
                    Season.season_year == latest_season_subquery.c.latest_season_year,
                ),
            )
            .join(Team, Team.id == TeamMembership.team_id)
            .outerjoin(MatchParticipant, MatchParticipant.player_id == Player.id)
            .outerjoin(Match, Match.id == MatchParticipant.match_id)
            .filter(~TeamMembership.is_borrowed)
            .group_by(
                Player.id,
                TeamMembership.team_id,
                Team.name,
                Player.name,
                Player.current_mu_combined,
                Player.current_sigma_combined,
                Player.current_mu_singles,
                Player.current_sigma_singles,
                Player.current_mu_doubles,
                Player.current_sigma_doubles,
            )
            .order_by(desc("confident_mu_combined"))
        )

        results = query.all()

        for row in results:
            win_percentage = (
                (row.matches_won / row.total_matches * 100)
                if row.total_matches > 0
                else 0.0
            )

            player_rankings.append(
                {
                    "player_id": str(row.player_id),
                    "player_name": row.player_name,
                    "image_file_name": row.image_file_name,
                    "confident_mu_combined": row.confident_mu_combined,
                    "confident_mu_singles": row.confident_mu_singles
                    if row.confident_mu_singles
                    else 0.0,
                    "confident_mu_doubles": row.confident_mu_doubles
                    if row.confident_mu_doubles
                    else 0.0,
                    "current_mu_combined": row.current_mu_combined,
                    "current_sigma_combined": row.current_sigma_combined,
                    "current_mu_singles": row.current_mu_singles,
                    "current_sigma_singles": row.current_sigma_singles,
                    "current_mu_doubles": row.current_mu_doubles,
                    "current_sigma_doubles": row.current_sigma_doubles,
                    "team_id": str(row.team_id),
                    "team_name": row.team_name,
                    "last_match_date": row.last_match_date
                    if row.last_match_date
                    else None,
                    "total_matches": row.total_matches,
                    "matches_won": int(row.matches_won),
                    "win_percentage": win_percentage,
                }
            )

    else:
        # find the latest global_match_nr for singles matches in the selected season
        latest_singles_match_subquery = (
            session.query(
                MatchParticipant.player_id,
                func.max(Match.global_match_nr).label("latest_global_match_nr"),
            )
            .join(Match, Match.id == MatchParticipant.match_id)
            .join(Season, Match.season_id == Season.id)
            .filter(Season.season_year == season_year, Match.match_type == "single")
            .group_by(MatchParticipant.player_id)
            .subquery()
        )

        # find the latest global_match_nr for doubles matches in the selected season
        latest_doubles_match_subquery = (
            session.query(
                MatchParticipant.player_id,
                func.max(Match.global_match_nr).label("latest_global_match_nr_doubles"),
            )
            .join(Match, Match.id == MatchParticipant.match_id)
            .join(Season, Match.season_id == Season.id)
            .filter(Season.season_year == season_year, Match.match_type == "double")
            .group_by(MatchParticipant.player_id)
            .subquery()
        )

        # Subquery to count all matches up to the player's last match in the season
        cumulative_matches_subquery = (
            session.query(
                MatchParticipant.player_id,
                func.count(MatchParticipant.match_id).label("total_matches"),
                func.sum(
                    case(
                        (
                            (Match.who_won == "home")
                            & (MatchParticipant.team_side == "home"),
                            1,
                        ),
                        (
                            (Match.who_won == "away")
                            & (MatchParticipant.team_side == "away"),
                            1,
                        ),
                        else_=0,
                    )
                ).label("matches_won"),
            )
            .join(Match, Match.id == MatchParticipant.match_id)
            .join(Season, Match.season_id == Season.id)
            .filter(
                Season.season_year <= season_year
            )  # Matches until the selected season
            .group_by(MatchParticipant.player_id)
            .subquery()
        )

        # Main query to fetch player rankings with both singles and doubles stats
        query = (
            session.query(
                Player.image_file_name,
                Player.id.label("player_id"),
                Player.name.label("player_name"),
                (
                    MatchParticipant.mu_after_combined
                    - 3 * MatchParticipant.sigma_after_combined
                ).label("confident_mu_combined"),
                (
                    MatchParticipant.mu_after_singles
                    - 3 * MatchParticipant.sigma_after_singles
                ).label("confident_mu_singles"),
                (
                    MatchParticipant.mu_after_doubles
                    - 3 * MatchParticipant.sigma_after_doubles
                ).label("confident_mu_doubles"),
                MatchParticipant.mu_after_combined.label("current_mu_combined"),
                MatchParticipant.sigma_after_combined.label("current_sigma_combined"),
                MatchParticipant.mu_after_singles.label("current_mu_singles"),
                MatchParticipant.sigma_after_singles.label("current_sigma_singles"),
                MatchParticipant.mu_after_doubles.label("current_mu_doubles"),
                MatchParticipant.sigma_after_doubles.label("current_sigma_doubles"),
                TeamMembership.team_id,
                Team.name.label("team_name"),
                func.max(Match.date).label("last_match_date"),
                cumulative_matches_subquery.c.total_matches.label("total_matches"),
                cumulative_matches_subquery.c.matches_won.label("matches_won"),
                func.max(MatchParticipant.mu_after_combined).label("last_mu_combined"),
                func.max(MatchParticipant.sigma_after_combined).label(
                    "last_sigma_combined"
                ),
                func.max(MatchParticipant.mu_after_singles).label("last_mu_singles"),
                func.max(MatchParticipant.sigma_after_singles).label(
                    "last_sigma_singles"
                ),
                func.max(MatchParticipant.mu_after_doubles).label("last_mu_doubles"),
                func.max(MatchParticipant.sigma_after_doubles).label(
                    "last_sigma_doubles"
                ),
            )
            .join(TeamMembership, TeamMembership.player_id == Player.id)
            .join(Team, Team.id == TeamMembership.team_id)
            .join(MatchParticipant, MatchParticipant.player_id == Player.id)
            .join(Match, Match.id == MatchParticipant.match_id)
            .join(
                latest_singles_match_subquery,
                and_(
                    MatchParticipant.player_id
                    == latest_singles_match_subquery.c.player_id,
                    Match.global_match_nr
                    == latest_singles_match_subquery.c.latest_global_match_nr,
                ),
            )
            .join(
                latest_doubles_match_subquery,
                and_(
                    MatchParticipant.player_id
                    == latest_doubles_match_subquery.c.player_id,
                    Match.global_match_nr
                    == latest_doubles_match_subquery.c.latest_global_match_nr_doubles,
                ),
                isouter=True,  # Optional join: a player might not have doubles matches
            )
            .join(
                cumulative_matches_subquery,
                cumulative_matches_subquery.c.player_id == Player.id,
            )
            .filter(
                ~TeamMembership.is_borrowed, TeamMembership.season_id == Match.season_id
            )
            .group_by(
                Player.id,
                TeamMembership.team_id,
                Team.name,
                Player.name,
                MatchParticipant.mu_after_combined,
                MatchParticipant.sigma_after_combined,
                MatchParticipant.mu_after_singles,
                MatchParticipant.sigma_after_singles,
                MatchParticipant.mu_after_doubles,
                MatchParticipant.sigma_after_doubles,
                cumulative_matches_subquery.c.total_matches,
                cumulative_matches_subquery.c.matches_won,
            )
            .order_by(desc("confident_mu_combined"))
        )

        results = query.all()

        # Process and return the results
        player_rankings = []
        for row in results:
            win_percentage = (
                (row.matches_won / row.total_matches * 100)
                if row.total_matches > 0
                else 0.0
            )

            player_rankings.append(
                {
                    "player_id": str(row.player_id),
                    "player_name": row.player_name,
                    "image_file_name": row.image_file_name,
                    "confident_mu_combined": row.confident_mu_combined,
                    "confident_mu_singles": row.confident_mu_singles
                    if row.confident_mu_singles
                    else 0.0,
                    "confident_mu_doubles": row.confident_mu_doubles
                    if row.confident_mu_doubles
                    else 0.0,
                    "current_mu_combined": row.current_mu_combined,
                    "current_sigma_combined": row.current_sigma_combined,
                    "current_mu_singles": row.current_mu_singles or 0.0,
                    "current_sigma_singles": row.current_sigma_singles or 0.0,
                    "current_mu_doubles": row.current_mu_doubles or 0.0,
                    "current_sigma_doubles": row.current_sigma_doubles or 0.0,
                    "team_id": str(row.team_id),
                    "team_name": row.team_name,
                    "last_match_date": row.last_match_date
                    if row.last_match_date
                    else None,
                    "total_matches": row.total_matches,
                    "matches_won": int(row.matches_won),
                    "win_percentage": win_percentage,
                }
            )

    return player_rankings


def get_player_match_data_with_gain(
    session: Session, player_name: str, season_year: int | None
) -> list[dict[str, Any]]:
    """Get all match data for a player, including mu_gain per matchday.

    Output is a list of dictionaries, ready for JSON serialization.
    """
    rows = get_player_match_data(session, player_name, season_year)

    matches: list[dict[str, Any]] = [row._asdict() for row in rows]

    # group by match_day_nr
    by_day: DefaultDict[int, list[dict[str, Any]]] = defaultdict(list)
    for m in matches:
        by_day[m["match_day_nr"]].append(m)

    return matches


def get_player_match_data(
    session: Session, player_name: str, season_year: int | None
) -> Any:
    """Get all the match data of a player.

    If season_year isn't provided fetch all matches.
    """
    # Aliases for home and away teams
    HomeTeam = aliased(Team)
    AwayTeam = aliased(Team)

    # Aliases for players, teammates, and opponents
    HomePlayer = aliased(MatchParticipant)
    AwayPlayer = aliased(MatchParticipant)
    HomeTeammate = aliased(MatchParticipant)
    AwayTeammate = aliased(MatchParticipant)
    HomePlayerDetail = aliased(Player)
    AwayPlayerDetail = aliased(Player)
    HomeTeammateDetail = aliased(Player)
    AwayTeammateDetail = aliased(Player)

    query = (
        session.query(
            Match.global_match_nr,
            Match.date,
            Match.match_day_nr,
            Match.match_nr,
            Match.sets_home,
            Match.sets_away,
            Match.who_won,
            Match.match_type,
            Match.BTFV_from_id,
            # Home team details
            HomeTeam.name.label("home_team_name"),
            HomeTeam.id.label("home_team_id"),
            HomePlayerDetail.name.label("home_player_name"),
            HomePlayerDetail.id.label("home_player_id"),
            HomePlayerDetail.image_file_name.label(
                "home_player_image"
            ),  # Home player image
            HomePlayer.mu_before_combined.label("home_mu_before"),
            HomePlayer.sigma_before_combined.label("home_sigma_before"),
            HomePlayer.mu_after_combined.label("home_mu_after"),
            HomePlayer.sigma_after_combined.label("home_sigma_after"),
            HomeTeammateDetail.name.label("home_teammate_name"),
            HomeTeammateDetail.id.label("home_teammate_id"),
            HomeTeammateDetail.image_file_name.label(
                "home_teammate_image"
            ),  # Home teammate image
            HomeTeammate.mu_before_combined.label("home_teammate_mu_before"),
            HomeTeammate.sigma_before_combined.label("home_teammate_sigma_before"),
            HomeTeammate.mu_after_combined.label("home_teammate_mu_after"),
            HomeTeammate.sigma_after_combined.label("home_teammate_sigma_after"),
            # Confident values for home team
            (
                HomePlayer.mu_before_combined - 3 * HomePlayer.sigma_before_combined
            ).label("confident_home_mu_before"),
            (
                HomeTeammate.mu_before_combined - 3 * HomeTeammate.sigma_before_combined
            ).label("confident_home_teammate_mu_before"),
            (HomePlayer.mu_after_combined - 3 * HomePlayer.sigma_after_combined).label(
                "confident_home_mu_after"
            ),
            (
                HomeTeammate.mu_after_combined - 3 * HomeTeammate.sigma_after_combined
            ).label("confident_home_teammate_mu_after"),
            # Away team details
            AwayTeam.name.label("away_team_name"),
            AwayTeam.id.label("away_team_id"),
            AwayPlayerDetail.name.label("away_player_name"),
            AwayPlayerDetail.id.label("away_player_id"),
            AwayPlayerDetail.image_file_name.label(
                "away_player_image"
            ),  # Away player image
            AwayPlayer.mu_before_combined.label("away_mu_before"),
            AwayPlayer.sigma_before_combined.label("away_sigma_before"),
            AwayPlayer.mu_after_combined.label("away_mu_after"),
            AwayPlayer.sigma_after_combined.label("away_sigma_after"),
            AwayTeammateDetail.name.label("away_teammate_name"),
            AwayTeammateDetail.id.label("away_teammate_id"),
            AwayTeammateDetail.image_file_name.label(
                "away_teammate_image"
            ),  # Away teammate image
            AwayTeammate.mu_before_combined.label("away_teammate_mu_before"),
            AwayTeammate.sigma_before_combined.label("away_teammate_sigma_before"),
            AwayTeammate.mu_after_combined.label("away_teammate_mu_after"),
            AwayTeammate.sigma_after_combined.label("away_teammate_sigma_after"),
            # Confident values for away team
            (
                AwayPlayer.mu_before_combined - 3 * AwayPlayer.sigma_before_combined
            ).label("confident_away_mu_before"),
            (
                AwayTeammate.mu_before_combined - 3 * AwayTeammate.sigma_before_combined
            ).label("confident_away_teammate_mu_before"),
            (AwayPlayer.mu_after_combined - 3 * AwayPlayer.sigma_after_combined).label(
                "confident_away_mu_after"
            ),
            (
                AwayTeammate.mu_after_combined - 3 * AwayTeammate.sigma_after_combined
            ).label("confident_away_teammate_mu_after"),
        )
        # Explicitly join home and away players based on team_side
        .join(
            HomePlayer,
            and_(HomePlayer.match_id == Match.id, HomePlayer.team_side == "home"),
        )
        .join(
            AwayPlayer,
            and_(AwayPlayer.match_id == Match.id, AwayPlayer.team_side == "away"),
        )
        .join(HomePlayerDetail, HomePlayerDetail.id == HomePlayer.player_id)
        .join(AwayPlayerDetail, AwayPlayerDetail.id == AwayPlayer.player_id)
        # Left join for teammates in doubles (if applicable)
        .outerjoin(
            HomeTeammate,
            and_(
                HomeTeammate.match_id == Match.id,
                HomeTeammate.team_side == "home",
                HomeTeammate.player_id != HomePlayer.player_id,
            ),
        )
        .outerjoin(HomeTeammateDetail, HomeTeammateDetail.id == HomeTeammate.player_id)
        .outerjoin(
            AwayTeammate,
            and_(
                AwayTeammate.match_id == Match.id,
                AwayTeammate.team_side == "away",
                AwayTeammate.player_id != AwayPlayer.player_id,
            ),
        )
        .outerjoin(AwayTeammateDetail, AwayTeammateDetail.id == AwayTeammate.player_id)
        .join(HomeTeam, HomeTeam.id == Match.home_team_id)
        .join(AwayTeam, AwayTeam.id == Match.away_team_id)
        .distinct(Match.global_match_nr)
        .filter(
            or_(
                AwayPlayerDetail.name == player_name,
                HomePlayerDetail.name == player_name,
            )
        )
        .order_by(Match.global_match_nr.desc())
    )

    # Filter by year if a specific year is provided, otherwise return all-time
    if season_year is not None:
        query = query.filter(extract("year", Match.date) == season_year)

    # Order the matches by global match number in descending order
    match_data = query.order_by(Match.global_match_nr.desc()).all()

    return match_data
