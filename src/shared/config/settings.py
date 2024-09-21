from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env.dev", ".env.test", ".env.prod"))
    PYTHONDONTWRITEBYTECODE: bool = False
    PYTHONPATH: str = "./src"

    APPNAME: str = "btfv.tablesoccer.rocks"

    RAW_HTML_PATH: Path = Field(default=Path.cwd() / "data" / "raw_html")

    @field_validator("RAW_HTML_PATH", mode="before")
    def convert_raw_html_path(cls, RAW_HTML_PATH):
        if isinstance(RAW_HTML_PATH, str):
            RAW_HTML_PATH = Path.cwd() / RAW_HTML_PATH
            Path.mkdir(RAW_HTML_PATH, exist_ok=True, parents=True)
            return RAW_HTML_PATH
        Path.mkdir(RAW_HTML_PATH, exist_ok=True, parents=True)
        return RAW_HTML_PATH


settings = Settings()
