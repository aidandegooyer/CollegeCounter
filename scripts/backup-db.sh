#!/bin/sh
# Postgres backups for the db-backup compose service.
#
#   backup-db.sh         dump now, then daily at BACKUP_HOUR_UTC (runs forever)
#   backup-db.sh once    dump now and exit (e.g. before a risky deploy)
#
# Connection comes from the standard PG* env vars. Dumps are plain SQL,
# gzipped, so they restore with psql / load_db.sh.
set -eu

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
BACKUP_HOUR_UTC="${BACKUP_HOUR_UTC:-9}"   # 09:00 UTC = 4-5am US Eastern

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
        echo "[backup] FAILED at $stamp" >&2
        return 1
    fi

    find "$BACKUP_DIR" -name 'cc_*.sql.gz' -mtime +"$RETENTION_DAYS" -print -delete \
        | sed 's/^/[backup] pruned /'
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
