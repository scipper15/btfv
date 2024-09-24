from logging import Logger
from pathlib import Path

from bs4 import BeautifulSoup

from shared.config.settings import Settings


class FileHandler:
    def __init__(self, logger: Logger, settings: Settings) -> None:
        self._logger = logger
        self._settings = settings

    def write_HTML(self, HTML: BeautifulSoup, file_path: Path) -> None:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(HTML.prettify())
        self._logger.info(f"HTML written to {file_path}")

    def read_HTML(self, file_path: Path) -> BeautifulSoup:
        self._logger.info(f"Reading HTML from {file_path}")
        with open(file_path, encoding="utf-8") as file:
            content = file.read()
        return BeautifulSoup(content, "html.parser")

    def generate_path_from_url(self, URL: str) -> Path:
        page_id = URL.split("/")[-2]
        page_type = URL.split("/")[4]
        return self._settings.RAW_HTML_PATH / f"{page_type}_{page_id}.html"

    def exists(self, path: Path) -> bool:
        return True if path.exists() else False
