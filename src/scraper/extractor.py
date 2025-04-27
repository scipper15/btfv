from datetime import datetime
from logging import Logger
import re
from types import MappingProxyType
from typing import Any, ClassVar, cast

from bs4 import BeautifulSoup

from scraper.custom_errors import ElementNotFound
from shared.config.settings import Settings


class Extractor:
    keyword_to_association = MappingProxyType(
        {
            "Aichach": "Speed Ball Team Aichach",
            "Allgäukickers": "Allgäukickers",
            "Allgäu": "TFC Allgäu",
            "Aschbach": "FK Aschbach",
            "Augsburg": "Soccer Connection Augsburg",
            "Bistro Avus": "TFC Bistro Avus Weidhausen",
            "Bamberg": "TFC Bamberg",
            "Bayreuth": "Soccer Club Foosion Bayreuth",
            "Burgheim": "Speed Ball Team Burgheim",
            "Deggendorf": "Kicker-Club Deggendorf",
            "First Floor Deggendorf": "First Floor Deggendorf",
            "Forchheim": "TFC Forchheim",
            "Ingolstadt": "ESV Ingolstadt Ringsee e.V.",
            "KC München": "KC München",
            "Kulmbach": "1. KSC Kulmbach e.V.",
            "Landau": "KC Landau",
            "Mainklein": "MK Mainklein",
            "Maisach": "TSG Maisach",
            "Marktleuthen": "Magic Soccer Marktleuthen",
            "Mellrichstadt": "GEKA Mellrichstadt e.V",
            "Münchberg": "TFC Münchberg",
            "München": "TFV München",
            "Nurn": "KC Nurn",
            "Nürnberg": "TFC Nürnberg",
            "Olydorf": "TFC Olydorf",
            "Passau": "DFST Passau",
            "Rettenbach": "TFC Old Stars Rettenbach",
            "Kronach": "Spielkiste Kronach",
            "Vilsbiburg": "Soccer Team Vilsbiburg",
            "Volkach": "Kurbelfreunde Volkach",
            "Vorderbreitenthann": "KDC Vorderbreitenthann e.V.",
            "Weiden": "DJK Weiden e.V.",
            "Würzburg": "Kurbelgemeinde Würzburg e. V.",
        }
    )
    team_name_sanitizer = MappingProxyType(
        {
            "DFST Passau": "DFST Passau 1",
            "KC Nurn": "KC Nurn 1",
            "Magic Soccer Marktleuthen": "Magic Soccer Marktleuthen 1",
            "Maintalkicker Mainklein": "MK Mainklein 1",
            "MK Mainklein": "MK Mainklein 1",
            "Soccer Club Foosion Bayreuth": "Soccer Club Foosion Bayreuth 1",
            "Soccer Team Landau": "Soccer Team Landau 1",
            "Speed Ball Team Burgheim": "Speed Ball Team Burgheim 1",
            "Spielkiste Kronach": "Spielkiste Kronach 1",
            "TFC Allgäu": "TFC Allgäu 1",
            "TFC Bamberg": "TFC Bamberg",
            "TFC München": "TFC München 1",
            "TFC Old Stars Rettenbach": "TFC Old Stars Rettenbach",
            "TFC Olydorf": "TFC Olydorf",
            "TFV München": "TFV München 1",
            "TSC Weiden": "TSC Weiden 1",
            "TSG Maisach e. V.": "TSG Maisach 1",
            "TSG Maisach e. V. 1": "TSG Maisach 1",
            "TSG Maisach e. V. 2": "TSG Maisach 2",
        }
    )
    division_name_sanitizer = MappingProxyType(
        {
            "Süd-Ost": "Südost",
            "Süd-West": "Südwest",
        }
    )
    players_to_remove: ClassVar = [
        "1, Freilos",
        "2, Freilos",
        "3, Freilos",
        "4, Freilos",
        "Freilos, 1",
        "Freilos, 2",
        "Freilos, 3",
        "Freilos, 4",
    ]
    player_name_sanitizer = MappingProxyType(
        {
            "Brosowsky , Felix": "Brosowsky, Felix",
            "Brosowsky , F.": "Brosowsky, F.",
            "Burkhardt, Hans": "Gangl, Hans",
            "Burkhardt, H.": "Gangl, H.",
            "Ebenhack , Matthias": "Ebenhack, Matthias",
            "Ebenhack , M.": "Ebenhack, M.",
            "Schillig , Stefan": "Schillig, Stefan",
            "Schillig , S.": "Schillig, S.",
            "Schließmann , Maximilian": "Schließmann, Maximilian",
            "Schließmann , M.": "Schließmann, M.",
            "Reitmaier , Korbinian": "Reitmaier, Korbinian",
            "Reitmaier , K.": "Reitmaier, K.",
            "Aboussibaa,  Soufiane": "Aboussibaa, Soufiane",
            "Aboussibaa,  S.": "Aboussibaa, S.",
            "Bowien, Monika": "Schließmann, Monika",
            "Bowien, M.": "Schließmann, M.",
            "Müller, Bernhard": "Fink, Bernhard",
            "Müller, B.": "Fink, B.",
            "Hysen, Hoti": "Hoti, Hysen",
            "Hysen, H.": "Hoti, H.",
            "Corc, Capar": "Capar, Corc",
            "Corc, C.": "Capar, C.",
            "Ak, Feyzullah": "Ak, Feyzo",
            "Al-Musali, Ali Ali Ali Awath": "Al-Musali, Ali",
            "Anderlic, Allexander": "Anderlic, Alexander",
            "Aslanidis, Dimitrios": "Aslanidis, Dimitri",
            "Dykeman, Christoph": "Dykeman, Christof",
            "Fischer, Rudi": "Fischer, Rudolf",
            "Fischer, Thorsten": "Fischer, Torsten",
            "Geb, Dennis": "Geb, Denis",
            "Hilgert, Erwin": "Hilgart, Erwin",
            "Hilgert, E.": "Hilgart, E.",
            "Jabiri, Souhail": "Jabiri, Souhayl",
            "Kastner, Matthias": "Kastner, Mathias",
            "Ruisinger, Tobias": "Keie-Ruisinger, Tobias",
            "Kinál, Bálazs": "Kinál, Balázs",
            "Lang, Reinhard Giovanni": "Lang, Reinhard",
            "Lorz, Karlheinz": "Lorz, Karl-Heinz",
            "Megele, Christopher": "Megele, Christoph",
            "Rankl, Rudi": "Rankl, Rudolf",
            "Willmann, Günther": "Willmann, Günter",
            "Zarember, Tobias": "Zaremba, Tobias",
            "Zarember, T.": "Zaremba, T.",
            "Ostermann, André": "Ostermann, Andree",
        }
    )

    def __init__(
        self,
        logger: "Logger",
        settings: "Settings",
    ) -> None:
        self._logger = logger
        self._settings = settings

    def extract_date(self, html: BeautifulSoup) -> datetime:
        small = html.find("small")
        if small:
            date_match = re.search(r"\d{2}.\d{2}.\d{4}", small.text.strip())
            if date_match:
                return datetime.strptime(date_match.group(), "%d.%m.%Y")
        raise ElementNotFound("No 'Date' found in <small> tag.")

    def extract_season_year(self, html: BeautifulSoup) -> int:
        small = html.find("small")
        if small:
            date_match = re.search(r"\d{2}.\d{2}.\d{4}", small.text.strip())
            if date_match:
                return datetime.strptime(date_match.group(), "%d.%m.%Y").year
        raise ElementNotFound("No 'Date' found in <small> tag.")

    def extract_urls(self, page_type: str, html: BeautifulSoup) -> list[str]:
        pattern = re.compile(
            re.escape(f"{self._settings.BTFV_URL_BASE}/{page_type}/anzeigen/")
        )
        a_tags = html.find_all("a", href=re.compile(pattern))
        # Using a set() to remove possible duplicates
        sorted_by_id = sorted(list({a_tag["href"] for a_tag in a_tags}))  # noqa: C414
        return sorted_by_id

    def extract_page_type_from_url(self, url: str) -> str:
        return url.split("/")[4]

    def extract_page_id_from_url(self, url: str) -> int:
        return int(url.split("/")[-2])

    def extract_data(self, page_id: int, html: BeautifulSoup) -> None:
        self.season = self.extract_season_year(html=html)
        self.page_id = page_id
        self.html = html
        self.heading1 = self.html.find("h1")
        self.meta = self._extract_matchday_metadata()
        self.home_players = Extractor.extract_players(html=self.html, home=True)
        self.away_players = Extractor.extract_players(html=self.html, home=False)
        self.player_map = self._create_player_map(self.home_players + self.away_players)
        self._logger.debug("Players on this matchday:")

        for abbr, player in self.player_map.items():
            self._logger.debug(f"{abbr}, {player}")

        self.matches = self._extract_matches(self.player_map)
        self._logger.info(f"{len(self.matches)} matches found.")

    @staticmethod
    def extract_players(html: BeautifulSoup, home: bool) -> list[Any]:
        idx = 0 if home else 1
        tables = html.find_all("table")
        rows = tables[idx].find("tbody").find_all("tr")
        player_names = [row.find_all("td")[1].get_text(strip=True) for row in rows]

        if any(name == ":" for name in player_names):
            idx = -2 if home else -1
            rows = (
                tables[idx].find("tbody").find_all("tr")
            )  # You need to re-assign rows here!
            player_names = [row.find_all("td")[1].get_text(strip=True) for row in rows]

        player_names = cast(
            list[str], Extractor._sanitize_player_names(player_names=player_names)
        )

        return player_names

    @staticmethod
    def _sanitize_player_names(
        player_names: list[Any] | tuple[Any, ...] | str,
    ) -> list[str] | tuple[str] | str:
        if isinstance(player_names, list):
            return [
                Extractor.player_name_sanitizer.get(player_name, player_name)
                for player_name in player_names
            ]
        elif isinstance(player_names, tuple):
            return [
                Extractor.player_name_sanitizer.get(player_name, player_name)
                for player_name in player_names
            ]
        elif isinstance(player_names, str):
            return Extractor.player_name_sanitizer.get(player_names, player_names)

    def _sanitize_division_name(self, region: str) -> str:
        return Extractor.division_name_sanitizer.get(region, region)

    def _sanitize_team_name(self, team_name: str) -> str:
        team_name = team_name.replace(" e.V.", "")
        team_name = team_name.replace("1.KSC", "1. KSC")
        team_name = team_name.replace("TFC-Bamberg", "TFC Bamberg")
        team_name = team_name.replace("Muenchen", "München")
        return team_name

    def _create_player_map(self, players: list[str]) -> dict[str, str]:
        player_map: dict[str, str] = {}
        for player in players:
            # abbreviate player name
            idx = player.find(",") + 3
            if idx:
                player_abbr = f"{player[:idx]}."
                if player_map.get(player_abbr, False):
                    self._logger.warning(
                        f"Ambiguity found: {player_abbr} -> {player} "
                        f"already exists as: {player_map.get(player_abbr)} "
                        f"found at {self.page_id}"
                    )
            else:
                # skip invalid player names
                continue
            player_map = player_map | {player_abbr: player}
        return player_map

    def _extract_matches(  # noqa: C901
        self, player_map: dict[str, str]
    ) -> list[dict[str, str | int]]:
        matches_list: list[dict[str, str | int]] = []
        pattern = re.compile(r"(einzel|doppel)")
        tables = self.html.find_all("table", id=pattern)
        offset_double = 6
        offset_single = 4
        match_number = 0
        if tables:
            for idx, table in enumerate(tables):
                table_id = table["id"]
                self._logger.debug(f"Processing table id: {table_id}.")
                if "doppel" in table_id:
                    tds = tables[idx].find("tbody").find_all("td")
                    for step in range(0, len(tds), offset_double):
                        match_number += 1

                        p_home1 = player_map.get(
                            cast(
                                str,
                                self._sanitize_player_names(tds[0 + step].text.strip()),
                            ),
                            None,
                        )
                        p_away1 = player_map.get(
                            cast(
                                str,
                                self._sanitize_player_names(tds[2 + step].text.strip()),
                            ),
                            None,
                        )
                        p_home2 = player_map.get(
                            cast(
                                str,
                                self._sanitize_player_names(tds[4 + step].text.strip()),
                            ),
                            None,
                        )
                        p_away2 = player_map.get(
                            cast(
                                str,
                                self._sanitize_player_names(tds[5 + step].text.strip()),
                            ),
                            None,
                        )

                        opponents_double = (p_home1, p_home2, p_away1, p_away2)

                        # check for invalid player name: skip the match data
                        if any(s is None for s in opponents_double):
                            continue
                        if any(
                            s in Extractor.players_to_remove for s in opponents_double
                        ):
                            continue

                        # sanitize player name abbreviations
                        (
                            p_home1,
                            p_home2,
                            p_away1,
                            p_away2,
                        ) = cast(
                            tuple[str, str, str, str],
                            Extractor._sanitize_player_names(opponents_double),
                        )

                        result = tds[3 + step].text.strip()
                        sets_home, sets_away, who_won = self._check_who_won(result)

                        matches_list.append(
                            {
                                "match_number": match_number,
                                "match_type": "double",
                                "who_won": who_won,
                                "p_home1": p_home1,
                                "p_home2": p_home2,
                                "p_away1": p_away1,
                                "p_away2": p_away2,
                                "result": result,
                                "sets_home": sets_home,
                                "sets_away": sets_away,
                            }
                        )
                elif "einzel" in table_id:
                    tds = tables[idx].find("tbody").find_all("td")
                    for step in range(0, len(tds), offset_single):
                        match_number += 1

                        p_home1 = player_map.get(
                            cast(
                                str,
                                self._sanitize_player_names(tds[0 + step].text.strip()),
                            ),
                            None,
                        )
                        p_away1 = player_map.get(
                            cast(
                                str,
                                self._sanitize_player_names(tds[2 + step].text.strip()),
                            ),
                            None,
                        )
                        result = tds[3 + step].text.strip()

                        # if invalid player name skip the match data
                        opponents_single = (p_home1, p_away1)
                        if any(s is None for s in opponents_single):
                            continue
                        if any(
                            s in Extractor.players_to_remove for s in opponents_single
                        ):
                            continue
                        # sanitize player name abbreviations
                        p_home1, p_away1 = cast(
                            tuple[str, str],
                            Extractor._sanitize_player_names(opponents_single),
                        )

                        sets_home, sets_away, who_won = self._check_who_won(result)

                        matches_list.append(
                            {
                                "match_number": match_number,
                                "match_type": "single",
                                "who_won": who_won,
                                "p_home1": p_home1,
                                "p_away2": p_away1,
                                "result": tds[3 + step].text.strip(),
                                "sets_home": sets_home,
                                "sets_away": sets_away,
                            }
                        )
        return matches_list

    def _check_who_won(self, result: str) -> tuple[str, str, str]:
        split_result = result.split(":")
        sets_home, sets_away = split_result[0], split_result[1]
        if sets_home != sets_away:
            who_won = "home" if sets_home > sets_away else "away"
        else:
            who_won = "draw"
        return sets_home, sets_away, who_won

    def _extract_matchday_metadata(self) -> dict[str, object]:
        division_name, division_region = self._extract_match_division()
        division_region = self._sanitize_division_name(division_region)
        possible_divisions = {
            "Landesliga": 1,
            "Verbandsliga": 2,
            "Bezirksliga": 3,
            "Kreisliga": 4,
        }
        division_hierarchy = possible_divisions[division_name]
        matchday = self._extract_match_day()
        matchdate = self._extract_match_date()
        home_team, away_team = self._extract_team_names()
        home_team, away_team = (
            self._sanitize_team_name(home_team),
            self._sanitize_team_name(away_team),
        )
        association_home_team = self._infer_association(home_team)
        association_away_team = self._infer_association(away_team)
        meta = {
            "division_name": division_name,
            "division_region": division_region,
            "division_hierarchy": division_hierarchy,
            "matchday": matchday,
            "matchdate": matchdate,
            "home_team": home_team,
            "away_team": away_team,
            "association_home_team": association_home_team,
            "association_away_team": association_away_team,
        }
        return meta

    def _extract_match_division(self) -> tuple[str, str]:
        if self.heading1:
            division = re.search(r"(.*?)(?=\s*Spieltag)", self.heading1.text.strip())
            if division:
                pattern = (
                    r"\b(?P<division>Landesliga|Verbandsliga|Bezirksliga|Kreisliga)"
                    r"\b(?:\s+(?P<region>Gruppe\s[A-D]|(?:Bayern|Nord|Süd|West|Ost)"
                    r"(?:[-]?(?:[A-Za-z]+))?(?:\s+[12])?))?"
                )
                match = re.search(pattern, division.group(1).strip())
                if match:
                    if (
                        match.group("division") == "Bezirksliga"
                        and match.group("region") is None
                    ):
                        # One exception in Bezirksliga 2016: Only region is "Bayern"
                        return match.group("division"), "Bayern"
                    return match.group("division"), match.group("region")
        raise ElementNotFound("No division name in <h1>-tag.")

    def _extract_match_day(self) -> int:
        if self.heading1:
            match_day = re.search(r"(?:.)+(?:Spieltag\s*)(\d+)*", self.heading1.text)
            if match_day:
                return int(match_day.group(1))
        raise ElementNotFound("No matchday in <h1>-tag.")

    def _extract_match_date(self) -> datetime:
        if self.heading1:
            match_date = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", self.heading1.text)
            if match_date:
                match_date_str = match_date.group()
                match_date_obj = datetime.strptime(match_date_str, "%d.%m.%Y")
                return match_date_obj
        raise ElementNotFound("No matchdate in <h1>-tag.")

    def _extract_team_names(self) -> tuple[str, str]:
        if self.heading1:
            h2 = self.html.find_all("h2")
            home_team = h2[0].text.strip()
            away_team = h2[2].text.strip()
            return (home_team, away_team)
        raise ElementNotFound("No team names found in <h1>-tag.")

    def extract_DTFB_player_information(
        self, player_html: BeautifulSoup, player_name: str
    ) -> dict[str, str | None]:
        tables = player_html.find_all("table")

        player_table = tables[4].find_all(
            "tr"
        )  # this table contains player information

        player_info = {
            "player_name": player_name,
            "category": None,
            "national_id": None,
            "international_id": None,
            "license": None,
        }

        row_to_key_mapping = {
            "Kategorie:": "category",
            "Nationale Spielernr.:": "national_id",
            "Internationale Spielernr.:": "international_id",
            "Lizenz:": "license",
        }

        # Iterate through each row and extract the relevant information
        for row in player_table:
            cols = row.find_all("td")
            if len(cols) == 2:
                label = cols[0].get_text(strip=True)
                value = cols[1].get_text(strip=True)

                # Check if the label corresponds to a key in the player_info dictionary
                if label in row_to_key_mapping:
                    player_info[row_to_key_mapping[label]] = value
        self._logger.debug("Player Information from DTFB:")
        for key, value in player_info.items():
            self._logger.info(f"{key}: {value}")

        return player_info

    def _infer_association(self, team_name: str) -> str:
        """Infers the association name from a team name mapping.

        Parameters:
            team_name (str): The name of the team to infer the association for.
            keyword_to_association (Dict[str, str]): A mapping of keywords to
                                                     association names.

        Returns:
            Optional[str]: The name of the inferred association, or None if
                           no match is found.
        """
        team_name_lower = team_name.lower()

        for keyword, association in Extractor.keyword_to_association.items():
            if keyword.lower() in team_name_lower:
                return association
        # if not mapped use team_name for association name
        return team_name
