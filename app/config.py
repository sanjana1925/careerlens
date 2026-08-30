from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./careerlens.db"

    jwt_secret_key: str = "change-this-to-a-random-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    gemini_api_key: str = ""

    # Dev default: any localhost/127.0.0.1 port (Vite's dev server runs on a
    # different port than the API). Override via CORS_ALLOW_ORIGIN_REGEX in
    # .env before deploying anywhere the frontend isn't served from localhost
    # — e.g. `^https://myapp\.example\.com$`.
    cors_allow_origin_regex: str = r"http://(localhost|127\.0\.0\.1):\d+"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
