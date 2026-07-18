from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.utils import timezone


def default_app_time_zone() -> str:
    return getattr(settings, "TIME_ZONE", "UTC") or "UTC"


def normalize_time_zone(value: str | None) -> str:
    time_zone = (value or default_app_time_zone()).strip()
    try:
        ZoneInfo(time_zone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Zona horaria invalida. Usa un identificador IANA como America/Mexico_City.") from exc
    return time_zone


def app_time_zone_name() -> str:
    try:
        from .models import AppSettings

        return normalize_time_zone(AppSettings.load().time_zone)
    except Exception:
        return normalize_time_zone(default_app_time_zone())


def app_zoneinfo(value: str | None = None) -> ZoneInfo:
    return ZoneInfo(normalize_time_zone(value or app_time_zone_name()))


def app_localdate() -> date:
    return timezone.localtime(timezone.now(), app_zoneinfo()).date()
