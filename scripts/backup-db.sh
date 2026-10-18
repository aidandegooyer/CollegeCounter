#!/bin/sh
# Postgres backups for the db-backup compose service.
#
#   backup-db.sh         dump now, then daily at BACKUP_HOUR_UTC (runs forever)
#   backup-db.sh once    dump now and exit (e.g. before a risky deploy):
#                          docker compose run --rm db-backup once
#
# Connection comes from the standard PG* env vars. Dumps are plain SQL,
# gzipped, so they restore with psql / load_db.sh.
#
# With BACKUP_S3_URI set (e.g. s3://collegecounter-db-backups/), each dump is
# also copied off the server with the AWS CLI, which reads AWS_ACCESS_KEY_ID,
# AWS_SECRET_ACCESS_KEY and AWS_DEFAULT_REGION. The key only needs to upload:
# off-site retention is the bucket's lifecycle rule, so a compromised server
# can't delete the history.
# Failures are posted to DISCORD_ALERTS_WEBHOOK_URL when it's set.
set -eu
umask 077   # dumps contain the whole database; owner-only

BACKUP_DIR="${BACKUP_DIR:-/backups}"
KEEP_BACKUPS="${KEEP_BACKUPS:-14}"
BACKUP_HOUR_UTC="${BACKUP_HOUR_UTC:-9}"   # 09:00 UTC = 4-5am US Eastern
BACKUP_S3_URI="${BACKUP_S3_URI:-}"
DISCORD_ALERTS_WEBHOOK_URL="${DISCORD_ALERTS_WEBHOOK_URL:-}"

# Log a failure and post it to Discord in the same embed style as the
# backend's alerts (cc/discord_logging.py). Messages are our own text, with
# no quotes or backslashes, so they go into the JSON as is.
alert() {
    echo "[backup] $1" >&2
    [ -n "$DISCORD_ALERTS_WEBHOOK_URL" ] || return 0
    payload=$(printf '{"embeds":[{"title":"ERROR in db-backup","description":"%s","color":15158332,"fields":[{"name":"Service","value":"db-backup","inline":true}],"timestamp":"%s"}]}' \
        "$1" "$(date -u +%Y-%m-%dT%H:%M:%SZ)")
    curl -fsS -m 10 -H 'Content-Type: application/json' -d "$payload" \
        "$DISCORD_ALERTS_WEBHOOK_URL" >/dev/null \
        || echo "[backup] couldn't post the alert to Discord" >&2
}

# Copy a finished dump off-site. .offsite_ok marks the last good copy for the
# compose healthcheck.
offsite() {
    [ -n "$BACKUP_S3_URI" ] || return 0
    dest="${BACKUP_S3_URI%/}/$(basename "$1")"
    if aws s3 cp "$1" "$dest" --only-show-errors; then
        touch "$BACKUP_DIR/.offsite_ok"
        echo "[backup] copied to $dest"
    else
        alert "Off-site copy to $dest FAILED. The local dump $1 is fine."
        return 1
    fi
}

dump() {
    stamp=$(date -u +%Y-%m-%dT%H%MZ)
    tmp="$BACKUP_DIR/.cc_$stamp.sql.gz.partial"
    out="$BACKUP_DIR/cc_$stamp.sql.gz"

    # Write to a temp name first so a failed dump never looks like a good backup.
    # pg_dump compresses itself (no pipe) so its exit status isn't masked.
    if pg_dump --no-owner --no-privileges --compress=6 --file="$tmp"; then
        mv "$tmp" "$out"
        echo "[backup] wrote $out ($(du -h "$out" | cut -f1))"
    else
        rm -f "$tmp"
        alert "pg_dump FAILED at $stamp. No new backup was written."
        return 1
    fi

    status=0
    offsite "$out" || status=1

    # Keep the newest KEEP_BACKUPS dumps by count, not age, so a run of failed
    # backups never prunes the last good ones. Names sort chronologically.
    ls -1 "$BACKUP_DIR"/cc_*.sql.gz | sort -r | tail -n +"$((KEEP_BACKUPS + 1))" \
        | while read -r old; do
            rm -f "$old"
            echo "[backup] pruned $old"
        done
    return "$status"
}

seconds_until_next_run() {
    now=$(date -u +%s)
    target=$(( BACKUP_HOUR_UTC * 3600 ))
    echo $(( (target - now % 86400 + 86400) % 86400 ))
}

mkdir -p "$BACKUP_DIR"

until pg_isready -q; do
    echo "[backup] waiting for database..."
    sleep 5
done

if [ "${1:-}" = "once" ]; then
    dump
    exit
fi

dump || true

while true; do
    wait_for=$(seconds_until_next_run)
    [ "$wait_for" -lt 60 ] && wait_for=$(( wait_for + 86400 ))
    echo "[backup] next backup in $(( wait_for / 3600 ))h$(( wait_for % 3600 / 60 ))m"
    sleep "$wait_for"
    dump || true
done
