#!/bin/sh
# Apply any pending migrations, then start the main process (gunicorn).
#
# `docker compose up` stops the old backend container before starting this
# one, so old code isn't running while migrations apply. Keep migrations
# additive/nullable anyway, so rolling back to the previous image still works.
set -e

python manage.py migrate --noinput

exec "$@"
