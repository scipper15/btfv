import re
import typing
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from scraper.custom_errors import InvalidSeason

if typing.TYPE_CHECKING:
    from logging import Logger

    from shared.config.settings import Settings


class Scraper:
    def __init__(self, settings: "Settings", logger: "Logger", season: int) -> None:
        self.settings = settings
        self.logger = logger
        self.season = season

        self.RAW_HTML_PATH = self.settings.RAW_HTML_PATH
        self.base_url = "https://btfv.de/sportdirector"
        self.suffix = "no_frame"

        self.page_id = self._get_id_from_season()
        self.season_url = self._generate_starting_url()
        self.season_html = self._get_html(self.season_url)
        self.liga_urls = self._get_urls("liga", self.season_html)

        self.logger.info(f"Season: {season}.")
        self.logger.info(f"Starting url: {self.season_url}")
        self.logger.info(self.liga_urls)

    def _get_id_from_season(self) -> int:
        if self.season < 2012:
            raise InvalidSeason(f"No data before season {self.season}.")
        elif 2012 <= self.season <= 2020:
            page_id = self.season - 2000
        elif self.season == 2021:
            raise InvalidSeason(f"No data due to Covid19 in season {self.season}.")
        elif 2022 <= self.season <= datetime.now().year:
            page_id = self.season - 2000 - 1
        elif self.season > datetime.now().year:
            raise InvalidSeason(f"No data for future season {self.season}.")
        return page_id

    def _generate_starting_url(self) -> str:
        return f"{self.base_url}/saison/anzeigen/{self.page_id}/{self.suffix}"

    def _get_html(self, url) -> BeautifulSoup:
        r = requests.get(url)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")

    def _get_urls(self, page_type: str, html: BeautifulSoup) -> list[str]:
        a_tags = html.find_all("a", href=re.compile(rf"{page_type}"))
        return [a_tag["href"] for a_tag in a_tags]

    def scrape(self) -> None:
        pass


def main():
    pass


if __name__ == "__main__":
    main()
