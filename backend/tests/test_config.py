from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import Mock

import pytest

from app import config


def _settings(**overrides: object) -> config.Settings:
    values: dict[str, object] = {
        "app_env": "test",
        "log_level": "INFO",
        "aws_region": "eu-north-1",
        "db_host": "db.internal",
        "db_port": 5432,
        "db_name": "leaseflow",
        "db_user": "leaseflow_app",
        "db_password": "direct-password",
        "db_password_secret_arn": "arn:aws:secretsmanager:eu-north-1:123456789012:secret:rds-master",
        "notification_email_delivery_enabled": False,
        "notification_email_sender": "",
        "notification_email_smtp_host": "email-smtp.eu-north-1.amazonaws.com",
        "notification_email_smtp_port": 587,
        "notification_email_smtp_username_ssm_param": None,
        "notification_email_smtp_password_ssm_param": None,
        "notification_email_configuration_set": "",
        "notification_email_batch_size": 25,
        "notification_email_max_attempts": 3,
    }
    values.update(overrides)
    return config.Settings(**values)


def _set_valid_load_settings_env(
    monkeypatch: pytest.MonkeyPatch, *, missing: str | None = None
) -> None:
    values = {
        "APP_ENV": "test",
        "LOG_LEVEL": "DEBUG",
        "AWS_REGION": "eu-west-1",
        "DB_HOST": "db.internal",
        "DB_PORT": "6543",
        "DB_NAME": "leaseflow",
        "DB_USER": "leaseflow_app",
        "DB_PASSWORD_SECRET_ARN": "arn:aws:secretsmanager:eu-west-1:123456789012:secret:rds-master",
    }
    for name, value in values.items():
        if name == missing:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)

    monkeypatch.delenv("DB_PASSWORD", raising=False)


@contextmanager
def _fresh_load_settings_cache() -> Iterator[None]:
    config.load_settings.cache_clear()
    try:
        yield
    finally:
        config.load_settings.cache_clear()


def test_resolve_db_password_returns_direct_password_without_ssm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boto_client = Mock()
    monkeypatch.setattr(config.boto3, "client", boto_client)

    settings = _settings()

    assert settings.resolve_db_password() == "direct-password"
    boto_client.assert_not_called()


def test_resolve_db_password_loads_value_from_secrets_manager(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import json

    secret_arn = "arn:aws:secretsmanager:eu-west-1:123456789012:secret:rds-master"
    sm_client = Mock()
    sm_client.get_secret_value.return_value = {
        "SecretString": json.dumps({"password": "sm-password", "username": "admin"})
    }
    boto_client = Mock(return_value=sm_client)
    monkeypatch.setattr(config.boto3, "client", boto_client)

    settings = _settings(
        aws_region="eu-west-1",
        db_password=None,
        db_password_secret_arn=secret_arn,
    )

    assert settings.resolve_db_password() == "sm-password"
    boto_client.assert_called_once_with("secretsmanager", region_name="eu-west-1")
    sm_client.get_secret_value.assert_called_once_with(SecretId=secret_arn)


def test_resolve_db_password_raises_when_no_password_source_is_configured() -> None:
    settings = _settings(db_password=None, db_password_secret_arn=None)

    with pytest.raises(config.ConfigError, match="Set DB_PASSWORD or DB_PASSWORD_SECRET_ARN."):
        settings.resolve_db_password()


def test_load_settings_reads_secret_arn_password_configuration_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _fresh_load_settings_cache():
        _set_valid_load_settings_env(monkeypatch)

        settings = config.load_settings()

        assert settings.app_env == "test"
        assert settings.log_level == "DEBUG"
        assert settings.aws_region == "eu-west-1"
        assert settings.db_host == "db.internal"
        assert settings.db_port == 6543
        assert settings.db_name == "leaseflow"
        assert settings.db_user == "leaseflow_app"
        assert settings.db_password is None
        assert (
            settings.db_password_secret_arn
            == "arn:aws:secretsmanager:eu-west-1:123456789012:secret:rds-master"
        )
        assert settings.notification_email_delivery_enabled is False
        assert settings.notification_email_sender == ""
        assert settings.notification_email_smtp_host == "email-smtp.eu-west-1.amazonaws.com"
        assert settings.notification_email_smtp_port == 587
        assert settings.notification_email_smtp_username_ssm_param is None
        assert settings.notification_email_smtp_password_ssm_param is None
        assert settings.notification_email_configuration_set == ""
        assert settings.notification_email_batch_size == 25
        assert settings.notification_email_max_attempts == 3


def test_load_settings_reads_notification_email_delivery_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _fresh_load_settings_cache():
        _set_valid_load_settings_env(monkeypatch)
        monkeypatch.setenv("NOTIFICATION_EMAIL_DELIVERY_ENABLED", "true")
        monkeypatch.setenv("NOTIFICATION_EMAIL_SENDER", "sender@example.test")
        monkeypatch.setenv("NOTIFICATION_EMAIL_SMTP_HOST", "smtp.example.test")
        monkeypatch.setenv("NOTIFICATION_EMAIL_SMTP_PORT", "2525")
        monkeypatch.setenv(
            "NOTIFICATION_EMAIL_SMTP_USERNAME_SSM_PARAM",
            "/leaseflow/dev/notification-email/smtp/username",
        )
        monkeypatch.setenv(
            "NOTIFICATION_EMAIL_SMTP_PASSWORD_SSM_PARAM",
            "/leaseflow/dev/notification-email/smtp/password",
        )
        monkeypatch.setenv("NOTIFICATION_EMAIL_CONFIGURATION_SET", "leaseflow-dev-events")
        monkeypatch.setenv("NOTIFICATION_EMAIL_BATCH_SIZE", "10")
        monkeypatch.setenv("NOTIFICATION_EMAIL_MAX_ATTEMPTS", "5")

        settings = config.load_settings()

        assert settings.notification_email_delivery_enabled is True
        assert settings.notification_email_sender == "sender@example.test"
        assert settings.notification_email_smtp_host == "smtp.example.test"
        assert settings.notification_email_smtp_port == 2525
        assert (
            settings.notification_email_smtp_username_ssm_param
            == "/leaseflow/dev/notification-email/smtp/username"
        )
        assert (
            settings.notification_email_smtp_password_ssm_param
            == "/leaseflow/dev/notification-email/smtp/password"
        )
        assert settings.notification_email_configuration_set == "leaseflow-dev-events"
        assert settings.notification_email_batch_size == 10
        assert settings.notification_email_max_attempts == 5


def test_resolve_notification_email_smtp_credentials_loads_username_and_password_from_ssm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ssm_client = Mock()
    ssm_client.get_parameter.side_effect = [
        {"Parameter": {"Value": "smtp-user"}},
        {"Parameter": {"Value": "smtp-password"}},
    ]
    boto_client = Mock(return_value=ssm_client)
    monkeypatch.setattr(config.boto3, "client", boto_client)

    settings = _settings(
        aws_region="eu-north-1",
        notification_email_smtp_username_ssm_param="/leaseflow/dev/smtp/username",
        notification_email_smtp_password_ssm_param="/leaseflow/dev/smtp/password",
    )

    assert settings.resolve_notification_email_smtp_credentials() == (
        "smtp-user",
        "smtp-password",
    )
    boto_client.assert_called_once_with("ssm", region_name="eu-north-1")
    assert ssm_client.get_parameter.call_args_list[0].kwargs == {
        "Name": "/leaseflow/dev/smtp/username",
        "WithDecryption": True,
    }
    assert ssm_client.get_parameter.call_args_list[1].kwargs == {
        "Name": "/leaseflow/dev/smtp/password",
        "WithDecryption": True,
    }


@pytest.mark.parametrize("missing_name", ["DB_HOST", "DB_NAME", "DB_USER"])
def test_load_settings_raises_for_missing_required_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
    missing_name: str,
) -> None:
    with _fresh_load_settings_cache():
        _set_valid_load_settings_env(monkeypatch, missing=missing_name)

        with pytest.raises(
            config.ConfigError,
            match=f"Missing required environment variable: {missing_name}",
        ):
            config.load_settings()
