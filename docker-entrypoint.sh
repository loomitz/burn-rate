#!/bin/sh
set -eu

if [ "${WAIT_FOR_DB:-true}" = "true" ]; then
  python - <<'PY'
import os
import sys
import time

import psycopg

deadline = time.time() + int(os.getenv("DB_WAIT_TIMEOUT", "30"))
dsn = {
    "dbname": os.getenv("DB_NAME", "burn_rate"),
    "user": os.getenv("DB_USER", "burn_rate"),
    "password": os.getenv("DB_PASSWORD", ""),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "connect_timeout": 2,
}

while True:
    try:
        with psycopg.connect(**dsn):
            break
    except psycopg.OperationalError as exc:
        if time.time() >= deadline:
            print(f"Database is not reachable: {exc}", file=sys.stderr)
            raise
        time.sleep(1)
PY
fi

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  python manage.py migrate --noinput
fi

if [ "${COLLECT_STATIC:-true}" = "true" ]; then
  python manage.py collectstatic --noinput --clear
fi

exec "$@"
