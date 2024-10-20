from logging import Logger

from sqlalchemy.orm import Session

from shared.config.settings import Settings, settings
from shared.database.database import Database
from shared.logging.logging import web_app_logger


def get_logger() -> Logger:
    return web_app_logger


def get_settings() -> Settings:
    return settings


def get_db_session() -> Session:
    logger = get_logger()
    settings = get_settings()
    database = Database(logger, settings)
    return database.get_sync_session()
