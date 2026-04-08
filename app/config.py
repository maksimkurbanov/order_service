from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


load_dotenv()


class Settings(BaseSettings):
    @field_validator("POSTGRES_CONNECTION_STRING", mode="before")
    @classmethod
    def build_connection_string(cls, v):
        return v.replace("postgres://", "postgresql+asyncpg://")

    POSTGRES_CONNECTION_STRING: str
    POSTGRES_HOST: str
    POSTGRES_USER: str = Field(..., alias="POSTGRES_USERNAME")
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = Field(..., alias="POSTGRES_DATABASE_NAME")
    POSTGRES_PORT: int

    SERVER_HOST: str
    SERVER_PORT: int

    LMS_API_KEY: str
    CAPASHINO_URL: str
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_TOPIC: str
    SENTRY_DSN: str

    OUTBOX_MAX_RETRIES: int = 3
    OUTBOX_EVENTS_LIFESPAN_HOURS: int = 48
    IDEMPOTENCY_KEY_LIFESPAN_HOURS: int = 48

    CALLBACK_URL: str
    OUTBOX_MAX_RETRIES: int


settings = Settings()
