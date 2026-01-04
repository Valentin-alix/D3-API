# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

D3-API is a FastAPI-based REST API for Dofus 3 item price analysis and character management. It collects price history data and calculates profitable trading/crafting opportunities.

## Commands

```bash
# Development server (starts dev DB container + uvicorn with reload)
python main.py

# Run tests
pytest

# Run single test
pytest tests/test_item_price_history.py::test_function_name

# Database migrations
poe makemigrations    # Generate new migration from model changes
poe migrate           # Apply pending migrations

# Production
docker-compose -f docker-compose.prod.yml up
```

## Architecture

```
src/
├── models/         # SQLAlchemy ORM models (Base class auto-generates snake_case table names)
├── schemas/        # Pydantic validation schemas
├── controllers/    # Business logic (price analysis, profitability calculations)
├── routers/        # FastAPI route handlers
├── alembic/        # Database migrations
└── database.py     # SQLAlchemy engine/session factory
```

**Key patterns:**

- Dependency injection for DB sessions: all routes use `Depends(session_local)`
- Controllers contain complex SQL with window functions for statistical analysis
- Models inherit from `Base` in `src/models/base.py` which auto-converts CamelCase class names to snake_case table names

## API Routes

- `/item_price_history` - Price data ingestion and analysis (sales speed, price evolution, profitability)
- `/character` - Character CRUD and mule management
- `/data_center` - Game data lookups (items, types) from D3Database submodule

## Database

PostgreSQL with SQLAlchemy. Connection configured via environment variables in `.env`:

- `DB_HOST`, `DB_USERNAME`, `DB_PASSWORD`, `DB_NAME`

On startup, `main.py` waits for DB readiness then auto-runs migrations.

## External Data

`D3Database/` is a git submodule containing Dofus 3 game data (item definitions, categories, recipes).
