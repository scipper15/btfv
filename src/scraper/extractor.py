from datetime import datetime
import re
import typing

from bs4 import BeautifulSoup

from scraper.custom_errors import ElementNotFound

if typing.TYPE_CHECKING:
    from logging import Logger

    from shared.config.settings import Settings


class Extractor:
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

    def extact_matchreport(self):
        metadata = self._extract_matchday_metadata()
        home_players = self._extract_players(home=True)
        away_players = self._extract_players(home=False)
        player_map = self._create_player_map(home_players + away_players)
        [print(abbr, player) for abbr, player in player_map.items()]

    def _extract_players(self, home: bool) -> list[str]:
        idx = 0 if home else 1
        tables = self.html.find_all("table")
        rows = tables[idx].find("tbody").find_all("tr")
        player_names = [row.find_all("td")[1].get_text(strip=True) for row in rows]
        return player_names

    def _create_player_map(self, players: list) -> dict[str, str]:
        player_map: dict[str, str] = {}
        for player in players:
            idx = player.find(",") + 3
            player_abbr = f"{player[:idx]}."
            player_map = player_map | {player_abbr: player}
        return player_map

    def _extract_matchday_metadata(self):
        match_data = {}
        division_name = self._extract_match_division_name()
        self.logger.info(f"Division name: {division_name}")
        matchday = self._extract_match_day()
        self.logger.info(f"match day: {matchday}")
        matchdate = self._extract_match_date()
        self.logger.info(f"Match date: {matchdate}")
        home_team, away_team = self._extract_team_names()
        self.logger.info(f"Team names: {home_team}, {away_team}")
        match_data["meta"] = {
            "division_name": division_name,
            "matchday": matchday,
            "matchdate": matchdate,
            "home_team": home_team,
            "away_team": away_team,
        }
        return match_data

    def _extract_match_division_name(self) -> str:
        if self.heading1:
            match_day = re.search(r"(.*?)(?=\s*Spieltag)", self.heading1.text)
            if match_day:
                return match_day.group(1).strip()
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
