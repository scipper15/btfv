from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env.dev", ".env.test", ".env.prod"))
    PYTHONDONTWRITEBYTECODE: bool = False
    PYTHONPATH: str = "./src"

    APPNAME: str = "btfv.tablesoccer.rocks"
    LOGGING_ENV: str = Field(default="dev")

    BASE_PATH: Path = Field(default=Path.cwd())
    RAW_HTML_PATH: Path = Field(default=Path.cwd() / "data" / "raw_html")
    PLAYER_HTML_PATH: Path = Field(default=Path.cwd() / "data" / "player_html")

    BTFV_URL_BASE: str = "https://btfv.de/sportdirector"

    @field_validator("RAW_HTML_PATH", mode="before")
    def convert_raw_html_path(cls, RAW_HTML_PATH):
        if isinstance(RAW_HTML_PATH, str):
            RAW_HTML_PATH = Path.cwd() / RAW_HTML_PATH
            Path.mkdir(RAW_HTML_PATH, exist_ok=True, parents=True)
            return RAW_HTML_PATH
        Path.mkdir(RAW_HTML_PATH, exist_ok=True, parents=True)
        return RAW_HTML_PATH

    @field_validator("PLAYER_HTML_PATH", mode="before")
    def convert_player_html_path(cls, PLAYER_HTML_PATH):
        if isinstance(PLAYER_HTML_PATH, str):
            PLAYER_HTML_PATH = Path.cwd() / PLAYER_HTML_PATH
            Path.mkdir(PLAYER_HTML_PATH, exist_ok=True, parents=True)
            return PLAYER_HTML_PATH
        Path.mkdir(PLAYER_HTML_PATH, exist_ok=True, parents=True)
        return PLAYER_HTML_PATH


settings = Settings()
