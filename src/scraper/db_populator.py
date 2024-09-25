from logging import Logger

from shared.config.settings import Settings


class DbPopulator:
    def __init__(self, logger: Logger, settings: Settings) -> None:
        self._logger = logger
        self._settings = settings
