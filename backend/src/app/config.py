from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

import boto3


class ConfigError(ValueError):
    """Raised when required backend configuration is missing."""


@dataclass(slots=True)
class Settings:
    app_env: str
    log_level: str
    aws_region: str
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str | None
    db_password_ssm_param: str | None

    def resolve_db_password(self) -> str:
        if self.db_password:
            return self.db_password
        if not self.db_password_ssm_param:
            raise ConfigError("Set DB_PASSWORD or DB_PASSWORD_SSM_PARAM.")

        ssm_client = boto3.client("ssm", region_name=self.aws_region)
        parameter = ssm_client.get_parameter(
            Name=self.db_password_ssm_param,
            WithDecryption=True,
        )
        return str(parameter["Parameter"]["Value"])

    def db_dsn(self) -> str:
        password = self.resolve_db_password()
        return (
            f"host={self.db_host} "
            f"port={self.db_port} "
            f"dbname={self.db_name} "
            f"user={self.db_user} "
            f"password={password}"
        )


def _env(name: str, default: str | None = None, *, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value or ""


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    return Settings(
        app_env=_env("APP_ENV", "dev"),
        log_level=_env("LOG_LEVEL", "INFO"),
        aws_region=_env("AWS_REGION", "eu-north-1"),
        db_host=_env("DB_HOST", required=True),
        db_port=int(_env("DB_PORT", "5432")),
        db_name=_env("DB_NAME", required=True),
        db_user=_env("DB_USER", required=True),
        db_password=os.getenv("DB_PASSWORD"),
        db_password_ssm_param=os.getenv("DB_PASSWORD_SSM_PARAM"),
    )
