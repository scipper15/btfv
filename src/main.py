from shared.logging.logging import main_logger
from web_app.main import app


def main() -> None:
    main_logger.info("Starting application.")
    # scraper_main.main()
    app.run(debug=True)
    exit()


if __name__ == "__main__":
    main()
