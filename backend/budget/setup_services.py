from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import User
from django.db import DEFAULT_DB_ALIAS, OperationalError, ProgrammingError, connections
from django.db.migrations.executor import MigrationExecutor

from .models import AppSettings


def _current_database_config() -> dict[str, object]:
    database = settings.DATABASES[DEFAULT_DB_ALIAS]
    engine = str(database.get("ENGINE", ""))
    return {
        "engine": engine.rsplit(".", 1)[-1] or engine,
        "name": database.get("NAME", ""),
        "user": database.get("USER", ""),
        "host": database.get("HOST", ""),
        "port": database.get("PORT", ""),
        "password_configured": bool(database.get("PASSWORD")),
    }


def _migration_status(connection) -> dict[str, object]:
    executor = MigrationExecutor(connection)
    pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
    return {
        "applied": len(pending) == 0,
        "pending_count": len(pending),
    }


def build_onboarding_status() -> dict[str, object]:
    connection = connections[DEFAULT_DB_ALIAS]
    database = {
        "configured": _current_database_config(),
        "connected": False,
        "message": "",
    }
    migrations = {"applied": False, "pending_count": None}
    initial_config = {
        "ready": False,
        "needs_first_admin": True,
        "has_users": False,
        "settings_ready": False,
    }

    try:
        connection.ensure_connection()
        database["connected"] = True
        database["message"] = "Conexion a base de datos lista."
        migrations = _migration_status(connection)
        if migrations["applied"]:
            has_users = User.objects.exists()
            # Touch the settings table without creating the default row from this public check.
            AppSettings.objects.filter(pk=1).exists()
            initial_config = {
                "ready": True,
                "needs_first_admin": not has_users,
                "has_users": has_users,
                "settings_ready": True,
            }
    except (OperationalError, ProgrammingError, OSError) as exc:
        database["message"] = str(exc)
    finally:
        connection.close_if_unusable_or_obsolete()

    ready = bool(database["connected"] and migrations["applied"] and initial_config["settings_ready"])
    return {
        "ready": ready,
        "database": database,
        "migrations": migrations,
        "initial_config": initial_config,
    }
