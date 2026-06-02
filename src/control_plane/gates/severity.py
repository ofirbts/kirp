from __future__ import annotations

from enum import Enum


class Severity(str, Enum):
    BLOCK = "block"
    WARN = "warn"
