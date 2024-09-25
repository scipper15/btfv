from scraper.extractor import Extractor
from scraper.file_handler import FileHandler
from scraper.scraper import Scraper
from scraper.scraping_manager import ScrapingManager
from shared.config.settings import settings
from shared.logging.logging import (
    extractor_logger,
    file_handler_logger,
    scraper_logger,
    scraping_manager_logger,
)


def main() -> None:
    file_handler = FileHandler(logger=file_handler_logger, settings=settings)
    extractor = Extractor(logger=extractor_logger, settings=settings)
    scraper = Scraper(
        logger=scraper_logger, file_handler=file_handler, extractor=extractor
    )
    scraping_manager = ScrapingManager(
        logger=scraping_manager_logger,
        settings=settings,
        scraper=scraper,
        extractor=extractor,
    )
    scraping_manager.process_seasons()


if __name__ == "__main__":
    main()
