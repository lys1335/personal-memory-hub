"""Configuration subsystem — settings, factories, and accessors."""

from __future__ import annotations

from .settings import AppSettings, get_settings, settings

__all__ = ["AppSettings", "get_settings", "settings"]
