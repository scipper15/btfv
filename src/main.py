import logging

from scraper.scraper import initial_scrape
from shared.config.settings import settings
from shared.logging.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Starting application.")
    new_match_reports = initial_scrape(logger=logger, settings=settings)


if __name__ == "__main__":
    main()
