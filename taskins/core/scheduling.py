"""Conversions de dates et calcul des occurrences cron.

Règle générale : tout est **stocké en UTC** au format SQLite
'YYYY-MM-DD HH:MM:SS', et tout est **saisi et affiché** dans le fuseau
TASKINS_TIMEZONE. Les expressions cron sont interprétées dans ce même fuseau :
'0 2 * * *' signifie 2h heure locale, y compris de part et d'autre des
changements d'heure.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from croniter import croniter

from taskins.core.config import settings

SQL_FORMAT = "%Y-%m-%d %H:%M:%S"


def local_tz() -> ZoneInfo:
    return ZoneInfo(settings.timezone)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_sql(dt: datetime) -> str:
    """datetime conscient du fuseau -> chaîne UTC stockable."""
    return dt.astimezone(timezone.utc).strftime(SQL_FORMAT)


def from_sql(value: str) -> datetime:
    """Chaîne UTC stockée -> datetime conscient du fuseau (UTC)."""
    return datetime.strptime(value, SQL_FORMAT).replace(tzinfo=timezone.utc)


def now_sql() -> str:
    return to_sql(now_utc())


def local_input_to_sql(value: str) -> str:
    """Saisie d'un <input type="datetime-local"> ('2026-07-22T14:30', heure
    locale) -> chaîne UTC stockable."""
    value = value.strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            naive = datetime.strptime(value, fmt)
            break
        except ValueError:
            continue
    else:
        raise ValueError(f"Date invalide : '{value}' (format attendu : AAAA-MM-JJ HH:MM)")
    return to_sql(naive.replace(tzinfo=local_tz()))


def sql_to_local_display(value: str | None) -> str | None:
    """Chaîne UTC stockée -> affichage en heure locale."""
    if value is None:
        return None
    return from_sql(value).astimezone(local_tz()).strftime(SQL_FORMAT)


def is_valid_cron(expression: str) -> bool:
    return croniter.is_valid(expression)


def next_cron_occurrence(expression: str, after: datetime | None = None) -> str:
    """Prochaine occurrence STRICTEMENT postérieure à `after` (par défaut,
    maintenant), calculée dans le fuseau local puis renvoyée en UTC."""
    base_local = (after or now_utc()).astimezone(local_tz())
    return to_sql(croniter(expression, base_local).get_next(datetime))
