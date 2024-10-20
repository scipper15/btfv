import scraper_main
from shared.logging.logging import main_logger
from web_app.main import app


def main() -> None:
    main_logger.info("Starting application.")
    app.run(debug=True)
    exit()
    scraper_main.main()


if __name__ == "__main__":
    main()
