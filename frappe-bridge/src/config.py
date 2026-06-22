from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Frappe
    frappe_base_url: str = "http://frappe:8080"
    frappe_api_key: str = ""
    frappe_api_secret: str = ""

    # Core
    core_base_url: str = "http://core:8000"
    core_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
