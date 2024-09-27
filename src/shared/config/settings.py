from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env.dev", ".env.test", ".env.prod"))

    PYTHONDONTWRITEBYTECODE: bool = False
    PYTHONPATH: str = "./src"
    LOGGING_ENV: str = Field(default="dev")

    APPNAME: str = "btfv.tablesoccer.rocks"

    # scraper
    SCRAPER_INTERVAL: int = Field(default=86400)
    BASE_PATH: Path = Field(default=Path.cwd())
    RAW_HTML_PATH: Path = Field(default=Path.cwd() / "data" / "raw_html")
    PLAYER_HTML_PATH: Path = Field(default=Path.cwd() / "data" / "player_html")
    PLAYER_IMAGES_PATH: Path = Field(default=Path.cwd() / "data" / "player_html")
    DTFB_CSV_FILE: Path = Field(default=Path.cwd() / "data" / "dtfb.csv")

    BTFV_CSV_HEADER: list[str] = ["BTFV_from_id"]
    DTFB_CSV_HEADER: list[str] = [
        "player_hash",
        "DTFB_from_id",
        "player_name",
    ]

    BTFV_URL_BASE: str = "https://btfv.de/sportdirector"
    DTFB_URL_BASE: str = "https://dtfb.de/wettbewerbe/turnierserie/spielersuche"

    # database
    POSTGRES_USER: str = Field(default="docker")
    POSTGRES_PASSWORD: str = Field(default="docker")
    POSTGRES_DB: str = Field(default="db")
    SYNC_URL: str = Field(
        default="postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}"
    )
    ASYNC_URL: str = Field(
        default="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}"
    )

    @field_validator("RAW_HTML_PATH", mode="before")
    def convert_raw_html_path(cls, RAW_HTML_PATH):
        if isinstance(RAW_HTML_PATH, str):
            RAW_HTML_PATH = Path.cwd() / RAW_HTML_PATH
            Path.mkdir(RAW_HTML_PATH, exist_ok=True, parents=True)
            return RAW_HTML_PATH
        Path.mkdir(RAW_HTML_PATH, exist_ok=True, parents=True)
        return RAW_HTML_PATH

    @field_validator(
        "RAW_HTML_PATH", "PLAYER_HTML_PATH", "PLAYER_IMAGES_PATH", mode="before"
    )
    def convert_paths(cls, path_value):
        """Convert string paths to Path objects.

        Creates the directories if they don't exist.
        """
        if isinstance(path_value, str):
            path_value = Path.cwd() / path_value

        Path.mkdir(path_value, exist_ok=True, parents=True)
        return path_value


settings = Settings()
