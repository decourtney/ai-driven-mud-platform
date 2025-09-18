from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_server_url: str = "http://localhost:8001"
    wait_for_models: bool = True
    auto_load_models: bool = False
    dev_mode: bool = False
    auth_secret: str  # required

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
