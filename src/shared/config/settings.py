from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.dev", ".env.test", ".env.prod"),
        extra="allow",
    )

    PYTHONDONTWRITEBYTECODE: bool = False
    PYTHONPATH: str = "./src"
    LOGGING_ENV: str = Field(default="dev")

    APPNAME: str = "btfv.tablesoccer.rocks"
    BASE_PATH: Path = Field(default=Path.cwd())
    STATIC_FOLDER: Path = Field(default=Path.cwd() / "src" / "web_app" / "static")

    # scraper
    SCRAPER_INTERVAL: int = Field(default=86400)
    MATCH_REPORT_HTML_PATH: Path = Field(
        default=Path.cwd() / "data" / "match_report_html"
    )
    ASSOCIATION_LOGOS_PATH: Path = Field(
        default=Path.cwd() / "data" / "association_logos"
    )
    PLAYER_HTML_PATH: Path = Field(default=Path.cwd() / "data" / "player_html")
    PLAYER_IMAGES_PATH: Path = Field(default=Path.cwd() / "data" / "player_images")

    DTFB_CSV_FILE: Path = Field(default=Path.cwd() / "data" / "dtfb.csv")

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
    POSTGRES_HOST: str = Field(default="db")
    POSTGRES_DB: str = Field(default="db")
    SYNC_URL: str = Field(
        default="postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"
    )
    ASYNC_URL: str = Field(
        default="postgresql+asyncpg://{POSTGRES_USER}:${POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"
    )

    @model_validator(mode="after")  # type: ignore
    def create_paths_and_symlinks(cls, values: "Settings") -> "Settings":
        """This validator runs after all fields have been populated.

        It ensures all directories exist and creates symlinks for association
        logos and player images.
        """
        # List of paths to create in the data directory
        paths_to_create = [
            values.MATCH_REPORT_HTML_PATH,
            values.ASSOCIATION_LOGOS_PATH,
            values.PLAYER_HTML_PATH,
            values.PLAYER_IMAGES_PATH,
        ]

        # Ensure all data paths are created
        for path in paths_to_create:
            path.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {path}")

        logos_target = values.STATIC_FOLDER / "logos"
        player_images_target = values.STATIC_FOLDER / "player_images"

        # Symlinks for logos and images to be used in flask app
        if not logos_target.is_symlink():
            logos_target.symlink_to(values.ASSOCIATION_LOGOS_PATH, True)
            print(f"Symlink created: {values.ASSOCIATION_LOGOS_PATH} -> {logos_target}")
        if not player_images_target.is_symlink():
            player_images_target.symlink_to(values.PLAYER_IMAGES_PATH, True)
            print(
                f"Symlink created: {values.PLAYER_IMAGES_PATH}"
                f" -> {player_images_target}"
            )

        return values


settings = Settings()
