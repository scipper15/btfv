from pathlib import Path
from urllib.parse import quote

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env.dev", "../.env.test", "../.env.prod"),
        extra="allow",
    )
    """
    The `Settings` class manages configuration for the application.

    This class automatically:
        - Loads environment variables from `.env` files (supports multiple environments
          like `.env.dev`, `.env.test`, `.env.prod`).
        - Dynamically builds database connection strings (`SYNC_URL` and `ASYNC_URL`)
          by URL-encoding sensitive information like passwords.
        - Ensures that specific directories (e.g., asset directories) are created, and
          symlinks are set up for these directories to make the application more
          portable."""

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
        default=f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"
    )
    ASYNC_URL: str = Field(
        default=f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"
    )

    # web app
    FLASK_APP: str = Field(default="web_main.py")
    FLASK_RUN_HOST: str = Field(default="0.0.0.0")
    FLASK_SECRET_KEY: str = Field(default="your_secret_key")
    SERVER_NAME: str = Field(default="tablesoccer.rocks:5000")
    VIRTUAL_PORT: int = Field(default=80)
    VIRTUAL_HOST: str = Field(default="btfv.tablesoccer.rocks")
    LETSENCRYPT_HOST: str = Field(default="btfv.tablesoccer.rocks")
    LETSENCRYPT_EMAIL: str = Field(default="reinhard.eichhorn@gmail.com")

    ASSETS_PATH: Path = Field(default=Path.cwd() / "data" / "assets")

    @model_validator(mode="after")  # type: ignore
    def build_sync_url(cls, values: "Settings") -> "Settings":
        """Post-processes the settings to build the database connection URLs.

        It constructs the `SYNC_URL` and `ASYNC_URL` based on the PostgreSQL
        credentials from the environment variables, properly URL-encoding the
        password to handle any special characters.
        """
        user = values.POSTGRES_USER
        password = values.POSTGRES_PASSWORD
        host = values.POSTGRES_HOST
        db = values.POSTGRES_DB
        values.SYNC_URL = (
            f"postgresql+psycopg2://{user}:{quote(password)}@{host}:5432/{db}"
        )
        values.ASYNC_URL = (
            f"postgresql+asyncpg://{user}:{quote(password)}@{host}:5432/{db}"
        )
        return values

    @model_validator(mode="after")  # type: ignore
    def create_paths_and_symlinks(cls, values: "Settings") -> "Settings":
        """This validator runs after all fields have been populated.

        It ensures all directories exist and creates symlinks for association
        logos, player images, and assets.
        """
        # List of paths to create in the data directory
        paths_to_create = [
            values.MATCH_REPORT_HTML_PATH,
            values.ASSOCIATION_LOGOS_PATH,
            values.PLAYER_HTML_PATH,
            values.PLAYER_IMAGES_PATH,
            values.ASSETS_PATH,
        ]

        # Ensure all data paths are created
        for path in paths_to_create:
            path.mkdir(parents=True, exist_ok=True)

        # Symlink targets
        logos_target = values.STATIC_FOLDER / "logos"
        player_images_target = values.STATIC_FOLDER / "player_images"
        assets_target = values.STATIC_FOLDER / "assets"

        def create_symlink(target: Path, link: Path) -> None:
            if link.exists() and not link.is_symlink():
                link.symlink_to(target, target_is_directory=True)
                print(f"Symlink created: {target} -> {link}")

        # Create symlinks for logos, player images, and assets
        create_symlink(values.ASSOCIATION_LOGOS_PATH, logos_target)
        create_symlink(values.PLAYER_IMAGES_PATH, player_images_target)
        create_symlink(values.ASSETS_PATH, assets_target)

        return values


settings = Settings()
