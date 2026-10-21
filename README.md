# College Counter

College Counter is a platform to view scores, rankings, and news for collegiate Counter-Strike. College Counter combines a React frontend with a Django REST API backend to deliver live match results, team/player ELO rankings, event brackets, and editorial content.

## Features

- Live and historical match results and upcoming matches
- Team and player ELO rankings with matchday history
- Event brackets and seed rendering
- News and articles for collegiate CS communities
- Admin tools for importing matches and updating player ELO

## Tech stack

- Frontend: React + TypeScript + Vite
- Backend : Django REST/DRF & Postgres

## Quick start (development)

On macOS or Debian/Ubuntu, one script installs everything and sets up the project:

```bash
./setup.sh                       # or: ./setup.sh --dump dev_dump.sql
./dev.sh                         # start the backend and frontend
```

The steps below do the same by hand.

### Prerequisites

- Node.js 18+ and npm (newest version preferred)
- Python 3.14 (matches the production Docker image; `uv` can install it for you)
- PostgreSQL 15+ (newest version preferred)
- Homebrew (macOS)

### Install Dependencies

_Note: this entire section was written by Claude, It should be helpful but feel free to reach out to @aidanxi on discord with any questions_

First, install all required dependencies:

```bash
# Install PostgreSQL 18
brew install postgresql@18

# Install Node.js (if not already installed)
brew install node

# Install Python 3.14 (if not already installed; or let uv do it below)
brew install python@3.14

# Install uv (Python package manager)
brew install uv
```

### Local Development Setup

#### Database Setup

1. Start PostgreSQL:

```bash
brew services start postgresql@15
```

2. Create the database and user:

Connect to PostgreSQL

```bash
psql postgres
```

Run these SQL commands:

```sql
CREATE USER ccdev WITH PASSWORD 'dev';
CREATE DATABASE cc;
GRANT ALL PRIVILEGES ON DATABASE cc TO ccdev;
\c cc
GRANT ALL ON SCHEMA public TO ccdev;
\q
```

Or as one-liners:

```bash
psql postgres -c "CREATE USER ccdev WITH PASSWORD 'dev';"
psql postgres -c "CREATE DATABASE cc;"
psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE cc TO ccdev;"
psql cc -c "GRANT ALL ON SCHEMA public TO ccdev;"
```

3. Test the connection:

```bash
psql -h localhost -U ccdev -d cc
# Password: dev
```

#### Using a Dev Data Dump (Optional)

If you want to work with realistic data instead of an empty database, contact [@aidandegooyer](https://github.com/aidandegooyer) (@aidanxi on discord) for a development database dump.

Once you receive the `dev_dump.sql` or `dev_dump.sql.gz` file:

```bash
# For uncompressed dump
psql -h localhost -U ccdev -d cc < dev_dump.sql

# For compressed dump
gunzip -c dev_dump.sql.gz | psql -h localhost -U ccdev -d cc

# Then run migrations to ensure schema is up to date
cd cc-backend/v1
uv run python manage.py migrate
```

#### Backend (Django v1)

```bash
# Navigate to backend directory
cd cc-backend/v1

# Create virtual environment (Python 3.14, from .python-version) and install
# dependencies. uv downloads Python 3.14 if it isn't installed.
uv sync

# Create .env file from example
cp .env.example .env

# Generate a Django secret key and update .env
uv run python -c 'from django.core.management.utils import get_random_secret_key; print(f"SECRET_KEY={get_random_secret_key()}")' >> .env

# Run migrations
uv run python manage.py migrate

# Create superuser (optional, for admin access)
uv run python manage.py createsuperuser

# Start development server
uv run python manage.py runserver
# Backend runs at http://localhost:8000
```

**Note:** For local development, use `@localhost:5432` in DATABASE_URL. For Docker, use `@db:5432`.

#### Frontend (React/Vite v1)

```bash
# Navigate to frontend directory (in a new terminal)
cd cc-frontend/v1

# Install dependencies
npm install

# Create environment file
echo "VITE_API_BASE_URL=http://localhost:8000/v1" > .env.local
 from example
cp .env.example
npm run dev
# Frontend runs at http://localhost:5173
```

## Configuration

### Environment Variables

Create a `.env` file in the project root (for Docker) or set these variables in your shell:

#### Required Variables

- `SECRET_KEY` - Django secret key (generate with `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`)
- `DATABASE_URL` - PostgreSQL connection string (format: `postgresql://user:password@host:port/dbname`)
- `POSTGRES_USER` - Database username (Docker only)
- `POSTGRES_PASSWORD` - Database password (Docker only)
- `POSTGRES_DB` - Database name (Docker only)

#### Frontend Variables

- `VITE_API_BASE_URL` - Backend API base URL (default: `https://api.collegecounter.org/v1`, for local dev: `http://localhost:8000/v1`)
- `VITE_CURRENT_SEASON_ID` - Current season UUID (optional)

#### Optional Backend Variables

- `DJANGO_DEBUG` - Enable debug mode (`"True"` or `"False"`, default: `"False"`)
- `DJANGO_ALLOWED_HOSTS` - Comma-separated list of allowed hosts (production only)
- `PLAYFLY_API_KEY` - PlayFly API integration key
- `FACEIT_API_KEY` - FACEIT API integration key
- `NWES_API_KEY` - NWES API integration key
- `DISCORD_WEBHOOK_URL` - Discord webhook for notifications
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to Firebase service account JSON

#### Image storage (production)

Team, player and event pictures are stored in an S3-compatible bucket (AWS S3 or DigitalOcean Spaces) behind a CDN, resized to 64/128/256/512px WebP. Without these, picture uploads return 503 and pictures stay at their original URLs.

- `IMAGE_STORAGE_BUCKET` - Bucket name, e.g. `collegecounter-images`
- `IMAGE_CDN_BASE_URL` - Public URL the bucket is served from, e.g. `https://img.collegecounter.org`
- `IMAGE_STORAGE_REGION` - Bucket region (default `us-east-1`)
- `IMAGE_STORAGE_ENDPOINT_URL` - Only for DigitalOcean Spaces, e.g. `https://nyc3.digitaloceanspaces.com`
- `IMAGE_STORAGE_ACL` - `public-read` for DigitalOcean Spaces (its CDN only serves public files); leave empty for AWS
- `IMAGE_AWS_ACCESS_KEY_ID`, `IMAGE_AWS_SECRET_ACCESS_KEY` - Key that can read and write the bucket

#### Off-site backups (production)

- `BACKUP_S3_URI` - Where each daily dump is copied, e.g. `s3://collegecounter-db-backups/`. Unset keeps dumps on the server only.
- `BACKUP_AWS_ACCESS_KEY_ID`, `BACKUP_AWS_SECRET_ACCESS_KEY` - Key that can only upload (`s3:PutObject`) to that bucket
- `BACKUP_AWS_REGION` - Bucket region (default `us-east-1`)
- `DISCORD_ALERTS_WEBHOOK_URL` - Also receives backup failures

### Example .env file

```env
# Database (Docker)
DATABASE_URL=postgresql://ccdev:dev@db:5432/cc
POSTGRES_USER=ccdev
POSTGRES_PASSWORD=dev
POSTGRES_DB=cc

# For local development, use @localhost:5432 instead:
# DATABASE_URL=postgresql://ccdev:dev@localhost:5432/cc

# Django
SECRET_KEY=your-generated-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# APIs (optional for basic functionality)
PLAYFLY_API_KEY=
FACEIT_API_KEY=
NWES_API_KEY=
DISCORD_WEBHOOK_URL=

# Firebase (optional)
GOOGLE_APPLICATION_CREDENTIALS=/secrets/college-counter-9057f-firebase-adminsdk-fbsvc-a632f7f6e6.json
```

## Important files

- Frontend (v1): [cc-frontend/v1/src](cc-frontend/v1/src)
- Backend API (v1): [cc-backend/v1/cc/views.py](cc-backend/v1/cc/views.py)
- Django settings: [cc-backend/v1/v1/settings.py](cc-backend/v1/v1/settings.py)
- Docker Compose: [docker-compose.yml](docker-compose.yml)
- Frontend routing: [cc-frontend/v1/src/App.tsx](cc-frontend/v1/src/App.tsx)
- API service: [cc-frontend/v1/src/services/api.ts](cc-frontend/v1/src/services/api.ts)

## Development Commands

### Backend

```bash
cd cc-backend/v1

# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Sync dependencies
uv sync

# Run Django commands with uv
uv run python manage.py migrate
uv run python manage.py makemigrations
uv run python manage.py createsuperuser
uv run python manage.py runserver
uv run python manage.py test
uv run python manage_admins.py

# Or activate venv and run directly
source .venv/bin/activate
python manage.py runserver

# Verify database connection
psql -h localhost -U ccdev -d cc
```

### Public API docs

The public API (`/v1/public/...`) is documented with OpenAPI. Swagger UI is at
[api.collegecounter.org/v1/public/docs/](https://api.collegecounter.org/v1/public/docs/)
(locally, `http://localhost:8000/v1/public/docs/`), and the raw schema at
`/v1/public/schema/`. The admin API isn't documented.

Each public view's parameters and response shape are described in
`cc/public_schema.py`. The tests check real responses against it, and check
that the committed `openapi.yaml` is what the code generates, so API changes
show up in PR diffs. After changing a public endpoint, update
`cc/public_schema.py`, bump `API_VERSION` in `v1/settings.py` (minor for
additions, major for changes that break clients; CI fails a PR that changes
`openapi.yaml` without a bump), and regenerate:

```bash
cd cc-backend/v1
uv run python manage.py spectacular --validate --fail-on-warn --file openapi.yaml
```

### Frontend

```bash
cd cc-frontend/v1

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

### Docker

```bash
# Build and start all services
docker-compose up --build

# Start services in background
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f [service_name]

# Rebuild specific service
docker-compose up --build [service_name]
```

### Deploying

On the droplet, `scripts/deploy-prod.sh` pulls `main` and rebuilds with the
commit baked into the images. The site footer shows it (`build 8f03a25`), as
do the API docs' version (`1.0.0+8f03a25`) and
`https://api.collegecounter.org/v1/public/version`, so you can check what's
running. The script waits for that endpoint to report the new commit and
fails, printing the backend's logs, if it doesn't within ~2 minutes. A plain `docker compose up --build` works too, but shows `dev`
instead of the commit.

### Backups

The `db-backup` service dumps the database daily at 09:00 UTC to `./backups` (newest 14 kept) and, with `BACKUP_S3_URI` set, copies each dump off the server. The off-site key can only upload, so the server can't delete anything there, and with bucket versioning on, an overwrite keeps the old version. Retention is the bucket's lifecycle rule (90 days for current versions, 7 for overwritten ones). Failures post to `DISCORD_ALERTS_WEBHOOK_URL`, and the service shows `unhealthy` if no dump or off-site copy succeeded in 26 hours.

```bash
# Back up now (do this before deploys with migrations)
docker compose run --rm db-backup once
```

To restore, use admin credentials on your own machine (the server's key can't list or download):

```bash
aws s3 ls s3://collegecounter-db-backups/
aws s3 cp s3://collegecounter-db-backups/cc_2026-10-17T0900Z.sql.gz .
gunzip -k cc_2026-10-17T0900Z.sql.gz
./load_db.sh cc_2026-10-17T0900Z.sql   # file mode; piped mode eats the first byte
```

Add `--endpoint-url https://<region>.digitaloceanspaces.com` to the `aws` commands for Spaces.

## Project Structure

- `cc-backend/v1/` - Current Django REST API backend
- `cc-frontend/v1/` - Current React + TypeScript + Vite frontend
- `studio-cc-cms/` - Sanity CMS for content management

## Development Tips

### Bypassing Firebase Auth During Development

When `DJANGO_DEBUG=True`, you can bypass Firebase authentication by using a development token:

```bash
# Use this Authorization header in your API requests
Authorization: Bearer dev
```

This gives you full admin/owner access without needing Firebase credentials. Great for:

- Testing admin endpoints
- Developing without sharing production Firebase keys
- Running integration tests

**Example with curl:**

```bash
curl -H "Authorization: Bearer dev" http://localhost:8000/v1/your-endpoint
```

**In your frontend development**, update the API interceptor to use the dev token:

```typescript
// In cc-frontend/v1/src/services/api.ts (temporarily for dev)
config.headers.Authorization = "Bearer dev";
```

**Security Note:** This bypass only works when `DJANGO_DEBUG=True`. Never set DEBUG=True in production!

## Contributing

- Create an issue describing the change or bug.
- Open a feature branch and submit a PR with tests or manual verification steps.
