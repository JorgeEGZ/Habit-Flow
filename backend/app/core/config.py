from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Reserved weak values that must never be used in non-development environments.
# `change_this_later` was the previous default and shipped to production by
# accident at least once; explicit deny-list prevents the recurrence.
_DEFAULT_SECRET_MARKERS = frozenset({"change_this_later", "changeme", "secret"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "HabitFlow API"
    app_version: str = "1.0.0"
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    database_url: str = Field(
        default="postgresql+asyncpg://habitflow:habitflow@localhost:5432/habitflow",
        description="SQLAlchemy async database URL.",
    )

    secret_key: str = Field(
        default="change_this_later",
        description=(
            "HMAC seed used to derive access- and refresh-token signing keys. "
            "Must be overridden outside development."
        ),
    )
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    cors_methods: list[str] = Field(
        default_factory=lambda: ["GET", "POST", "PATCH", "DELETE"]
    )
    cors_headers: list[str] = Field(
        default_factory=lambda: ["Authorization", "Content-Type"]
    )

    # ---------- validators ----------

    @field_validator("secret_key")
    @classmethod
    def _normalize_secret_key(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("SECRET_KEY must not be empty.")
        return value

    @model_validator(mode="after")
    def _enforce_secret_strength_in_non_dev(self) -> "Settings":
        if self.environment == "development":
            return self
        # Outside development, the secret must be a real value: not a known
        # placeholder, and at least 32 bytes of entropy. 32 bytes of base64
        # (43 chars) is the minimum sane HS256 key length.
        if self.secret_key.lower() in _DEFAULT_SECRET_MARKERS:
            raise ValueError(
                "SECRET_KEY is set to a placeholder value. Override it before "
                f"running in environment={self.environment!r}."
            )
        if len(self.secret_key.encode("utf-8")) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 bytes in non-development "
                "environments. Generate one with `python -c 'import secrets; "
                "print(secrets.token_urlsafe(32))'`."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
