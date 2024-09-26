from bs4 import BeautifulSoup

from scraper.db_populator import DbPopulator
from scraper.extractor import Extractor
from scraper.file_handler import FileHandler
from scraper.scraper import PlayerScraper, Scraper
from scraper.scraping_manager import ScrapingManager
from shared.config.settings import settings
from shared.database.database import Database
from shared.logging.logging import (
    extractor_logger,
    file_handler_logger,
    populator_logger,
    scraper_logger,
    scraping_manager_logger,
)


def main() -> None:
    file_handler = FileHandler(logger=file_handler_logger, settings=settings)
    database = Database(logger=populator_logger, settings=settings)
    extractor = Extractor(logger=extractor_logger, settings=settings)
    scraper = Scraper(
        logger=scraper_logger, file_handler=file_handler, extractor=extractor
    )
    player_scraper = PlayerScraper(
        logger=scraper_logger,
        settings=settings,
        file_handler=file_handler,
    )
    db_populator = DbPopulator(
        logger=populator_logger,
        settings=settings,
        extractor=extractor,
        database=database,
    )
    scraping_manager = ScrapingManager(
        logger=scraping_manager_logger,
        settings=settings,
        scraper=scraper,
        player_scraper=player_scraper,
        extractor=extractor,
        db_populator=db_populator,
        database=database,
    )
    with open(
        "/home/menn/btfv/data/raw_html/spielbericht_8.html", encoding="utf-8"
    ) as file:
        html = BeautifulSoup(file.read(), "html.parser")
    scraping_manager.populate_db(html=html, season=2012, page_id=8)


if __name__ == "__main__":
    main()
