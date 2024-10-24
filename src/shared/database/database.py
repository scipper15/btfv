from typing import Any, Self

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from shared.config.settings import Settings
from shared.database.models import BaseModel


class Database:
    _instance = None
    _initialized = False

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, settings: Settings) -> None:
        if not self._initialized:
            self._settings = settings

            # Sync engine and sessionmaker
            self.sync_engine = create_engine(self._settings.SYNC_URL)
            self.SyncSessionLocal = scoped_session(
                sessionmaker(autocommit=False, autoflush=False, bind=self.sync_engine)
            )

            # Async engine and sessionmaker
            self.async_engine = create_async_engine(
                self._settings.ASYNC_URL, future=True
            )
            self.AsyncSessionLocal = async_sessionmaker(
                self.async_engine, expire_on_commit=False, class_=AsyncSession
            )

            # Mark as initialized to avoid repeating the setup
            self._initialized = True

    def init_flask_app(self, app: Flask) -> None:
        @app.teardown_appcontext
        def shutdown_session(exception: BaseException | None = None) -> None:
            self.SyncSessionLocal.remove()

    def init_db(self) -> None:
        BaseModel.metadata.drop_all(self.sync_engine)
        BaseModel.metadata.create_all(self.sync_engine)

    def get_sync_session(self) -> Session:
        """Provide a transactional scope around a series of operations for sync."""
        return self.SyncSessionLocal()

    async def get_async_session(self) -> async_sessionmaker[AsyncSession]:
        """Provide a transactional scope around a series of operations for async."""
        return self.AsyncSessionLocal

    # Close async engine (useful for shutdown)
    async def close_async(self) -> None:
        await self.async_engine.dispose()

    @classmethod
    def instance(cls, settings: Settings) -> "Database":
        if cls._instance is None:
            cls._instance = cls(settings)
        return cls._instance
