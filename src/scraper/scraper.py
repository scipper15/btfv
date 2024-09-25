from datetime import datetime
from logging import Logger

from bs4 import BeautifulSoup
import requests

from scraper.extractor import Extractor
from scraper.file_handler import FileHandler


class Scraper:
    def __init__(
        self,
        logger: Logger,
        file_handler: FileHandler,
        extractor: Extractor,
    ) -> None:
        self._logger = logger
        self._file_handler = file_handler
        self._extractor = extractor

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
