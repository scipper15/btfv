import csv
import hashlib
from logging import Logger
from pathlib import Path
import re

from bs4 import BeautifulSoup
from requests import Response

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

    def append_to_csv(self, file_path: Path, data: dict | None = None):
        file_exists = file_path.exists()
        with open(file_path, mode="a+", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file, fieldnames=self._settings.DTFB_CSV_HEADER, delimiter=";"
            )
            if not file_exists:
                self._logger.info(f"{file_path} created")
                writer.writeheader()
            if data:
                self._logger.info(f"Written player data to {file_path}")
                writer.writerow(data)

    def write_image(self, response: Response, player_name: str) -> None:
        # Save the image to the output directory
        file_name = f"{self.generate_hash(string=player_name)}.jpg"
        image_file_path = self._settings.PLAYER_HTML_PATH / file_name
        with open(image_file_path, "wb") as file:
            file.write(response.content)

        self._logger.info(f"Image saved to: {image_file_path}")

    def read_csv_as_dict(self, file_path: Path) -> list[dict[str, str]]:
        if not file_path.exists():
            self.append_to_csv(file_path=file_path)
        rows = []
        with open(file_path, mode="r", encoding="utf-8") as file:
            csv_reader = csv.DictReader(file, delimiter=";")
            for row in csv_reader:
                rows.append(row)
        return rows

    def generate_path_from_url(self, URL: str) -> Path:
        page_id = URL.split("/")[-2]
        page_type = URL.split("/")[4]
        return self._settings.RAW_HTML_PATH / f"{page_type}_{page_id}.html"

    def generate_path_for_player(self, player_name: str) -> Path:
        player_hash = self.generate_hash(string=player_name)
        directory_path = Path(f"{self._settings.PLAYER_HTML_PATH}/{player_hash}.html")
        return directory_path

    def generate_path_for_player_image(self, player_name: str) -> Path:
        player_hash = self.generate_hash(string=player_name)
        directory_path = Path(f"{self._settings.PLAYER_HTML_PATH}/{player_hash}.jpg")
        return directory_path

    def generate_hash(self, string: str) -> str:
        # Normalize player name by stripping extra spaces and converting to lowercase
        normalized_name = string.strip().lower()
        hash_object = hashlib.sha256(normalized_name.encode())
        player_hash = hash_object.hexdigest()
        # Using first 8 characters of hash
        return player_hash[:8]

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
            raise ValueError("No number found in the file name.")
