from scraper.extractor import Extractor
from scraper.scraper import Scraper
from shared.config.settings import settings
from shared.logging.logging import extractor_logger, main_logger, scraper_logger


def main() -> None:
    main_logger.info("Starting application.")
    scraper = Scraper(
        logger=scraper_logger,
        settings=settings,
        season=2012,
    )
    new_match_reports = scraper.scrape()
    for season, match_tuple_list in new_match_reports.items():
        for page_id, match_report in match_tuple_list:
            extractor = Extractor(
                logger=extractor_logger,
                settings=settings,
                season=season,
                page_id=page_id,
                html=match_report,
            )
            extractor.extract_matchreport()


if __name__ == "__main__":
    main()
