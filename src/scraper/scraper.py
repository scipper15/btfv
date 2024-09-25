from datetime import datetime
from logging import Logger

from bs4 import BeautifulSoup
import requests

from scraper.extractor import Extractor
from scraper.file_handler import FileHandler
from shared.config.settings import Settings


class Scraper:
    def __init__(
        self,
        logger: Logger,
        file_handler: FileHandler,
        extractor: Extractor,
    ) -> None:
        self._extractor = extractor
        self._logger = logger
        self._file_handler = file_handler

    def get_HTML(self, season: int, URL: str) -> BeautifulSoup | None:
        file_path = self._file_handler.generate_path_from_url(URL=URL)

        self._logger.debug(f"Checking file path: {file_path}")
        if not self._file_handler.exists(file_path):
            HTML = self._get_from_server(URL=URL)

            # cache the HTML
            self._file_handler.write_HTML(HTML=HTML, file_path=file_path)
            self._logger.debug(f"HTML written to {file_path}")
            return HTML
        else:
            if self._extractor is not None:
                page_type = self._extractor.extract_page_type_from_url(URL)
            if page_type in ["saison", "liga"]:
                # for the current season re-download HTML in case match reports updated
                if season != datetime.now().year:
                    return self._file_handler.read_HTML(file_path)
                else:
                    # cache the HTML
                    HTML = self._get_from_server(URL=URL)
                    self._file_handler.write_HTML(HTML=HTML, file_path=file_path)
                    return HTML

            self._logger.debug("Page type 'spielbericht': File already cached.")
            return None

    def _get_from_server(self, URL) -> BeautifulSoup:
        self._logger.info(f"HTML from server: {URL}")
        r = requests.get(URL)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")


class PlayerScraper:
    def __init__(
        self,
        logger: Logger,
        file_handler: FileHandler,
        settings: Settings,
    ) -> None:
        self._logger = logger
        self._file_handler = file_handler
        self._settings = settings

    def get_player_html(self, player_name: str) -> BeautifulSoup | None:
        path = self._file_handler.generate_path_for_player(player_name=player_name)
        if not self._file_handler.exists(path):
            self._logger.info("Retrieving additional player Information from DTFB:")
            search_url = self._settings.DTFB_URL_BASE
            data = {
                "filter": player_name,
                "veranstalterid": 6,  # value for "Bayerischer Tischfußballverband BTFV"
            }

            r = requests.post(search_url, data=data)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            # find the link to the player details page
            # m.b.: assuming first hit is the right one
            player_detail_link = soup.find(
                "a", href=lambda href: href and "task=spieler_details" in href
            )

            if player_detail_link is None:
                self._logger.warning(f"Player {player_name} not found")
                return None

            # Extract the relevant part of the URL
            player_detail_url: str = player_detail_link["href"]  # type: ignore
            parts = player_detail_url.split("&")
            full_player_url = f"https://dtfb.de{parts[0]}&{parts[1]}"
            print(f"Player details URL: {full_player_url}")

            # Now, request the player details page
            player_response = requests.get(full_player_url)
            player_response.raise_for_status()

            return BeautifulSoup(player_response.text, "html.parser")
        else:
            self._logger.info("Retrieving additional player Information from file:")
            return self._file_handler.read_HTML(path)
