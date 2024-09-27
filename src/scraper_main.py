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
    # scraping_manager.process_seasons()
    # scraping_manager.populate_with_all_available_cached_data()
    scraping_manager.populate_by_page_id()
    # scraping_manager.get_all_player_html()


if __name__ == "__main__":
    main()
