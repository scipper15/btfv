import typing

if typing.TYPE_CHECKING:
    from logging import Logger

    from shared.config.settings import Settings


class Scraper:
    def __init__(self, settings: "Settings", logger: "Logger") -> None:
        self.settings = settings
        self.logger = logger
        self.RAW_HTML_PATH = self.settings.RAW_HTML_PATH
        logger.info(f"Hello from {Scraper.__name__}!")

    def scrape(self) -> None:
        pass


def main():
    pass


if __name__ == "__main__":
    main()
