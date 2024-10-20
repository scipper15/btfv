from datetime import datetime
from logging import Logger
from pathlib import Path
import traceback
from typing import Any, cast

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
import trueskill

from scraper.extractor import Extractor
from scraper.file_handler import FileHandler
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
    PlayerCategory,
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
        filehandler: FileHandler,
    ) -> None:
        self._logger = logger
        self._settings = settings
        self._extractor = extractor
        self._database = database
        self._filehandler = filehandler

    def populate(self, page_id: int, html: BeautifulSoup) -> None:
        """Main function to populate the database with extracted data."""
        session = self._database.get_sync_session()
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
                cast(str, self._extractor.meta["division_name"]),
                cast(int, self._extractor.meta["division_hierarchy"]),
                cast(str, self._extractor.meta["division_region"]),
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
                name=cast(str, association_home_team),
                organisation=organisation,
            )
            away_team_association = self._get_or_create_association(
                session,
                name=cast(str, association_away_team),
                organisation=organisation,
            )

            # Create or get teams
            self._logger.debug("Creating teams.")
            home_team = self._get_or_create_team(
                session,
                cast(str, self._extractor.meta["home_team"]),
                division,
                home_team_association,
            )
            away_team = self._get_or_create_team(
                session,
                cast(str, self._extractor.meta["away_team"]),
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
                page_id,
            )

            # Commit transaction
            session.commit()
            self._logger.info("Database populated successfully.")

        except Exception as e:
            session.rollback()
            self._logger.error(f"Error populating database: {e!s}")
            self._logger.error(traceback.format_exc())

            # Re-raise the exception to stop further execution
            raise
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
            .filter_by(
                name=division_enum,
                hierarchy=hierarchy,
                region=region,
                season_id=season.id,
            )
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
        team = (
            session.query(Team)
            .filter_by(name=team_name, division_id=division.id)
            .first()
        )
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
        self._logger.info(f"Processing: {player_name}")
        player = session.query(Player).filter_by(name=player_name).first()
        if not player:
            player_html_path = self._filehandler.generate_path_for_player_html(
                player_name=player_name
            )
            player_image_path: Path | None = (
                self._filehandler.generate_path_for_player_image(
                    player_name=player_name
                )
            )

            if self._filehandler.exists(player_html_path):
                html = self._filehandler.read_HTML(file_path=player_html_path)
                player_info = self._extractor.extract_DTFB_player_information(
                    player_html=html, player_name=player_name
                )
                category_string = player_info.get("category", None)
                if category_string:
                    category = PlayerCategory(player_info.get("category"))
            else:
                category = None
                player_info = {}

            if not self._filehandler.exists(cast(Path, player_image_path)):
                player_image_path = None
                if category == PlayerCategory.HERREN:
                    # use placeholder image for men
                    player_image_file_name = "dummy_avatar_mann.png"
                elif category == PlayerCategory.DAMEN:
                    # use placeholder image for women
                    player_image_file_name = "dummy_avatar_frau.png"
                else:
                    # use placeholder binary / unknown
                    player_image_file_name = "dummy_avatar_binary.jpg"
            else:
                # use filename of existing image
                if player_image_path:
                    player_image_file_name = player_image_path.name

            DTFB_from_id: int | None = self._get_DTFB_from_id(player_name=player_name)

            player = Player(
                name=player_name,
                category=category if category else PlayerCategory.UNBEKANNT,
                national_id=player_info.get("national_id", None),
                international_id=player_info.get("international_id", None),
                # default values for mu and sigma
                current_mu_combined=25.0,
                current_sigma_combined=8.0,
                current_mu_singles=25.0,
                current_sigma_singles=8.0,
                current_mu_doubles=25.0,
                current_sigma_doubles=8.0,
                DTFB_from_id=DTFB_from_id,
                image_file_name=player_image_file_name,  # store filename only, not path
            )
            session.add(player)
            session.flush()
        return player

    def _get_DTFB_from_id(self, player_name: str) -> int | None:
        csv_data = self._filehandler.read_csv_as_dict(self._settings.DTFB_CSV_FILE)
        for row in csv_data:
            if row["player_name"] == player_name:
                if row["DTFB_from_id"]:
                    return int(row["DTFB_from_id"])
                return None
        return None

    def _create_matches_and_players(
        self,
        session: Session,
        home_team: Team,
        away_team: Team,
        season: Season,
        page_id: int,
    ) -> None:
        """Process match and player data, create necessary records."""
        if self._draws_possible(self._extractor.matches):
            env_draw_probability_double = 0.2
        else:
            env_draw_probability_double = 0.0
        env_draw_probability_single = 0.0

        # Create SkillCalc instances for singles and doubles
        self.skill_calc_single = SkillCalc(draw_probability=env_draw_probability_single)
        self.skill_calc_double = SkillCalc(draw_probability=env_draw_probability_double)

        for match_data in self._extractor.matches:
            self._logger.info(match_data)

            if match_data["match_type"] == "single":
                self._logger.debug("Processing single match")
                home_player1 = self._get_or_create_player(
                    session, cast(str, match_data["p_home1"])
                )
                away_player1 = self._get_or_create_player(
                    session, cast(str, match_data["p_away2"])
                )

                # Create TrueSkill Rating objects singles and doubles (combined)
                h1_before_combined = self.skill_calc_single.create_rating(
                    mu=home_player1.current_mu_combined,
                    sigma=home_player1.current_sigma_combined,
                )
                a1_before_combined = self.skill_calc_single.create_rating(
                    mu=away_player1.current_mu_combined,
                    sigma=away_player1.current_sigma_combined,
                )

                # Create TrueSkill Rating objects for singles (singles only)
                h1_before_singles = self.skill_calc_single.create_rating(
                    mu=home_player1.current_mu_singles,
                    sigma=home_player1.current_sigma_singles,
                )
                a1_before_singles = self.skill_calc_single.create_rating(
                    mu=away_player1.current_mu_singles,
                    sigma=away_player1.current_sigma_singles,
                )

                # Combined Rating Calculation
                (
                    h1_after_combined,
                    a1_after_combined,
                ) = self.skill_calc_single.rate_single_match(
                    h1_before_combined,
                    a1_before_combined,
                    winner="player1" if match_data["who_won"] == "home" else "player2",
                )

                # Singles Rating Calculation
                (
                    h1_after_singles,
                    a1_after_singles,
                ) = self.skill_calc_single.rate_single_match(
                    h1_before_singles,
                    a1_before_singles,
                    winner="player1" if match_data["who_won"] == "home" else "player2",
                )

                # Update current player ratings for combined and singles
                home_player1.current_mu_combined = h1_after_combined.mu
                home_player1.current_sigma_combined = h1_after_combined.sigma
                away_player1.current_mu_combined = a1_after_combined.mu
                away_player1.current_sigma_combined = a1_after_combined.sigma

                home_player1.current_mu_singles = h1_after_singles.mu
                home_player1.current_sigma_singles = h1_after_singles.sigma
                away_player1.current_mu_singles = a1_after_singles.mu
                away_player1.current_sigma_singles = a1_after_singles.sigma

                # Calculate Draw and Win Probabilities using Singles Ratings
                draw_probability = self.skill_calc_single.env.quality(
                    [[h1_before_singles], [a1_before_singles]]
                )
                win_probability = self.skill_calc_single.win_probability(
                    [h1_before_singles], [a1_before_singles]
                )

                session.flush()

                player_ratings_combined = (
                    h1_before_combined,
                    h1_after_combined,
                    a1_before_combined,
                    a1_after_combined,
                )
                player_ratings_singles = (
                    h1_before_singles,
                    h1_after_singles,
                    a1_before_singles,
                    a1_after_singles,
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

                # Create TrueSkill Rating objects for doubles (combined)
                h1_before_combined = self.skill_calc_double.create_rating(
                    mu=home_player1.current_mu_combined,
                    sigma=home_player1.current_sigma_combined,
                )
                h2_before_combined = self.skill_calc_double.create_rating(
                    mu=home_player2.current_mu_combined,
                    sigma=home_player2.current_sigma_combined,
                )
                a1_before_combined = self.skill_calc_double.create_rating(
                    mu=away_player1.current_mu_combined,
                    sigma=away_player1.current_sigma_combined,
                )
                a2_before_combined = self.skill_calc_double.create_rating(
                    mu=away_player2.current_mu_combined,
                    sigma=away_player2.current_sigma_combined,
                )

                # Create TrueSkill Rating objects for doubles (doubles only)
                h1_before_doubles = self.skill_calc_double.create_rating(
                    mu=home_player1.current_mu_doubles,
                    sigma=home_player1.current_sigma_doubles,
                )
                h2_before_doubles = self.skill_calc_double.create_rating(
                    mu=home_player2.current_mu_doubles,
                    sigma=home_player2.current_sigma_doubles,
                )
                a1_before_doubles = self.skill_calc_double.create_rating(
                    mu=away_player1.current_mu_doubles,
                    sigma=away_player1.current_sigma_doubles,
                )
                a2_before_doubles = self.skill_calc_double.create_rating(
                    mu=away_player2.current_mu_doubles,
                    sigma=away_player2.current_sigma_doubles,
                )

                # Combined Rating Calculation
                (
                    (h1_after_combined, h2_after_combined),
                    (a1_after_combined, a2_after_combined),
                ) = self.skill_calc_double.rate_double_match(
                    [h1_before_combined, h2_before_combined],
                    [a1_before_combined, a2_before_combined],
                    winner="team1" if match_data["who_won"] == "home" else "team2",
                )

                # Doubles Rating Calculation
                (
                    (h1_after_doubles, h2_after_doubles),
                    (a1_after_doubles, a2_after_doubles),
                ) = self.skill_calc_double.rate_double_match(
                    [h1_before_doubles, h2_before_doubles],
                    [a1_before_doubles, a2_before_doubles],
                    winner="team1" if match_data["who_won"] == "home" else "team2",
                )

                # Update current player ratings for combined and doubles
                home_player1.current_mu_combined = h1_after_combined.mu
                home_player1.current_sigma_combined = h1_after_combined.sigma
                home_player2.current_mu_combined = h2_after_combined.mu
                home_player2.current_sigma_combined = h2_after_combined.sigma

                away_player1.current_mu_combined = a1_after_combined.mu
                away_player1.current_sigma_combined = a1_after_combined.sigma
                away_player2.current_mu_combined = a2_after_combined.mu
                away_player2.current_sigma_combined = a2_after_combined.sigma

                home_player1.current_mu_doubles = h1_after_doubles.mu
                home_player1.current_sigma_doubles = h1_after_doubles.sigma
                home_player2.current_mu_doubles = h2_after_doubles.mu
                home_player2.current_sigma_doubles = h2_after_doubles.sigma

                away_player1.current_mu_doubles = a1_after_doubles.mu
                away_player1.current_sigma_doubles = a1_after_doubles.sigma
                away_player2.current_mu_doubles = a2_after_doubles.mu
                away_player2.current_sigma_doubles = a2_after_doubles.sigma

                # Calculate Draw and Win Probabilities using Doubles Ratings
                team1_ratings_doubles = [h1_before_doubles, h2_before_doubles]
                team2_ratings_doubles = [a1_before_doubles, a2_before_doubles]

                draw_probability = self.skill_calc_double.env.quality(
                    [team1_ratings_doubles, team2_ratings_doubles]
                )
                win_probability = self.skill_calc_double.win_probability(
                    team1_ratings_doubles, team2_ratings_doubles
                )

                session.flush()

                player_ratings_combined = (  # type: ignore
                    h1_before_combined,
                    h1_after_combined,
                    a1_before_combined,
                    a1_after_combined,
                    h2_before_combined,
                    h2_after_combined,
                    a2_before_combined,
                    a2_after_combined,
                )
                player_ratings_doubles = (
                    h1_before_doubles,
                    h1_after_doubles,
                    a1_before_doubles,
                    a1_after_doubles,
                    h2_before_doubles,
                    h2_after_doubles,
                    a2_before_doubles,
                    a2_after_doubles,
                )

            # Create match record
            match = Match(
                match_nr=int(match_data["match_number"]),
                date=cast(datetime, self._extractor.meta["matchdate"]),
                match_day_nr=cast(int, self._extractor.meta["matchday"]),
                draw_probability=draw_probability,
                win_probability=win_probability,
                sets_home=int(match_data["sets_home"]),
                sets_away=int(match_data["sets_away"]),
                who_won=str(match_data["who_won"]),
                match_type=str(match_data["match_type"]),
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                season_id=season.id,
                BTFV_from_id=page_id,
            )

            session.add(match)
            session.flush()

            # Add participants to the match
            if match_data["match_type"] == "single":
                self._add_match_participants(
                    session,
                    match,
                    match_data,
                    home_team,
                    away_team,
                    season,
                    player_ratings_combined=player_ratings_combined,
                    player_ratings_singles=player_ratings_singles,
                )
            elif match_data["match_type"] == "double":
                self._add_match_participants(
                    session,
                    match,
                    match_data,
                    home_team,
                    away_team,
                    season,
                    player_ratings_combined=player_ratings_combined,
                    player_ratings_doubles=player_ratings_doubles,
                )

    def _add_match_participants(
        self,
        session: Session,
        match: Match,
        match_data: dict[str, str | int],
        home_team: Team,
        away_team: Team,
        season: Season,
        player_ratings_combined: trueskill.Rating,
        player_ratings_singles: trueskill.Rating | None = None,
        player_ratings_doubles: trueskill.Rating | None = None,
    ) -> None:
        """Add players to the match and ensure team memberships are recorded."""
        # Get players for the home and away teams
        home_player1 = self._get_or_create_player(
            session, cast(str, match_data["p_home1"])
        )
        away_player1 = self._get_or_create_player(
            session,
            cast(str, match_data.get("p_away1", ""))
            or cast(str, match_data.get("p_away2", "")),
        )

        # Record team memberships for home and away players
        self._get_or_create_team_membership(session, home_player1, home_team, season)
        self._get_or_create_team_membership(session, away_player1, away_team, season)

        # Add participants to match (single match: home_player1)
        match_participant_home1 = MatchParticipant(
            match_id=match.id,
            player_id=home_player1.id,
            team_side="home",
            mu_before_combined=player_ratings_combined[0].mu,
            sigma_before_combined=player_ratings_combined[0].sigma,
            mu_after_combined=player_ratings_combined[1].mu,
            sigma_after_combined=player_ratings_combined[1].sigma,
            mu_before_singles=player_ratings_singles[0].mu
            if player_ratings_singles
            else None,
            sigma_before_singles=player_ratings_singles[0].sigma
            if player_ratings_singles
            else None,
            # n. b.: Adding current_mu_singles from Player
            # As we need both singles and double rating in each MatchParticipant
            mu_after_singles=player_ratings_singles[1].mu
            if player_ratings_singles
            else home_player1.current_mu_singles,
            sigma_after_singles=player_ratings_singles[1].sigma
            if player_ratings_singles
            else home_player1.current_sigma_singles,
            mu_before_doubles=player_ratings_doubles[0].mu
            if player_ratings_doubles
            else None,
            sigma_before_doubles=player_ratings_doubles[0].sigma
            if player_ratings_doubles
            else None,
            mu_after_doubles=player_ratings_doubles[1].mu
            # n. b.: Adding current_mu_doubles from Player
            # As we need both singles and double rating in each MatchParticipant
            if player_ratings_doubles else home_player1.current_mu_doubles,
            sigma_after_doubles=player_ratings_doubles[1].sigma
            if player_ratings_doubles
            else home_player1.current_sigma_doubles,
        )

        # Add participants to match (single match: away_player1)
        match_participant_away1 = MatchParticipant(
            match_id=match.id,
            player_id=away_player1.id,
            team_side="away",
            mu_before_combined=player_ratings_combined[2].mu,
            sigma_before_combined=player_ratings_combined[2].sigma,
            mu_after_combined=player_ratings_combined[3].mu,
            sigma_after_combined=player_ratings_combined[3].sigma,
            mu_before_singles=player_ratings_singles[2].mu
            if player_ratings_singles
            else None,
            sigma_before_singles=player_ratings_singles[2].sigma
            if player_ratings_singles
            else None,
            # n. b.: Adding current_mu_singles from Player
            # As we need both singles and double rating in each MatchParticipant
            mu_after_singles=player_ratings_singles[3].mu
            if player_ratings_singles
            else away_player1.current_mu_singles,
            sigma_after_singles=player_ratings_singles[3].sigma
            if player_ratings_singles
            else away_player1.current_sigma_singles,
            mu_before_doubles=player_ratings_doubles[2].mu
            if player_ratings_doubles
            else None,
            sigma_before_doubles=player_ratings_doubles[2].sigma
            if player_ratings_doubles
            else None,
            mu_after_doubles=player_ratings_doubles[3].mu
            # n. b.: Adding current_mu_doubles from Player
            # As we need both singles and double rating in each MatchParticipant
            if player_ratings_doubles else away_player1.current_mu_doubles,
            sigma_after_doubles=player_ratings_doubles[3].sigma
            if player_ratings_doubles
            else away_player1.current_sigma_doubles,
        )
        session.add(match_participant_home1)
        session.add(match_participant_away1)

        # Add additional participants for double match
        if match_data["match_type"] == "double":
            home_player2 = self._get_or_create_player(
                session, cast(str, match_data["p_home2"])
            )
            away_player2 = self._get_or_create_player(
                session, cast(str, match_data["p_away2"])
            )

            self._get_or_create_team_membership(
                session, home_player2, home_team, season
            )
            self._get_or_create_team_membership(
                session, away_player2, away_team, season
            )

            # Add participants to match (single match: home_player2)
            match_participant_home2 = MatchParticipant(
                match_id=match.id,
                player_id=home_player2.id,
                team_side="home",
                mu_before_combined=player_ratings_combined[4].mu,
                sigma_before_combined=player_ratings_combined[4].sigma,
                mu_after_combined=player_ratings_combined[5].mu,
                sigma_after_combined=player_ratings_combined[5].sigma,
                mu_before_singles=None,
                sigma_before_singles=None,
                # n. b.: Adding current_mu_singles from Player
                # As we need both singles and double rating in each MatchParticipant
                mu_after_singles=home_player2.current_mu_singles,
                sigma_after_singles=home_player2.current_sigma_singles,
                # adding newly calculated doubles values
                mu_before_doubles=player_ratings_doubles[4].mu,  # type: ignore
                sigma_before_doubles=player_ratings_doubles[4].sigma,  # type: ignore
                mu_after_doubles=player_ratings_doubles[5].mu,  # type: ignore
                sigma_after_doubles=player_ratings_doubles[5].sigma,  # type: ignore
            )
            # Add participants to match (single match: away_player2)
            match_participant_away2 = MatchParticipant(
                match_id=match.id,
                player_id=away_player2.id,
                team_side="away",
                mu_before_combined=player_ratings_combined[6].mu,
                sigma_before_combined=player_ratings_combined[6].sigma,
                mu_after_combined=player_ratings_combined[7].mu,
                sigma_after_combined=player_ratings_combined[7].sigma,
                mu_before_singles=None,
                sigma_before_singles=None,
                # n. b.: Adding current_mu_singles from Player
                # As we need both singles and double rating in each MatchParticipant
                mu_after_singles=away_player2.current_mu_singles,
                sigma_after_singles=away_player2.current_sigma_singles,
                # adding newly calculated doubles values
                mu_before_doubles=player_ratings_doubles[6].mu,  # type: ignore
                sigma_before_doubles=player_ratings_doubles[6].sigma,  # type: ignore
                mu_after_doubles=player_ratings_doubles[7].mu,  # type: ignore
                sigma_after_doubles=player_ratings_doubles[7].sigma,  # type: ignore
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
            logo_file_name = self._get_logo_file_name(name)
            association = Association(
                name=name,
                organisation_id=organisation.id,
                logo_file_name=logo_file_name,
            )
            session.add(association)
            session.flush()
            self._logger.info(
                f"Created association (Verein): {name} "
                f"under organisation: {organisation.name}"
            )
        return association

    def _get_logo_file_name(self, association_name: str) -> str:
        association_logo_dict_list = self._filehandler.read_csv_as_dict(
            Path(__file__).parent / "team_data.csv"
        )
        for item in association_logo_dict_list:
            if item["association_name"] == association_name:
                return item["logo_file_name"]
        return "dummy_logo.png"

    def _get_or_create_team_membership(
        self, session: Session, player: Player, team: Team, season: Season
    ) -> TeamMembership:
        """Get or create a team membership for the player in the given season."""
        # teams are allowed to use players of other teams playing in lower divisions
        # as support players twice a year, if they belong to the same association
        # example: Both SC Augsburg 2 and SC Augsburg 3 belong to the same organisation
        # SC Augsburg 2 can borrow a player from SC Augsburg 3 to play in their division
        # twice each division. We must prevent team association of these players to the
        # wrong team (the team playing in the higher division).

        # first we check if the player is already part of the team
        team_membership = (
            session.query(TeamMembership)
            .filter_by(player_id=player.id, team_id=team.id, season_id=season.id)
            .first()
        )

        if not team_membership:
            # if player has no team_membership we check if he is already registered to
            # another team in this particular season
            team_membership = (
                session.query(TeamMembership)
                .filter_by(player_id=player.id, season_id=season.id)
                .first()
            )
            if not team_membership:
                # just now we add the player to the team
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
            else:
                # otherwise we set the is_borrowed flag to True
                team_membership = TeamMembership(
                    player_id=player.id,
                    team_id=team.id,
                    season_id=season.id,
                    is_borrowed=True,
                )
                session.add(team_membership)
                session.flush()  # Ensure the record is saved to the database
                self._logger.info(
                    f"Created team membership for *BORROWED* {player.name} "
                    f"in team {team.name} for season {season.season_year}"
                )
        return team_membership

    def get_division_enum_from_value(self, division_name: str) -> DivisionName:
        for enum_value in DivisionName:
            if enum_value.value == division_name:
                return enum_value
        raise ValueError(f"Invalid division name: {division_name}")

    def get_category_enum_from_value(self, category_name: str) -> PlayerCategory:
        for enum_value in PlayerCategory:
            if enum_value.value == category_name:
                return enum_value
        raise ValueError(f"Invalid division name: {category_name}")

    def _draws_possible(self, matches_list: list[dict[str, Any]]) -> bool:
        # Iterate over each match in the list
        for match in matches_list:
            if match.get("result") == "1:1":
                return True
        return False
