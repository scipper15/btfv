import logging

from scraper.scraper import Scraper
from shared.config.settings import settings
from shared.logging.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Starting application.")
    season = 2015
    scraper = Scraper(settings=settings, logger=logger, season=season)
    new_match_reports = scraper.scrape()
    if new_match_reports:
        logger.info(f"{len(new_match_reports)} NEW match report(s) found.")
    else:
        logger.info("No new match reports found.")


if __name__ == "__main__":
    main()
