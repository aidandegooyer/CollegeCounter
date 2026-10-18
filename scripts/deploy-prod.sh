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

# `up -d` succeeds even if the new backend then crash-loops or its migrations
# fail, so wait (up to ~2 minutes) for the API to report this build
VERSION_URL=https://api.collegecounter.org/v1/public/version
tries=0
until curl -fsS --max-time 5 "$VERSION_URL" 2>/dev/null | grep -q "\"$GIT_SHA\""; do
  tries=$((tries + 1))
  if [ "$tries" -ge 40 ]; then
    echo "Deploy failed: $VERSION_URL isn't serving $GIT_SHA" >&2
    docker compose logs --tail=50 backend >&2
    exit 1
  fi
  sleep 3
done

echo "Deployed $GIT_SHA"
