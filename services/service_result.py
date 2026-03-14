"""Shared service result model for cross-module error handling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ServiceResult:
    ok: bool
    data: Any = None
    error_code: str | None = None
    error_msg: str | None = None


def success(data: Any = None) -> ServiceResult:
    return ServiceResult(ok=True, data=data)


def failure(error_code: str, error_msg: str) -> ServiceResult:
    return ServiceResult(ok=False, error_code=error_code, error_msg=error_msg)

