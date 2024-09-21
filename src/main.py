from scraper.scraper import Scraper
from shared.config.settings import settings


def main():
    scraper = Scraper(settings=settings)
    scraper.scrape()


if __name__ == "__main__":
    main()
