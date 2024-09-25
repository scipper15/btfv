from logging import Logger

from sqlalchemy import create_engine

from shared.config.settings import Settings
from shared.database.models import BaseModel


class Database:
    def __init__(self, logger: Logger, settings: Settings) -> None:
        self._settings = settings
        self._logger = logger
        self._logger.info(f"Using engine (sync): {self._settings.SYNC_URL}")
        self._logger.info(f"Using engine (async): {self._settings.ASYNC_URL}")
        self.sync_engine = create_engine(self._settings.SYNC_URL)
        self.async_engine = create_engine(self._settings.ASYNC_URL)

    def init_db(self):
        BaseModel.metadata.create_all(self.sync_engine)
