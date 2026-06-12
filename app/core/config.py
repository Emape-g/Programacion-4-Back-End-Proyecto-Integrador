import json

from pydantic import computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    postgres_user: str = "postgres"
    postgres_password: str = "password"
    postgres_db: str = "foodstore_db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    jwt_secret_key: str = "changeme-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    cors_origins: str = '["http://localhost:5173"]'

    mp_access_token: str = "TEST-xxxx"
    mp_public_key: str = "TEST-xxxx"
    mp_notification_url: str = ""

    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return json.loads(self.cors_origins)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
