import logging

from scraper.scraper import Scraper
from shared.config.settings import settings
from shared.logging.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Starting application.")
    season = 3000
    scraper = Scraper(settings=settings, logger=logger, season=season)
    scraper.scrape()


if __name__ == "__main__":
    main()
