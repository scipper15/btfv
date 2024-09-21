import logging

from scraper.scraper import Scraper
from shared.config.settings import settings
from shared.logging.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Starting application.")
    scraper = Scraper(settings=settings, logger=logger)
    scraper.scrape()


if __name__ == "__main__":
    main()
