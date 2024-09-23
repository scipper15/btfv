from datetime import datetime
import re
from types import MappingProxyType
import typing

from bs4 import BeautifulSoup

from scraper.custom_errors import ElementNotFound

if typing.TYPE_CHECKING:
    from logging import Logger

    from shared.config.settings import Settings


class Extractor:
    player_name_sanitizer = MappingProxyType(
        {
            "Brosowsky , Felix": "Brosowsky, Felix",
            "Brosowsky , F.": "Brosowsky, F.",
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
            "Kinál, Bálazs": "Kinál, Balázs",
            "Lang, Reinhard Giovanni": "Lang, Reinhard",
            "Lorz, Karlheinz": "Lorz, Karl-Heinz",
            "Megele, Christopher": "Megele, Christoph",
            "Rankl, Rudi": "Rankl, Rudolf",
            "Willmann, Günther": "Willmann, Günter",
            "Zarember, Tobias": "Zaremba, Tobias",
            "Zarember, T.": "Zaremba, T.",
        }
    )

    def __init__(
        self,
        settings: "Settings",
        logger: "Logger",
        season: int,
        page_id: int,
        html: BeautifulSoup,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.season = season
        self.page_id = page_id
        self.html = html
        self.heading1 = self.html.find("h1")
        logger.info("Next matchday...")
        logger.info(f"Season: {season}, page id: {page_id}")

    def extract_matchreport(self):
        self.metadata = self._extract_matchday_metadata()
        home_players = self._extract_players(home=True)
        away_players = self._extract_players(home=False)
        player_map = self._create_player_map(home_players + away_players)
        self.logger.info("Players on this matchday:")
        [self.logger.info(f"{abbr}, {player}") for abbr, player in player_map.items()]
        self.matches = self._extract_matches(player_map)
        self.logger.info(f"{len(self.matches)} matches found.")

    def _extract_players(self, home: bool) -> list[str]:
        idx = 0 if home else 1
        tables = self.html.find_all("table")
        rows = tables[idx].find("tbody").find_all("tr")
        player_names = [row.find_all("td")[1].get_text(strip=True) for row in rows]
        player_names = self._sanitize_player_names(player_names=player_names)
        return player_names

    def _sanitize_player_names(self, player_names: list | tuple) -> list[str]:
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

    def _create_player_map(self, players: list) -> dict[str, str]:
        player_map: dict[str, str] = {}
        for player in players:
            # abbreveate player name
            idx = player.find(",") + 3
            if idx:
                player_abbr = f"{player[:idx]}."
                if player_map.get(player_abbr, False):
                    self.logger.warning(
                        f"Ambiguity found: {player_abbr} -> {player} "
                        f"already exists as: {player_map.get(player_abbr)} "
                        f"found at {self.page_id}"
                    )
            else:
                # skip invalid player names
                continue
            player_map = player_map | {player_abbr: player}
        return player_map

    def _extract_matches(self, player_map) -> list[dict[str, str]]:
        matches_list: list[dict[str, str]] = []
        pattern = re.compile(r"(einzel|doppel)")
        tables = self.html.find_all("table", id=pattern)
        offset_double = 6
        offset_single = 4
        match_number = 0

        if tables:
            for idx, table in enumerate(tables):
                table_id = table["id"]
                self.logger.debug(f"Processing table id: {table_id}.")
                if "doppel" in table_id:
                    tds = tables[idx].find("tbody").find_all("td")
                    for step in range(0, len(tds), offset_double):
                        match_number += 1

                        p_home1 = player_map.get(tds[0 + step].text.strip(), None)
                        p_away1 = player_map.get(tds[2 + step].text.strip(), None)
                        p_home2 = player_map.get(tds[4 + step].text.strip(), None)
                        p_away2 = player_map.get(tds[5 + step].text.strip(), None)

                        # if invalid player name skip the match data
                        opponents_double = (p_home1, p_home2, p_away1, p_away2)
                        if any(opponents_double) is None:
                            continue
                        # sanitize player name abbreviations
                        (
                            p_home1,
                            p_home2,
                            p_away1,
                            p_away2,
                        ) = self._sanitize_player_names(opponents_double)

                        result = tds[3 + step].text.strip()
                        sets_home, sets_away, who_won = self._check_who_won(result)

                        matches_list.append(
                            {
                                "match_number": str(match_number),
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

                        p_home1 = player_map.get(tds[0 + step].text.strip(), None)
                        p_away1 = player_map.get(tds[2 + step].text.strip(), None)
                        result = tds[3 + step].text.strip()

                        # if invalid player name skip the match data
                        opponents_single = (p_home1, p_away1)
                        if any(opponents_single) is None:
                            continue
                        # sanitize player name abbreviations
                        p_home1, p_away1 = self._sanitize_player_names(opponents_single)

                        sets_home, sets_away, who_won = self._check_who_won(result)

                        matches_list.append(
                            {
                                "match_number": str(match_number),
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

    def _check_who_won(self, result) -> tuple[str, str, str]:
        split_result = result.split(":")
        sets_home, sets_away = split_result[0], split_result[1]
        if sets_home != sets_away:
            who_won = "home" if sets_home > sets_away else "away"
        else:
            who_won = "draw"
        return sets_home, sets_away, who_won

    def _extract_matchday_metadata(self):
        match_data = {}
        division_name, division_region = self._extract_match_division()
        possible_divisions = {
            "Landesliga": 1,
            "Verbandsliga": 2,
            "Bezirksliga": 3,
            "Kreisliga": 4,
        }
        division_hierarchy = possible_divisions[division_name]
        self.logger.info(
            f"Division name: {division_name}, Region: {division_region}, Hierarchy: {division_hierarchy}"  # noqa
        )
        matchday = self._extract_match_day()
        self.logger.info(f"match day: {matchday}")
        matchdate = self._extract_match_date()
        self.logger.info(f"Match date: {matchdate}")
        home_team, away_team = self._extract_team_names()
        self.logger.info(f"Team names: {home_team}, {away_team}")
        match_data["meta"] = {
            "division_name": division_name,
            "division_region": division_region,
            "division_hierarchy": division_hierarchy,
            "matchday": matchday,
            "matchdate": matchdate,
            "home_team": home_team,
            "away_team": away_team,
        }
        return match_data

    def _extract_match_division(self) -> tuple[str, str]:
        if self.heading1:
            division = re.search(r"(.*?)(?=\s*Spieltag)", self.heading1.text)
            if division:
                pattern = (
                    r"\b(?P<division>Landesliga|Verbandsliga|Bezirksliga|Kreisliga)"
                    r"\b(?:\s+(?P<region>Gruppe\s[A-D]|(?:Bayern|Nord|Süd|West|Ost)"
                    r"(?:[-]?(?:[A-Za-z]+))?(?:\s+[12])?))\s*(?!\d{4})"
                )
                match = re.search(pattern, division.group(1).strip())
                if match:
                    return match.group("division"), match.group("region")
        raise ElementNotFound("No division name in <h1>-tag.")

    def _extract_match_day(self) -> int:
        if self.heading1:
            match_day = re.search(r"(?:.)+(?:Spieltag\s*)(\d)*", self.heading1.text)
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
