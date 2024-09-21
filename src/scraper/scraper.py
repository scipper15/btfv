from datetime import datetime
from pathlib import Path
import re
import typing

from bs4 import BeautifulSoup
import requests

from scraper.custom_errors import InvalidSeason, ValidationError

if typing.TYPE_CHECKING:
    from logging import Logger

    from shared.config.settings import Settings


class Scraper:
    """A class to scrape foosball data from BTFV website based on a given season.

    Attributes:
        season (int): The season to scrape.
        new_matchreports_html (list[tuple[int, BeautifulSoup]]): List to store new match
                                                                 reports.
        season_url (str): Starting URL for the season.
        division_urls (list[str]): List of division URLs to scrape.
    """

    def __init__(self, settings: "Settings", logger: "Logger", season: int) -> None:
        """Initialize the Scraper with settings, logger, and season.

        Args:
            settings (Settings): Application settings for paths, env variables, etc.
            logger (Logger): Logger instance to log information and errors.
            season (int): The foosball season to scrape.
        """
        self._settings = settings
        self._logger = logger
        self.season = season
        self.new_matchreports_html: list[tuple[int, BeautifulSoup]] = []

        self._RAW_HTML_PATH = self._settings.RAW_HTML_PATH
        self._base_url = "https://btfv.de/sportdirector"
        self._url_suffix = "no_frame"

        self._page_id = self._get_id_from_season()
        self.season_url = self._generate_starting_url()
        self._season_html = self._get_html(self.season_url)
        self.division_urls = self._get_urls("liga", self._season_html)

        self._logger.info(f"Season: {season}.")
        self._logger.info(f"Starting url: {self.season_url}")
        self._logger.info(self.division_urls)

    def _get_id_from_season(self) -> int:
        """Get the page ID for the given season.

        Raises:
            InvalidSeason: If the season is before 2012, during 2021 (Covid19),
                           or in the future.

        Returns:
            int: The page ID for the season.
        """
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

    def _get_page_id_from_url(self, url) -> int:
        """Extract the page ID from the given URL.

        Args:
            url (str): The URL from which to extract the page ID.

        Raises:
            ValidationError: If the page ID is not found in the URL.

        Returns:
            int: The extracted page ID.
        """
        page_id = url.split("/")[-2]
        if page_id:
            return page_id
        raise ValidationError(f"page_id not found in url {url}")

    def _generate_starting_url(self) -> str:
        """Generate the starting URL for the season.

        Returns:
            str: The starting URL for the season.
        """
        return f"{self._base_url}/saison/anzeigen/{self._page_id}/{self._url_suffix}"

    def _retrieve_html_from_server(self, url) -> BeautifulSoup:
        """Retrieve the HTML content from the given URL.

        Args:
            url (str): The URL to request HTML from.

        Returns:
            BeautifulSoup: Parsed HTML content.
        """
        self._logger.info(f"Reading HTML from {url}.")
        r = requests.get(url)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")

    def _cache_html_to_file(self, filepath, html) -> None:
        """Save the HTML content to a file.

        Args:
            filepath (Path): Path to save the HTML file.
            html (BeautifulSoup): Parsed HTML content to save.
        """
        self._logger.info(f"Saving HTML to {filepath}.")
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(html.prettify())

    def _get_html(self, url) -> BeautifulSoup:
        """Retrieve and cache HTML from a URL, using a cached file if it exists.

        Args:
            url (str): The URL to get HTML content from.

        Returns:
            BeautifulSoup: Parsed HTML content.
        """
        filepath = self._generate_path_from_url(url)
        page_type = self._get_page_type_from_url(url)
        if filepath.exists() and self.season == datetime.now().year:
            if page_type == "liga":
                self._logger.info(
                    "Current Season: re-downloading <liga> page_type to \
                     check for new matchreports."
                )
                html = self._retrieve_html_from_server(url=url)
                self._cache_html_to_file(filepath=filepath, html=html)
        if not filepath.exists():
            html = self._retrieve_html_from_server(url=url)
            self._cache_html_to_file(filepath=filepath, html=html)
            if page_type == "spielbericht":
                page_id = self._get_page_id_from_url(url=url)
                self.new_matchreports_html.append((page_id, html))
        else:
            with open(filepath, encoding="utf-8") as file:
                content = file.read()
            self._logger.info(f"Reading HTML from {filepath}.")
            html = BeautifulSoup(content, "html.parser")
        return html

    def _get_page_type_from_url(self, url) -> str:
        """Get the page type from the URL.

        Args:
            url (str): The URL to extract the page type from.

        Returns:
            str: The page type, e.g., 'liga' or 'spielbericht'.
        """
        return url.split("/")[4]

    def _generate_path_from_url(self, url) -> Path:
        """Generate a file path from the URL for caching HTML.

        Args:
            url (str): The URL to generate the file path from.

        Returns:
            Path: The file path for caching the HTML content.
        """
        page_type = url.split("/")[4]
        page_id = url.split("/")[-2]
        filepath = self._RAW_HTML_PATH / f"{page_type}_{page_id}.html"
        return filepath

    def _get_urls(self, page_type: str, html: BeautifulSoup) -> list[str]:
        """Extract URLs from HTML content that match a specific page type.

        Args:
            page_type (str): The page type to filter URLs.
            html (BeautifulSoup): The HTML content to search within.

        Returns:
            list[str]: List of URLs matching the given page type.
        """
        pattern = re.compile(re.escape(f"{self._base_url}/{page_type}/anzeigen/"))
        a_tags = html.find_all("a", href=re.compile(pattern))
        # Using a set() to remove duplicates
        sorted_by_id = sorted(list({a_tag["href"] for a_tag in a_tags}))  # noqa: C414
        return sorted_by_id

    def scrape(self) -> list[tuple[int, BeautifulSoup]]:
        """Scrape data for match reports from the website and cache HTML content.

        Returns:
            list[tuple[int, BeautifulSoup]]: List of new match reports' IDs and HTML
                                             content, sorted by date.
        """
        for division_url in self.division_urls:
            division_html = self._get_html(url=division_url)
            matchreport_urls = self._get_urls(
                page_type="spielbericht", html=division_html
            )
            for matchreport_url in matchreport_urls:
                self._get_html(url=matchreport_url)
        new_matchreport_html_sorted_by_id = sorted(
            self.new_matchreports_html,
            key=lambda page_id_html: self._extract_date(page_id_html[1]),
        )

        return new_matchreport_html_sorted_by_id

    def _extract_date(self, html) -> datetime:
        """Extract the date from the HTML content.

        Args:
            html (BeautifulSoup): The HTML content to extract the date from.

        Raises:
            ValidationError: If no date is found in the HTML.

        Returns:
            datetime: The extracted date.
        """
        small = html.find("small").text.strip()
        if small:
            date_match = re.search(r"\d{2}.\d{2}.\d{4}", small)
            if date_match:
                return datetime.strptime(date_match.group(), "%d.%m.%Y")
        raise ValidationError("No 'Date' found in <small> tag.")
