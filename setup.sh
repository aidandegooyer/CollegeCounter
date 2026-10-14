#!/usr/bin/env bash
#
# One-time setup for a new College Counter dev machine (macOS or Debian/Ubuntu).
# Installs the tools, creates the local database, and sets up the backend and
# frontend. Safe to run again: it skips anything already done.
#
# Usage:
#   ./setup.sh                       # everything
#   ./setup.sh --dump dev_dump.sql   # also load a dev data dump (.sql or .sql.gz)
#   ./setup.sh --skip-install        # tools are already installed; just set up the project
#
# Then start both servers with ./dev.sh

set -euo pipefail

# Must match DATABASE_URL in cc-backend/v1/.env.example
DB_NAME="cc"
DB_USER="ccdev"
DB_PASSWORD="dev"
PG_VERSION="18"
NODE_MAJOR="22"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

step() { echo -e "\n${BLUE}==> $1${NC}"; }
ok() { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}! $1${NC}"; }
die() { echo -e "${RED}✗ $1${NC}" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

usage() {
    sed -n '3,12p' "$0" | sed 's/^# \{0,1\}//'
    exit "${1:-0}"
}

DUMP=""
SKIP_INSTALL=false
while [ $# -gt 0 ]; do
    case "$1" in
        --dump)
            [ $# -ge 2 ] || die "--dump needs a file"
            DUMP="$2"
            shift 2
            ;;
        --skip-install) SKIP_INSTALL=true; shift ;;
        -h | --help) usage ;;
        *) echo -e "${RED}Unknown option: $1${NC}"; usage 1 ;;
    esac
done

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/cc-backend/v1"
FRONTEND="$ROOT/cc-frontend/v1"
[ -d "$BACKEND" ] && [ -d "$FRONTEND" ] || die "Run this from a College Counter checkout"
if [ -n "$DUMP" ]; then
    [ -f "$DUMP" ] || die "Dump file not found: $DUMP"
    DUMP="$(cd "$(dirname "$DUMP")" && pwd)/$(basename "$DUMP")"
fi

case "$(uname -s)" in
    Darwin) OS="mac" ;;
    Linux)
        have apt-get || die "Only Debian/Ubuntu Linux is supported; see README.md to install by hand"
        OS="linux"
        ;;
    *) die "Unsupported OS $(uname -s); see README.md to install by hand (or use WSL on Windows)" ;;
esac

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

load_brew() {
    for brew in /opt/homebrew/bin/brew /usr/local/bin/brew; do
        [ -x "$brew" ] && eval "$("$brew" shellenv)" && return 0
    done
    return 1
}

install_mac() {
    if ! have brew && ! load_brew; then
        step "Installing Homebrew (it will ask for your password)"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        load_brew || die "Homebrew installed, but brew isn't on PATH; open a new terminal and rerun"
    fi
    ok "Homebrew"

    # Don't upgrade anything that's already installed
    export HOMEBREW_NO_INSTALL_UPGRADE=1

    if node_ok; then
        ok "Node.js $(node -v) already installed"
    else
        step "Installing Node.js"
        brew install node
    fi

    if have uv; then
        ok "uv already installed"
    else
        step "Installing uv"
        brew install uv
    fi

    # An existing Postgres (Postgres.app, another Homebrew version, ...) is
    # used as is; installing a second one would fight it for port 5432
    local existing
    if pg_running; then
        ok "PostgreSQL already running on localhost:5432"
    elif existing="$(brew list --formula -1 | grep -E '^postgresql(@[0-9]+)?$' | sort -V | tail -1)" \
        && [ -n "$existing" ]; then
        step "Starting the installed $existing"
        brew services start "$existing"
    else
        step "Installing PostgreSQL $PG_VERSION"
        brew install "postgresql@$PG_VERSION"
        brew services start "postgresql@$PG_VERSION"
    fi
}

install_linux() {
    local packages=()
    have curl || packages+=(curl ca-certificates gnupg)
    have psql || packages+=(postgresql postgresql-contrib)
    if [ ${#packages[@]} -gt 0 ]; then
        step "Installing ${packages[*]} (needs sudo)"
        sudo apt-get update
        sudo apt-get install -y "${packages[@]}"
    else
        ok "PostgreSQL already installed"
    fi

    if node_ok; then
        ok "Node.js $(node -v) already installed"
    else
        step "Installing Node.js $NODE_MAJOR (needs sudo)"
        curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | sudo -E bash -
        sudo apt-get install -y nodejs
    fi

    if have uv; then
        ok "uv already installed"
    else
        step "Installing uv"
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    fi

    if pg_running; then
        ok "PostgreSQL already running on localhost:5432"
    else
        sudo systemctl enable --now postgresql 2>/dev/null || sudo service postgresql start
    fi
}

# Vite 6 needs Node 20+
node_ok() {
    have node && [ "$(node -p 'process.versions.node.split(".")[0]')" -ge 20 ]
}

pg_running() {
    have pg_isready && pg_isready -h localhost -q
}

# psql from Homebrew's keg-only postgresql@N or Postgres.app isn't on PATH by
# default
add_postgres_to_path() {
    have psql && return
    local dir
    for dir in /Applications/Postgres.app/Contents/Versions/latest/bin; do
        [ -x "$dir/psql" ] && export PATH="$dir:$PATH" && return
    done
    if have brew; then
        dir="$(brew list --formula -1 | grep -E '^postgresql(@[0-9]+)?$' | sort -V | tail -1)"
        [ -n "$dir" ] && export PATH="$(brew --prefix "$dir")/bin:$PATH"
    fi
    return 0
}

[ "$OS" = "mac" ] && { have brew || load_brew || true; }
add_postgres_to_path
if [ "$SKIP_INSTALL" = false ]; then
    if [ "$OS" = "mac" ]; then install_mac; else install_linux; fi
    add_postgres_to_path
fi

for tool in psql node npm uv; do
    have "$tool" || die "$tool isn't installed or isn't on PATH"
done
ok "psql $(psql --version | awk '{print $3}'), node $(node -v), uv $(uv --version | awk '{print $2}')"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

step "Setting up the local database"

# Superuser access: your own user with Homebrew, the postgres user on Linux
admin_psql() {
    if [ "$OS" = "mac" ]; then
        psql -d postgres -v ON_ERROR_STOP=1 "$@"
    else
        sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 "$@"
    fi
}

for _ in $(seq 1 30); do
    pg_isready -h localhost -q && break
    sleep 1
done
pg_isready -h localhost -q || die "PostgreSQL isn't accepting connections on localhost:5432"

if [ "$(admin_psql -tAc "SELECT 1 FROM pg_roles WHERE rolname = '$DB_USER'")" = "1" ]; then
    ok "Database user $DB_USER exists"
else
    admin_psql -qc "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD'"
    ok "Created database user $DB_USER"
fi
# The test runner creates and drops its own test_$DB_NAME database
admin_psql -qc "ALTER USER $DB_USER CREATEDB"

if [ "$(admin_psql -tAc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'")" = "1" ]; then
    ok "Database $DB_NAME exists"
else
    admin_psql -qc "CREATE DATABASE $DB_NAME OWNER $DB_USER"
    ok "Created database $DB_NAME"
fi

export PGPASSWORD="$DB_PASSWORD"
app_psql() { psql -h localhost -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 "$@"; }
app_psql -qc "SELECT 1" >/dev/null || die "Can't log in as $DB_USER; check pg_hba.conf allows password logins on localhost"

if [ -n "$DUMP" ]; then
    tables="$(app_psql -tAc "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'")"
    if [ "$tables" != "0" ]; then
        warn "Database $DB_NAME already has tables, so the dump wasn't loaded. To replace it: ./load_db.sh $DUMP"
    else
        step "Loading $(basename "$DUMP")"
        if [[ "$DUMP" == *.gz ]]; then
            gunzip -c "$DUMP" | app_psql -q >/dev/null
        else
            app_psql -q -f "$DUMP" >/dev/null
        fi
        ok "Loaded the dump"
    fi
fi

# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------

step "Setting up the backend (cc-backend/v1)"
cd "$BACKEND"

# Installs Python 3.14 (from .python-version) if needed, plus the dependencies
uv sync
ok "Python dependencies"

# Django's load_dotenv() uses the nearest .env up the tree, so a repo-root
# .env (the Docker one) also counts; a new one here would override it
if [ -f .env ]; then
    ok ".env exists; leaving it alone"
elif [ -f "$ROOT/.env" ]; then
    ok "Using the repo-root .env; leaving it alone"
else
    cp .env.example .env
    uv run python - <<'EOF'
from pathlib import Path

from django.core.management.utils import get_random_secret_key

env = Path(".env")
lines = [
    f"SECRET_KEY={get_random_secret_key()}" if line.startswith("SECRET_KEY=") else line
    for line in env.read_text().splitlines()
]
env.write_text("\n".join(lines) + "\n")
EOF
    ok "Created .env with a new SECRET_KEY"
fi

uv run python manage.py migrate --noinput
ok "Migrations applied"

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

step "Setting up the frontend (cc-frontend/v1)"
cd "$FRONTEND"

npm ci
ok "Node dependencies"

if [ -f .env ]; then
    ok ".env exists; leaving it alone"
else
    cp .env.example .env
    ok "Created .env"
fi

# ---------------------------------------------------------------------------

echo -e "\n${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Setup complete${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "Start both servers:   ${BLUE}./dev.sh${NC}"
echo -e "Frontend:             http://localhost:5173"
echo -e "Backend:              http://localhost:8000"
echo -e "Run backend tests:    cd cc-backend/v1 && uv run python manage.py test cc.tests"
echo
echo "Optional:"
echo "  - API keys (FACEIT_API_KEY, PLAYFLY_API_KEY, ...) go in cc-backend/v1/.env;"
echo "    match imports and refreshes need them, browsing doesn't."
echo "  - Admin pages work locally without Firebase: with DJANGO_DEBUG=True the"
echo "    backend accepts the token \"Bearer dev\"."
if [ -z "$DUMP" ] && [ "$(app_psql -tAc "SELECT count(*) FROM cc_match" 2>/dev/null || echo 0)" = "0" ]; then
    echo "  - The database is empty. Ask @aidanxi on Discord for a dev dump, then:"
    echo "      ./setup.sh --skip-install --dump dev_dump.sql   (or ./load_db.sh to replace data)"
fi
