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
    notification_email_delivery_enabled: bool
    notification_email_sender: str
    notification_email_smtp_host: str
    notification_email_smtp_port: int
    notification_email_smtp_username_ssm_param: str | None
    notification_email_smtp_password_ssm_param: str | None
    notification_email_batch_size: int
    notification_email_max_attempts: int

    def resolve_db_password(self) -> str:
        if self.db_password:
            return self.db_password
        if not self.db_password_ssm_param:
            raise ConfigError("Set DB_PASSWORD or DB_PASSWORD_SSM_PARAM.")

        return self._resolve_ssm_parameter(self.db_password_ssm_param)

    def resolve_notification_email_smtp_credentials(self) -> tuple[str, str]:
        if (
            not self.notification_email_smtp_username_ssm_param
            or not self.notification_email_smtp_password_ssm_param
        ):
            raise ConfigError(
                "Set NOTIFICATION_EMAIL_SMTP_USERNAME_SSM_PARAM and "
                "NOTIFICATION_EMAIL_SMTP_PASSWORD_SSM_PARAM."
            )

        ssm_client = boto3.client("ssm", region_name=self.aws_region)
        return (
            _resolve_ssm_parameter(
                ssm_client,
                self.notification_email_smtp_username_ssm_param,
            ),
            _resolve_ssm_parameter(
                ssm_client,
                self.notification_email_smtp_password_ssm_param,
            ),
        )

    def _resolve_ssm_parameter(self, name: str) -> str:
        ssm_client = boto3.client("ssm", region_name=self.aws_region)
        return _resolve_ssm_parameter(ssm_client, name)

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


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _resolve_ssm_parameter(ssm_client: object, name: str) -> str:
    parameter = ssm_client.get_parameter(Name=name, WithDecryption=True)
    return str(parameter["Parameter"]["Value"])


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    aws_region = _env("AWS_REGION", "eu-north-1")
    return Settings(
        app_env=_env("APP_ENV", "dev"),
        log_level=_env("LOG_LEVEL", "INFO"),
        aws_region=aws_region,
        db_host=_env("DB_HOST", required=True),
        db_port=int(_env("DB_PORT", "5432")),
        db_name=_env("DB_NAME", required=True),
        db_user=_env("DB_USER", required=True),
        db_password=os.getenv("DB_PASSWORD"),
        db_password_ssm_param=os.getenv("DB_PASSWORD_SSM_PARAM"),
        notification_email_delivery_enabled=_env_bool(
            "NOTIFICATION_EMAIL_DELIVERY_ENABLED",
            False,
        ),
        notification_email_sender=_env("NOTIFICATION_EMAIL_SENDER", ""),
        notification_email_smtp_host=_env(
            "NOTIFICATION_EMAIL_SMTP_HOST",
            f"email-smtp.{aws_region}.amazonaws.com",
        ),
        notification_email_smtp_port=_env_int("NOTIFICATION_EMAIL_SMTP_PORT", 587),
        notification_email_smtp_username_ssm_param=_optional_env(
            "NOTIFICATION_EMAIL_SMTP_USERNAME_SSM_PARAM"
        ),
        notification_email_smtp_password_ssm_param=_optional_env(
            "NOTIFICATION_EMAIL_SMTP_PASSWORD_SSM_PARAM"
        ),
        notification_email_batch_size=_env_int("NOTIFICATION_EMAIL_BATCH_SIZE", 25),
        notification_email_max_attempts=_env_int("NOTIFICATION_EMAIL_MAX_ATTEMPTS", 3),
    )
