import logging
from pathlib import Path

from scraper.extractor import Extractor
from scraper.scraper import initial_scrape
from shared.config.settings import settings
from shared.logging.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Starting application.")
    Path.unlink(settings.RAW_HTML_PATH / "spielbericht_12.html")
    new_match_reports = initial_scrape(logger=logger, settings=settings)
    if new_match_reports:
        keys = new_match_reports.keys()
        for key in keys:
            season = key
            break
        page_id = new_match_reports[season][0][0]
        html = new_match_reports[season][0][1]
        extractor = Extractor(
            logger=logger,
            settings=settings,
            season=season,
            page_id=page_id,
            matchday_data=html,
        )
        extractor.extact_matchreport()


if __name__ == "__main__":
    main()
