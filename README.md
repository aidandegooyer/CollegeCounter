# College Counter

College Counter is a platform to view scores, rankings, and news for collegiate Counter-Strike. College Counter combines a React frontend with Python backends (legacy Flask and a newer Django-based v1 API) to deliver live match results, team/player ELO rankings, event brackets, and editorial content.

## Features

- Live and historical match results and upcoming matches
- Team and player ELO rankings with matchday history
- Event brackets and seed rendering
- News and articles for collegiate CS communities
- Admin tools for importing matches and updating player ELO

## Tech stack

- Frontend: React + TypeScript + Vite (legacy and v1 frontends)
  - Entry point: [cc-frontend/v1/src/App.tsx](cc-frontend/v1/src/App.tsx)
- Backend (v1): Django REST / DRF (controllers at [cc-backend/v1/cc/views.py](cc-backend/v1/cc/views.py))
  - Example API: [`cc.views.update_player_elo`](cc-backend/v1/cc/views.py)

## Quick start (development)

### Note: These instructions are not final and will likely not work without significant debugging. Check back soon.

Prereqs: Node 18+, npm/yarn, Python 3.9+, pip, and optionally Docker.

Frontend (v1)

1. cd cc-frontend/v1
2. npm install
3. npm run dev

Backend (v1 / Django)

1. cd cc-backend/v1
2. python -m venv .venv && source .venv/bin/activate
3. pip install -r requirements.txt
4. python manage.py migrate
5. python manage.py runserver

Postgres

1. Steps to come

## Configuration

- Root environment file: `.env`
- Frontend API base: VITE_API_BASE_URL

## Important files

- Frontend (v1): [cc-frontend/v1/src](cc-frontend/v1/src)
- Backend API (v1): [cc-backend/v1/cc/views.py](cc-backend/v1/cc/views.py)

## Contributing

- Create an issue describing the change or bug.
- Open a feature branch and submit a PR with tests or manual verification steps.
