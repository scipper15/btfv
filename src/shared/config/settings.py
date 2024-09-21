from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env.dev", ".env.test", ".env.prod"))
    PYTHONDONTWRITEBYTECODE: bool = False
    PYTHONPATH: str = "./src"
    APPNAME: str = "btfv.tablesoccer.rocks"


settings = Settings()
