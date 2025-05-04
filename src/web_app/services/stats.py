from typing import Any
import uuid

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import aliased

from shared.database.models import (
    Division,
    Match,
    MatchParticipant,
    Player,
    Season,
    Team,
    TeamMembership,
)

# Ausdruck für confident μ
conf_mu = Player.current_mu_combined - 3 * Player.current_sigma_combined

# Aggregats-Labels
avg_conf_mu = func.avg(conf_mu).label("avg_conf_mu")
median_conf_mu = (
    func.percentile_cont(0.5).within_group(conf_mu.asc()).label("median_conf_mu")
)
player_count = func.count(func.distinct(TeamMembership.player_id)).label("player_count")


def stats_per_season_all(session: Any) -> Any:
    """Liefert für jede Saison das Tupel.

    (season_year, player_count, avg_conf_mu, median_conf_mu).
    Dabei wird pro Spieler nur sein CONFIDENT_MU aus dem letzten
    Spiel der jeweiligen Saison benutzt.
    """
    mp = MatchParticipant
    m = Match
    s = Season

    # 1) Ausdruck für confident_mu im Teilnehmer-Datensatz
    conf_mu = mp.mu_after_combined - 3 * mp.sigma_after_combined

    # 2) Subquery: Nummeriere je (Saison, Spieler) die Matches absteigend nach Datum
    numbered = (
        select(
            s.season_year.label("year"),
            mp.player_id.label("player_id"),
            conf_mu.label("conf_mu"),
            func.row_number()
            .over(partition_by=(s.season_year, mp.player_id), order_by=m.date.desc())
            .label("rn"),
        )
        .join(m, mp.match_id == m.id)
        .join(s, m.season_id == s.id)
        .subquery()
    )

    # 3) Hauptquery: Nur Zeilen mit rn=1 (letztes Match pro Spieler/Saison)
    stmt = (
        select(
            numbered.c.year,
            func.count().label("player_count"),
            func.avg(numbered.c.conf_mu).label("avg_conf_mu"),
            func.percentile_cont(0.5)
            .within_group(numbered.c.conf_mu.asc())
            .label("median_conf_mu"),
            func.percentile_cont(0.9)
            .within_group(numbered.c.conf_mu.asc())
            .label("p90_conf_mu"),
        )
        .where(numbered.c.rn == 1)
        .group_by(numbered.c.year)
        .order_by(numbered.c.year)
    )

    return session.execute(stmt).all()


def stats_per_season_by_division(
    session: Any, year: int | None = None, division: str | None = None
) -> Any:
    """Liefert für jede Saison und jede Division+Region das Tupel.

    (year, division_name, region, player_count, avg_conf_mu, median_conf_mu).
    """
    # confident μ
    conf_mu = (
        MatchParticipant.mu_after_combined - 3 * MatchParticipant.sigma_after_combined
    )

    # ermittle das korrekte Team je Teilnehmer
    team_id_expr = case(
        (MatchParticipant.team_side == "home", Match.home_team_id),
        else_=Match.away_team_id,
    )

    # Window-Subquery: letzte Partie pro Saison/Division/Spieler
    numbered = (
        session.query(
            Season.season_year.label("year"),
            Division.name.label("division_name"),
            Division.region.label("region"),
            MatchParticipant.player_id.label("player_id"),
            conf_mu.label("conf_mu"),
            func.row_number()
            .over(
                partition_by=[
                    Season.season_year,
                    Division.id,
                    MatchParticipant.player_id,
                ],
                order_by=Match.date.desc(),
            )
            .label("rn"),
        )
        .join(Match, MatchParticipant.match_id == Match.id)
        .join(Season, Match.season_id == Season.id)
        .join(Team, team_id_expr == Team.id)
        .join(Division, Team.division_id == Division.id)
        .subquery()
    )

    # Haupt-Query: nur rn=1, dann Gruppen-Aggregation
    q = (
        session.query(
            numbered.c.year,
            numbered.c.division_name,
            numbered.c.region,
            func.count().label("player_count"),
            func.avg(numbered.c.conf_mu).label("avg_conf_mu"),
            func.percentile_cont(0.5)
            .within_group(numbered.c.conf_mu.asc())
            .label("median_conf_mu"),
            func.percentile_cont(0.9)
            .within_group(numbered.c.conf_mu.asc())
            .label("p90_conf_mu"),
        )
        .filter(numbered.c.rn == 1)
        .group_by(
            numbered.c.year,
            numbered.c.division_name,
            numbered.c.region,
        )
        .order_by(
            numbered.c.year,
            numbered.c.division_name,
            numbered.c.region,
        )
    )

    if year is not None:
        q = q.filter(numbered.c.year == year)
    if division:
        q = q.filter(numbered.c.division_name == division)
    return q.all()


def stats_per_season_by_team(session: Any) -> Any:
    """Liefert pro Saison und pro Team.

    (year, team_id, team_name, player_count, avg_conf_mu, median_conf_mu, p90_conf_mu)
    """
    conf_mu = (
        MatchParticipant.mu_after_combined - 3 * MatchParticipant.sigma_after_combined
    )

    team_id_expr = case(
        (MatchParticipant.team_side == "home", Match.home_team_id),
        else_=Match.away_team_id,
    )

    numbered = (
        session.query(
            Season.season_year.label("year"),
            Team.id.label("team_id"),
            Team.name.label("team_name"),
            Division.name.label("division_name"),
            Division.region.label("region"),
            MatchParticipant.player_id.label("player_id"),
            conf_mu.label("conf_mu"),
            func.row_number()
            .over(
                partition_by=[Season.season_year, Team.id, MatchParticipant.player_id],
                order_by=Match.date.desc(),
            )
            .label("rn"),
        )
        .join(Match, MatchParticipant.match_id == Match.id)
        .join(Season, Match.season_id == Season.id)
        .join(Team, team_id_expr == Team.id)
        .join(Division, Team.division_id == Division.id)
        .subquery()
    )

    q = (
        session.query(
            numbered.c.year,
            numbered.c.team_id,
            numbered.c.team_name,
            numbered.c.division_name,
            numbered.c.region,
            func.count().label("player_count"),
            func.avg(numbered.c.conf_mu).label("avg_conf_mu"),
            func.percentile_cont(0.5)
            .within_group(numbered.c.conf_mu.asc())
            .label("median_conf_mu"),
            func.percentile_cont(0.9)
            .within_group(numbered.c.conf_mu.asc())
            .label("p90_conf_mu"),
        )
        .filter(numbered.c.rn == 1)
        .group_by(
            numbered.c.year,
            numbered.c.team_id,
            numbered.c.team_name,
            numbered.c.division_name,
            numbered.c.region,
        )
        .order_by(numbered.c.year, numbered.c.team_name)
    )
    return q.all()


def get_team_details(session: Any, team_id: uuid.UUID, season_id: uuid.UUID) -> Any:
    """Liefert pro Spieler in genau diesem Team + dieser Saison.

    - name, image_file_name
    - aktuelles mu/sigma
    - datum des letzten Matches in dieser Saison für dieses Team
    - performance = mu_after - 3*sigma_after im letzten Match
    """
    P = aliased(Player)
    TM = aliased(TeamMembership)
    T = aliased(Team)
    D = aliased(Division)
    S = aliased(Season)
    M = aliased(Match)
    MP = aliased(MatchParticipant)

    # CASE um zu prüfen, wo der Teilnehmer gespielt hat:
    team_id_expr = case(
        (MP.team_side == "home", M.home_team_id),
        else_=M.away_team_id,
    )

    # 1) Subquery: höchste global_match_nr pro Spieler in dieser Saison+Team
    last_match_sq = (
        select(
            MP.player_id.label("player_id"),
            func.max(M.global_match_nr).label("last_nr"),
        )
        .join(M, MP.match_id == M.id)
        .where(
            M.season_id == season_id,
            team_id_expr == team_id,
        )
        .group_by(MP.player_id)
        .subquery()
    )

    # 2) Hauptquery:
    q = (
        session.query(
            P.id.label("player_id"),
            P.name,
            P.image_file_name,
            P.current_mu_combined,
            P.current_sigma_combined,
            P.current_mu_singles,
            P.current_sigma_singles,
            P.current_mu_doubles,
            P.current_sigma_doubles,
            S.season_year.label("season_year"),
            M.date.label("last_match_date"),
            (MP.mu_after_combined - 3 * MP.sigma_after_combined).label(
                "mu_confident_combined"
            ),
            (MP.mu_after_doubles - 3 * MP.sigma_after_doubles).label(
                "mu_confident_doubles"
            ),
            (MP.mu_after_singles - 3 * MP.sigma_after_singles).label(
                "mu_confident_singles"
            ),
        )
        .select_from(P)
        # Nur Spieler, die in diesem Team+Saison sind
        .join(
            TM,
            and_(
                P.id == TM.player_id,
                TM.team_id == team_id,
                TM.season_id == season_id,
            ),
        )
        # Subquery mit letzter global_match_nr ankleben
        .join(last_match_sq, last_match_sq.c.player_id == P.id)
        # Jetzt erst das Match-Objekt für diese global_match_nr
        .join(M, M.global_match_nr == last_match_sq.c.last_nr)
        # Und danach den passenden MatchParticipant-Datensatz
        .join(
            MP,
            and_(
                MP.player_id == P.id,
                MP.match_id == M.id,
            ),
        )
        .join(T, TM.team_id == T.id)
        .join(D, T.division_id == D.id)
        .join(S, TM.season_id == S.id)
        .order_by(MP.mu_after_combined - 3 * MP.sigma_after_combined.desc())
    )

    return q.all()
