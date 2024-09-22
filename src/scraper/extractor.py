import typing

from bs4 import BeautifulSoup

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
        matchday_data: BeautifulSoup,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.season = season
        self.page_id = page_id
        self.matchday_data = matchday_data

    def extact_matchreport(self):
        pass
