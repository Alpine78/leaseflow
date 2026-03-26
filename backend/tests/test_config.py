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
        "db_password_ssm_param": "/leaseflow/dev/db/password",
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
        "DB_PASSWORD_SSM_PARAM": "/leaseflow/dev/db/password",
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


def test_resolve_db_password_loads_value_from_ssm(monkeypatch: pytest.MonkeyPatch) -> None:
    ssm_client = Mock()
    ssm_client.get_parameter.return_value = {"Parameter": {"Value": "ssm-password"}}
    boto_client = Mock(return_value=ssm_client)
    monkeypatch.setattr(config.boto3, "client", boto_client)

    settings = _settings(
        aws_region="eu-west-1",
        db_password=None,
        db_password_ssm_param="/leaseflow/dev/db/password",
    )

    assert settings.resolve_db_password() == "ssm-password"
    boto_client.assert_called_once_with("ssm", region_name="eu-west-1")
    ssm_client.get_parameter.assert_called_once_with(
        Name="/leaseflow/dev/db/password",
        WithDecryption=True,
    )


def test_resolve_db_password_raises_when_no_password_source_is_configured() -> None:
    settings = _settings(db_password=None, db_password_ssm_param=None)

    with pytest.raises(config.ConfigError, match="Set DB_PASSWORD or DB_PASSWORD_SSM_PARAM."):
        settings.resolve_db_password()


def test_load_settings_reads_ssm_password_configuration_from_environment(
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
        assert settings.db_password_ssm_param == "/leaseflow/dev/db/password"


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
