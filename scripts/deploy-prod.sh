#!/bin/sh
# Deploy the latest main on the droplet: pull, then rebuild and restart with
# the commit baked into the images. The site footer, /v1/public/version and
# the API docs show it, so you can check what's running.
#
# Back up first if the new code has migrations (see "Backups" in the README).
set -eu

cd "$(dirname "$0")/.."

git pull --ff-only

GIT_SHA="$(git rev-parse --short HEAD)"
BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
export GIT_SHA BUILD_DATE

docker compose up -d --build

echo "Deployed $GIT_SHA. Check: curl https://api.collegecounter.org/v1/public/version"
