import logging.config
import os
from pathlib import Path

import yaml

from shared.config.settings import settings


def setup_logging(default_level=logging.INFO):
    """Setup logging configuration based on the environment variable LOGGING_ENV.

    Default level is INFO if no environment is specified.
    """
    env = settings.LOGGING_ENV

    config_file = Path(__file__).parent / f"logging_{env}.yaml"

    if os.path.exists(config_file):
        print(f"Using config_file {config_file}")
        with open(config_file, "r") as f:
            config = yaml.safe_load(f.read())
            logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)
        logging.warning(
            f"Logging configuration file for {env} not found, using basic config."
        )


setup_logging()

main_logger = logging.getLogger("main")
file_handler_logger = logging.getLogger("filehandler")
scraper_logger = logging.getLogger("scraper")
extractor_logger = logging.getLogger("extractor")
populator_logger = logging.getLogger("populator")
database_logger = logging.getLogger("database")
skill_calc_logger = logging.getLogger("skillcalc")
scraping_manager_logger = logging.getLogger("scrapingmanager")
