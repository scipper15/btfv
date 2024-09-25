import scraper_main
from shared.logging.logging import main_logger


def main() -> None:
    main_logger.info("Starting application.")
    scraper_main.main()


if __name__ == "__main__":
    main()
