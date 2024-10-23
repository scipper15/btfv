import time

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


def run_scraper() -> None:
    file_handler = FileHandler(logger=file_handler_logger, settings=settings)
    database = Database.instance(settings=settings)
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
        filehandler=file_handler,
    )
    scraping_manager = ScrapingManager(
        logger=scraping_manager_logger,
        settings=settings,
        scraper=scraper,
        player_scraper=player_scraper,
        extractor=extractor,
        db_populator=db_populator,
        database=database,
        file_handler=file_handler,
    )
    scraping_manager.process_seasons()


def main() -> None:
    interval = (
        settings.SCRAPER_INTERVAL
    )  # Retrieve the interval from the environment variable
    while True:
        try:
            run_scraper()
            print(
                "Scraper run completed."
                f"Waiting for {interval} seconds before the next run."
            )
        except Exception as e:
            print(f"Error occurred during scraper run: {e}")
        time.sleep(interval)


if __name__ == "__main__":
    main()
