from logging import Logger

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from shared.config.settings import Settings
from shared.database.models import BaseModel


class Database:
    def __init__(self, logger: Logger, settings: Settings) -> None:
        self._settings = settings
        self._logger = logger

        self._logger.info(f"Using sync engine: {self._settings.SYNC_URL}")
        self._logger.info(f"Using async engine: {self._settings.ASYNC_URL}")

        # Sync engine and sessionmaker
        self.sync_engine = create_engine(self._settings.SYNC_URL)
        self.SyncSessionLocal = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=self.sync_engine)
        )

        # Async engine and sessionmaker
        self.async_engine = create_async_engine(self._settings.ASYNC_URL, future=True)
        self.AsyncSessionLocal = async_sessionmaker(
            self.async_engine, expire_on_commit=False, class_=AsyncSession
        )

    def init_db(self):
        BaseModel.metadata.drop_all(self.sync_engine)
        BaseModel.metadata.create_all(self.sync_engine)

    def get_sync_session(self) -> Session:
        """Provide a transactional scope around a series of operations for sync."""
        return self.SyncSessionLocal()

    async def get_async_session(self) -> async_sessionmaker[AsyncSession]:
        """Provide a transactional scope around a series of operations for async."""
        AsyncSessionLocal = async_sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        return AsyncSessionLocal

    # Close sync engine (useful for shutdown)
    def close_sync(self):
        self.sync_engine.dispose()

    # Close async engine (useful for shutdown)
    async def close_async(self):
        await self.async_engine.dispose()
