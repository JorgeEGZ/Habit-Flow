# HabitFlow

HabitFlow is a personal productivity and finance web app built with FastAPI, Vue 3, PostgreSQL, and Docker.

## Features

- Authentication
- Dashboard overview
- Daily habit tracking
- Habit management
- Savings goals
- Contribution history
- Personal finance tracking
- Accounts and categories
- Recurring transaction rules
- Responsive dark UI

## Tech Stack

Backend:
- FastAPI
- SQLAlchemy 2.0
- PostgreSQL
- Alembic
- JWT

Frontend:
- Vue 3
- Vite
- Pinia
- Vue Router
- PrimeVue
- Axios

Infrastructure:
- Docker
- Docker Compose

## Getting Started

### Backend

```bash
docker compose up -d --build
docker compose exec backend alembic upgrade head