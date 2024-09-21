class Scraper:
    def __init__(self, settings, logger) -> None:
        self.settings = settings
        self.logger = logger
        logger.info(f"Hello from {Scraper.__name__}!")

    def scrape(self) -> None:
        pass


def main():
    pass


if __name__ == "__main__":
    main()
