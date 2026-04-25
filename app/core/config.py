# app/core/config.py
from pydantic import computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    

    postgres_user: str = "postgres"
    postgres_password: str = "password"
    postgres_db: str = "foodstore_db"
    postgres_host: str = "localhost"
    postgres_port: int = 5433

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        
        "extra": "ignore",
    }


settings = Settings()
