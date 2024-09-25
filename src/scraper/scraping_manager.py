from datetime import datetime
from logging import Logger

from bs4 import BeautifulSoup

from scraper.extractor import Extractor
from scraper.scraper import PlayerScraper, Scraper
from shared.config.settings import Settings


class ScrapingManager:
    def __init__(
        self,
        logger: Logger,
        settings: Settings,
        scraper: Scraper,
        player_scraper: PlayerScraper,
        extractor: Extractor,
    ) -> None:
        self.logger = logger
        self.settings = settings
        self.scraper = scraper
        self.player_scraper = player_scraper
        self.extractor = extractor
        self._generate_starting_url()

    def _generate_starting_url(self) -> list[str]:
        return [
            f"{self.settings.BTFV_URL_BASE}/saison/anzeigen/{page_id}/no_frame"
            for page_id in range(12, datetime.now().year - 2000)
        ]

    def _get_season_from_season_page_id(self, page_id: int) -> int:
        if 12 <= page_id <= 20:
            return 2000 + page_id
        else:
            return 2000 + page_id + 1

    def _process_match_reports(
        self, season: int, division_url: str
    ) -> list[tuple[int, BeautifulSoup]]:
        """Fetches and processes match reports for a given division."""
        html = self.scraper.get_HTML(season, division_url)
        if not html:
            return []

        match_report_data = []
        match_report_urls = self.extractor.extract_urls(
            page_type="spielbericht", html=html
        )

        for match_report_url in match_report_urls:
            match_html = self.scraper.get_HTML(season, match_report_url)
            if match_html:
                match_report_page_id = self.extractor.extract_page_id_from_url(
                    match_report_url
                )
                match_report_data.append((match_report_page_id, match_html))
                self.logger.info(f"New match report found: {match_report_page_id}")

        return match_report_data

    def _process_divisions(
        self, season: int, season_html: BeautifulSoup
    ) -> list[tuple[int, BeautifulSoup]]:
        """Fetches and processes divisions for a given season."""
        division_urls = self.extractor.extract_urls(page_type="liga", html=season_html)
        all_match_reports = []
        for division_url in division_urls:
            match_reports = self._process_match_reports(season, division_url)
            all_match_reports.extend(match_reports)
        return all_match_reports

    def _sort_match_reports(
        self, match_report_data: list[tuple[int, BeautifulSoup]]
    ) -> list[tuple[int, BeautifulSoup]]:
        """Sort match reports by date extracted from HTML."""
        return sorted(
            match_report_data,
            key=lambda id_html: self.extractor.extract_date(id_html[1]),
        )

    def process_seasons(self) -> None:
        """Process all seasons."""
        new_match_report_data_by_season = {}

        for season_url in self._generate_starting_url():
            season_page_id = self.extractor.extract_page_id_from_url(season_url)
            season = self._get_season_from_season_page_id(season_page_id)
            self.logger.info(
                f"Processing: Season {season}, Page ID {season_page_id}, "
                f"Season URL {season_url}"
            )

            season_html = self.scraper.get_HTML(season, season_url)
            if not season_html:
                continue

            # Process all divisions and gather match report data
            match_report_data = self._process_divisions(season, season_html)

            # Sort match reports by date
            sorted_match_reports = self._sort_match_reports(match_report_data)
            new_match_report_data_by_season[season] = sorted_match_reports

        self._log_and_extract_data(new_match_report_data_by_season)

    def process_season(self, season: int) -> None:
        """Convenience function: Process one season."""
        pass

    def _log_and_extract_data(
        self,
        new_match_report_data_by_season: dict[int, list[tuple[int, BeautifulSoup]]],
    ) -> None:
        """Logs and extracts data from new match reports."""
        match_report_count = len(
            {x for v in new_match_report_data_by_season.values() for x in v}
        )

        if match_report_count:
            for season, tuple_list in new_match_report_data_by_season.items():
                self.logger.info(f"{season}: {len(tuple_list)} match reports.")
                for page_id, html in tuple_list:
                    self.extractor.extract_data(season, page_id, html)
        else:
            self.logger.info("No new match reports found.")
