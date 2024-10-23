from datetime import datetime
from logging import Logger
import re
from typing import cast

from bs4 import BeautifulSoup
import requests

from scraper.custom_errors import ElementNotFound
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

    def _get_from_server(self, URL: str) -> BeautifulSoup:
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

    def get_player_html(self, player_name: str) -> BeautifulSoup | int | None:
        """Returns html (from url or if cached from file) or DTFB_from_id or None."""
        path = self._file_handler.generate_path_for_player_html(player_name=player_name)
        if not self._file_handler.exists(path):
            # file does not exist, but player information might not be available online
            already_tried = self._already_tried(player_name=player_name)
            if isinstance(already_tried, int) and not isinstance(already_tried, bool):
                DTFB_from_id: int = already_tried
                return DTFB_from_id
            elif already_tried:
                # unsuccessfully tried before
                self._logger.info(
                    "Unsuccessfully tried before: Giving up, no further "
                    "player information available online."
                )
                return None
            else:
                # try to scrape the player
                self._logger.info("Retrieving additional player Information from DTFB:")
                search_url = self._settings.DTFB_URL_BASE
                data = {
                    "filter": player_name,
                    # value for "Bayerischer Tischfußballverband BTFV"
                    "veranstalterid": 6,
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
                    self._logger.warning(
                        f"Player {player_name} not found, writing to csv"
                    )
                    self._file_handler.append_to_csv(
                        file_path=self._settings.DTFB_CSV_FILE,
                        data={
                            "player_hash": self._file_handler.generate_hash(
                                player_name
                            ),
                            "DTFB_from_id": "",
                            "player_name": player_name,
                        },
                    )
                    return None

                # Extract the relevant part of the URL
                player_detail_url: str = cast(str, player_detail_link["href"])  # type: ignore
                parts = player_detail_url.split("&")
                match = re.search(r"(\d)+", parts[1])
                if match:
                    DTFB_from_id = int(match.group())

                    full_player_url = f"https://dtfb.de{parts[0]}&{parts[1]}"
                    self._logger.info(f"Player details URL: {full_player_url}")

                    # Now, request the player details page
                    player_response = requests.get(full_player_url)
                    player_response.raise_for_status()
                    # cache to disk
                    if player_response:
                        self._file_handler.write_HTML(
                            BeautifulSoup(player_response.text, "html.parser"),
                            path,
                        )
                        self._file_handler.append_to_csv(
                            file_path=self._settings.DTFB_CSV_FILE,
                            data={
                                "player_hash": self._file_handler.generate_hash(
                                    player_name
                                ),
                                "DTFB_from_id": cast(str, DTFB_from_id),
                                "player_name": player_name,
                            },
                        )
                        html = BeautifulSoup(player_response.text, "html.parser")
                        # download image
                        self._find_and_download_image(
                            html=html, player_name=player_name
                        )
                        return html
                raise ElementNotFound("DTFB_from_id not found")
        else:
            # get data from file
            self._logger.info("Retrieving additional player Information from file:")
            return self._file_handler.read_HTML(path)

    def _already_tried(self, player_name: str) -> bool | int:
        player_data = self._file_handler.read_csv_as_dict(
            file_path=self._settings.DTFB_CSV_FILE
        )
        player_hash = self._file_handler.generate_hash(string=player_name)
        # look up player hash / player name and if a DTFB ID already has been cached
        for row in player_data:
            if row["player_hash"] == player_hash:
                # lookup in csv: means already tried to scrape this particular player
                if row["DTFB_from_id"]:
                    # successfully tried to retrieve player before
                    return int(row["DTFB_from_id"])
                else:
                    # unsuccessfully tried to retrieve player before
                    return True
        # never tried to look up player online
        return False

    def _find_and_download_image(self, html: BeautifulSoup, player_name: str) -> None:
        # Find the URL with "spieler" and ending in ".jpg"
        pattern = re.compile(r'https://[^"]*spieler[^"]*\.jpg|png')
        match = html.find("img", {"src": pattern})

        if match and "src" in match.attrs:  # type: ignore
            image_url = match["src"]  # type: ignore
            self._logger.info(f"Found image URL: {image_url}")
            if (
                image_url
                == "https://dtfb.de/images/sportsmanager/spieler/ImT1661962960W180H240.png"
            ):
                self._logger.info("Only dummy image, not saving")
                return
            response = requests.get(image_url)  # type: ignore
            response.raise_for_status()
            self._file_handler.write_image(
                response=response, name=player_name, page_type="player"
            )

        else:
            self._logger.info("No matching image URL found in HTML.")
            return
