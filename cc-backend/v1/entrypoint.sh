#!/bin/sh
# Apply any pending migrations, then start the main process (gunicorn).
# Migrations must stay backwards compatible (additive/nullable) because the
# previous container may still be serving while this one starts.
set -e

python manage.py migrate --noinput

exec "$@"
