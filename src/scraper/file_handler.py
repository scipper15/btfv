import hashlib
from logging import Logger
from pathlib import Path
import re

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

    def generate_path_for_player(self, player_name: str) -> Path:
        # Normalize player name by stripping extra spaces and converting to lowercase
        normalized_name = player_name.strip().lower()

        hash_object = hashlib.sha256(normalized_name.encode())
        player_hash = hash_object.hexdigest()

        # Using first 8 characters of hash
        directory_path = Path(
            f"{self._settings.PLAYER_HTML_PATH}/{player_hash[:8]}.html"
        )

        return directory_path

    def exists(self, path: Path) -> bool:
        return True if path.exists() else False

    def get_all_cached_match_reports(self) -> list[Path]:
        path = self._settings.RAW_HTML_PATH
        return list(path.glob("spielbericht_*.html"))

    def extract_page_id_from_path(self, file_path: Path) -> int:
        # Extract the file name from the complete path
        file_name = file_path.name
        # Use a regular expression to find the number in the file name
        match = re.search(r"\d+", file_name)
        if match:
            return int(match.group())
        else:
            raise ValueError("No number found in the file name")
