"""Tests for deployment security configuration."""
from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.config import Settings


def _production_settings(**overrides) -> Settings:
    values = {
        "environment": "production",
        "secret_key": "a" * 32,
        "cors_origins": ["https://app.example.com"],
        "cors_headers": ["Authorization", "Content-Type", "X-CSRF-Protection"],
        "refresh_cookie_secure": True,
        "refresh_cookie_samesite": "none",
    }
    values.update(overrides)
    return Settings(**values)


def test_production_settings_reject_wildcard_cors_origin() -> None:
    with pytest.raises(PydanticValidationError, match="explicit origins"):
        _production_settings(cors_origins=["*"])


def test_settings_reject_samesite_none_without_secure_cookie() -> None:
    with pytest.raises(PydanticValidationError, match="requires REFRESH_COOKIE_SECURE"):
        _production_settings(refresh_cookie_secure=False)


def test_production_settings_require_secure_refresh_cookie() -> None:
    with pytest.raises(PydanticValidationError, match="must be true outside development"):
        _production_settings(
            refresh_cookie_secure=False,
            refresh_cookie_samesite="lax",
        )
