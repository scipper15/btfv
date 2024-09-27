from logging import Logger
from typing import Any, Union, cast

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
import trueskill  # type: ignore

from scraper.extractor import Extractor
from scraper.skill_calc import SkillCalc
from shared.config.settings import Settings
from shared.database.database import Database
from shared.database.models import (
    Association,
    Division,
    DivisionName,
    Match,
    MatchParticipant,
    Organisation,
    Player,
    Season,
    Team,
    TeamMembership,
)


class DbPopulator:
    def __init__(
        self,
        logger: Logger,
        settings: Settings,
        extractor: Extractor,
        database: Database,
    ) -> None:
        self._logger = logger
        self._settings = settings
        self._extractor = extractor
        self._database = database

    def populate(self, page_id: int, html: BeautifulSoup) -> None:
        """Main function to populate the database with extracted data."""
        session = self._database.get_sync_session()()
        # Extract match metadata and data
        self._logger.debug("Extracting match metadata and data...")
        self._extractor.extract_data(page_id, html)
        season_year = self._extractor.season
        association_home_team = self._extractor.meta["association_home_team"]
        association_away_team = self._extractor.meta["association_away_team"]
        try:
            # Create or get season
            self._logger.debug("Creating season.")
            season = self._get_or_create_season(session, season_year)

            # Create or get division
            self._logger.debug("Creating division.")
            division = self._get_or_create_division(
                session,
                self._extractor.meta["division_name"],
                self._extractor.meta["division_hierarchy"],
                self._extractor.meta["division_region"],
                season,
            )

            # Create or get organisation
            self._logger.debug("Creating organisation.")
            organisation = self._get_or_create_organisation(
                session,
            )

            # Create or get association
            self._logger.debug("Creating association.")
            home_team_association = self._get_or_create_association(
                session,
                name=association_home_team,
                organisation=organisation,
            )
            away_team_association = self._get_or_create_association(
                session,
                name=association_away_team,
                organisation=organisation,
            )

            # Create or get teams
            self._logger.debug("Creating teams.")
            home_team = self._get_or_create_team(
                session,
                self._extractor.meta["home_team"],
                division,
                home_team_association,
            )
            away_team = self._get_or_create_team(
                session,
                self._extractor.meta["away_team"],
                division,
                away_team_association,
            )

            # Process matches and players
            self._logger.info("Processing matches...")
            self._create_matches_and_players(
                session,
                home_team,
                away_team,
                season,
            )

            # Commit transaction
            session.commit()
            self._logger.info("Database populated successfully.")

        except Exception as e:
            session.rollback()
            self._logger.error(f"Error populating database: {e!s}")
        finally:
            session.close()

    def _get_or_create_season(self, session: Session, season_year: int) -> Season:
        """Retrieve or create a new Season."""
        season = session.query(Season).filter_by(season_year=season_year).first()
        if not season:
            season = Season(season_year=season_year)
            session.add(season)
            session.flush()
        return season

    def _get_or_create_division(
        self,
        session: Session,
        division_name: str,
        hierarchy: int,
        region: str,
        season: Season,
    ) -> Division:
        """Retrieve or create a new Division."""
        # Convert division_name string to Division Enum
        division_enum = self.get_division_enum_from_value(division_name)
        division = (
            session.query(Division)
            .filter_by(name=division_enum, hierarchy=hierarchy, season_id=season.id)
            .first()
        )
        if not division:
            division = Division(
                name=division_enum,
                hierarchy=hierarchy,
                region=region,
                season_id=season.id,
            )
            session.add(division)
            session.flush()
        return division

    def _get_or_create_team(
        self,
        session: Session,
        team_name: str,
        division: Division,
        association: Association,
    ) -> Team:
        """Retrieve or create a new Team."""
        team = session.query(Team).filter_by(name=team_name).first()
        if not team:
            team = Team(
                name=team_name, division_id=division.id, association_id=association.id
            )
            session.add(team)
            session.flush()
        return team

    def _get_or_create_player(
        self,
        session: Session,
        player_name: str,
    ) -> Player:
        """Retrieve or create a new Player."""
        player = session.query(Player).filter_by(name=player_name).first()
        if not player:
            player = Player(
                name=player_name,
                current_mu=25.0,  # default value for mu
                current_sigma=8.0,  # default value for sigma
            )
            session.add(player)
            session.flush()
        return player

    def _create_matches_and_players(
        self,
        session: Session,
        home_team: Team,
        away_team: Team,
        season: Season,
    ) -> None:
        """Process match and player data, create necessary records."""
        if self._draws_possible(self._extractor.matches):
            self._logger.info("Draws are possible! Only double matches can be drawn.")
            env_draw_probability_double = 0.2
        else:
            self._logger.info(
                "Draws are NOT possible (both single and double matches)."
            )
            env_draw_probability_double = 0.0
        env_draw_probability_single = 0.0

        self.skill_calc_single = SkillCalc(draw_probability=env_draw_probability_single)
        self.skill_calc_double = SkillCalc(draw_probability=env_draw_probability_double)
        for match_data in self._extractor.matches:
            # Fetch initial ratings for the players
            if match_data["match_type"] == "single":
                self._logger.debug("Processing single match")
                home_player1 = self._get_or_create_player(
                    session, cast(str, match_data["p_home1"])
                )
                away_player1 = self._get_or_create_player(
                    session, cast(str, match_data["p_away2"])
                )

                # Create TrueSkill Rating objects
                h1_before = self.skill_calc_single.create_rating(
                    mu=home_player1.current_mu, sigma=home_player1.current_sigma
                )
                a1_before = self.skill_calc_single.create_rating(
                    mu=away_player1.current_mu, sigma=away_player1.current_sigma
                )

                # draw and win probabilities
                draw_probability: float = self.skill_calc_single.env.quality(
                    [[h1_before], [a1_before]]
                )
                win_probability: float = self.skill_calc_single.win_probability(
                    [h1_before], [a1_before]
                )

                # Rate players based on match outcome
                h1_after, a1_after = self.skill_calc_single.rate_single_match(
                    h1_before,
                    a1_before,
                    winner="player1" if match_data["who_won"] == "home" else "player2",
                )

                # Update current player ratings in Player()
                home_player1.current_mu = h1_after.mu
                home_player1.current_sigma = h1_after.sigma
                away_player1.current_mu = a1_after.mu
                away_player1.current_sigma = a1_after.sigma

                session.flush()

                player_ratings: Union[
                    # For singles matches
                    tuple[
                        trueskill.Raing,
                        trueskill.Raing,
                        trueskill.Raing,
                        trueskill.Raing,
                    ],
                    # For doubles matches
                    tuple[
                        trueskill.Raing,
                        trueskill.Raing,
                        trueskill.Raing,
                        trueskill.Raing,
                        trueskill.Raing,
                        trueskill.Raing,
                        trueskill.Raing,
                        trueskill.Raing,
                    ],
                ] = (
                    h1_before,
                    h1_after,
                    a1_before,
                    a1_after,
                )

            elif match_data["match_type"] == "double":
                self._logger.debug("Processing double match")
                home_player1 = self._get_or_create_player(
                    session, cast(str, match_data["p_home1"])
                )
                home_player2 = self._get_or_create_player(
                    session, cast(str, match_data["p_home2"])
                )
                away_player1 = self._get_or_create_player(
                    session, cast(str, match_data["p_away1"])
                )
                away_player2 = self._get_or_create_player(
                    session, cast(str, match_data["p_away2"])
                )
                # Create TrueSkill Rating objects
                h1_before = self.skill_calc_double.create_rating(
                    mu=home_player1.current_mu, sigma=home_player1.current_sigma
                )
                h2_before = self.skill_calc_double.create_rating(
                    mu=home_player2.current_mu, sigma=home_player2.current_sigma
                )
                a1_before = self.skill_calc_double.create_rating(
                    mu=away_player1.current_mu, sigma=away_player1.current_sigma
                )
                a2_before = self.skill_calc_double.create_rating(
                    mu=away_player2.current_mu, sigma=away_player2.current_sigma
                )

                # Teams for TrueSkill calculations
                team1 = [h1_before, h2_before]
                team2 = [a1_before, a2_before]

                # draw and win probabilities
                draw_probability = self.skill_calc_double.env.quality([team1, team2])
                win_probability = self.skill_calc_double.win_probability(team1, team2)

                # Rate teams based on match outcome
                (
                    (h1_after, h2_after),
                    (
                        a1_after,
                        a2_after,
                    ),
                ) = self.skill_calc_double.rate_double_match(
                    team1,
                    team2,
                    winner="team1" if match_data["who_won"] == "home" else "team2",
                )
                # Update player ratings
                home_player1.current_mu = h1_after.mu
                home_player1.current_sigma = h1_after.sigma
                home_player2.current_mu = h2_after.mu
                home_player2.current_sigma = h2_after.sigma

                away_player1.current_mu = a1_after.mu
                away_player1.current_sigma = a1_after.sigma
                away_player2.current_mu = a2_after.mu
                away_player2.current_sigma = a2_after.sigma

                session.flush()

                player_ratings = (
                    h1_before,
                    h1_after,
                    a1_before,
                    a1_after,
                    h2_before,
                    h2_after,
                    a2_before,
                    a2_after,
                )

            # Create match record
            match = Match(
                match_nr=int(match_data["match_number"]),
                date=self._extractor.meta["matchdate"],
                match_day_nr=self._extractor.meta["matchday"],
                draw_probability=draw_probability,
                win_probability=win_probability,
                sets_home=int(match_data["sets_home"]),
                sets_away=int(match_data["sets_away"]),
                who_won=str(match_data["who_won"]),
                match_type=str(match_data["match_type"]),
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                season_id=season.id,
            )

            session.add(match)

            # Add participants to the match
            self._add_match_participants(
                session,
                match,
                match_data,
                home_team,
                away_team,
                season,
                player_ratings,
            )

    def _add_match_participants(
        self,
        session: Session,
        match: Match,
        match_data: dict,
        home_team: Team,
        away_team: Team,
        season: Season,
        player_ratings: trueskill.Rating,
    ) -> None:
        """Add players to the match and ensure team memberships are recorded."""
        # Get players for the home and away teams
        home_player1 = self._get_or_create_player(session, match_data["p_home1"])
        away_player1 = self._get_or_create_player(
            session,
            match_data.get("p_away1", "") or match_data.get("p_away2", ""),
        )
        # Record team memberships for home and away players
        self._get_or_create_team_membership(session, home_player1, home_team, season)
        self._get_or_create_team_membership(session, away_player1, away_team, season)

        # Add participants to match (single match)
        match_participant_home1 = MatchParticipant(
            match_id=match.id,
            player_id=home_player1.id,
            team_side="home",
            mu_before=player_ratings[0].mu,
            sigma_before=player_ratings[0].sigma,
            mu_after=player_ratings[1].mu,
            sigma_after=player_ratings[1].sigma,
        )
        match_participant_away1 = MatchParticipant(
            match_id=match.id,
            player_id=away_player1.id,
            team_side="away",
            mu_before=player_ratings[2].mu,
            sigma_before=player_ratings[2].sigma,
            mu_after=player_ratings[3].mu,
            sigma_after=player_ratings[3].sigma,
        )
        session.add(match_participant_home1)
        session.add(match_participant_away1)

        # Add additional participants for double match
        if match_data["match_type"] == "double":
            home_player2 = self._get_or_create_player(session, match_data["p_home2"])
            away_player2 = self._get_or_create_player(session, match_data["p_away2"])

            self._get_or_create_team_membership(
                session, home_player2, home_team, season
            )
            self._get_or_create_team_membership(
                session, away_player2, away_team, season
            )

            match_participant_home2 = MatchParticipant(
                match_id=match.id,
                player_id=home_player2.id,
                team_side="home",
                mu_before=player_ratings[4].mu,
                sigma_before=player_ratings[4].sigma,
                mu_after=player_ratings[5].mu,
                sigma_after=player_ratings[5].sigma,
            )
            match_participant_away2 = MatchParticipant(
                match_id=match.id,
                player_id=away_player2.id,
                team_side="away",
                mu_before=player_ratings[6].mu,
                sigma_before=player_ratings[6].sigma,
                mu_after=player_ratings[7].mu,
                sigma_after=player_ratings[7].sigma,
            )
            session.add(match_participant_home2)
            session.add(match_participant_away2)

    def _get_or_create_organisation(self, session: Session) -> Organisation:
        """Retrieve or create a new Organisation."""
        # hardcoded: For now there is only BTFV
        name = "Bayerischer Tischfußballverband e.V."
        acronym = "BTFV"
        organisation = session.query(Organisation).filter_by(name=name).first()
        if not organisation:
            organisation = Organisation()
            session.add(organisation)
            session.flush()
            self._logger.info(f"Created organisation: {name} ({acronym})")
        return organisation

    def _get_or_create_association(
        self, session: Session, name: str, organisation: Organisation
    ) -> Association:
        """Retrieve or create a new Association."""
        association = session.query(Association).filter_by(name=name).first()
        if not association:
            association = Association(name=name, organisation_id=organisation.id)
            session.add(association)
            session.flush()
            self._logger.info(
                f"Created association (Verein): {name} "
                f"under organisation: {organisation.name}"
            )
        return association

    def _get_or_create_team_membership(
        self, session: Session, player: Player, team: Team, season: Season
    ) -> TeamMembership:
        """Get or create a team membership for the player in the given season."""
        team_membership = (
            session.query(TeamMembership)
            .filter_by(player_id=player.id, team_id=team.id, season_id=season.id)
            .first()
        )

        if not team_membership:
            team_membership = TeamMembership(
                player_id=player.id,
                team_id=team.id,
                season_id=season.id,
            )
            session.add(team_membership)
            session.flush()  # Ensure the record is saved to the database
            self._logger.info(
                f"Created team membership for {player.name} in team {team.name} "
                f"for season {season.season_year}"
            )

        return team_membership

    def get_division_enum_from_value(self, division_name: str) -> DivisionName:
        for enum_value in DivisionName:
            if enum_value.value == division_name:
                return enum_value
        raise ValueError(f"Invalid division name: {division_name}")

    def _draws_possible(self, matches_list: list[dict[str, Any]]) -> bool:
        # Iterate over each match in the list
        for match in matches_list:
            if match.get("result") == "1:1":
                return True
        return False
