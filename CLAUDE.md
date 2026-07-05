# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Project Netfall is a FOSS application that gamifies STEM education through a tactical UAV interception simulator. Players analyze spatiotemporal Probability Density Functions (PDFs) of drone traffic to execute timed net-drop interceptions. The app teaches PDFs through hands-on analysis.

## Commands

All commands use [Pixi](https://pixi.prefix.dev/latest/) as the package/environment manager.

```shell
# Start the backend API server (http://localhost:8000)
pixi run backend

# Start the frontend dev server (http://localhost:5173)
# Also starts tsc in watch mode
pixi run frontend

# Run backend unit tests (current environment only)
pixi run backend-tests

# Run backend tests across all Python versions (3.11, 3.12, 3.13, 3.14)
pixi run test-all

# Run pre-commit hooks manually (lint-staged + ruff fix/format)
pixi run pre-commit
```

The Swagger UI for interactive API testing is at http://localhost:8000/docs.

Backend `pytest` tests use an in-memory SQLite database (never the dev database). To run a single test file:

```shell
pixi run -e test-py314 -- pytest backend/tests/test_target_mechanics.py -v
```

## Architecture

### Backend (`backend/`)

The backend is a FastAPI application with two distinct layers:

**REST endpoints** (`app/main.py`): CRUD for Users, Maps, and Targets. Also exposes `/save_target_state/{id}` which triggers Parquet cache generation and `/configure_pdf_parameters/` which updates a global singleton.

**WebSocket endpoint** (`app/features/target_pdf_helpers.py`): `/ws/tactical_map/{target_id}` streams ECharts-formatted JSON payloads. When the frontend sends `{ rel_seconds: N }`, the server evaluates the PDF at that time offset and sends back `{ x, y, data, max_val }`. CPU-bound PDF math runs in `asyncio.to_thread` to avoid blocking the event loop. Results are memoized with `lru_cache`.

**Physics engine** (`app/features/target_mechanics.py`): Pure NumPy/Polars math with no I/O. The PDF pipeline:

1. `generate_map_heat_points` — random anchor nodes on the map grid
2. `describe_lanes` — parametric routes between nodes, with per-target-class variance
3. `map_lane_traffic` — Gaussian spread around each lane (spatial PDF component)
4. `calculate_temporal_lane_traffic` — amplitude-modulated rush-hour surges (temporal component)
5. `evaluate_total_pdf` — returns a `Callable[[datetime], pl.LazyFrame]` that combines both components at a specific moment

Lane configurations are saved to Parquet files under `backend/app/data/parquet_cache/` via `save_map_state`. The WebSocket reads these files on each frame request.

**Schemas** (`app/schemas/`):

- `sqlmodels.py` — SQLModel ORM models (User, Map, Target, RPGClass, Trait, Stats, Upgrade, DefaultTargets) + `get_session` dependency that creates SQLite tables on first call
- `pydmodels.py` — Pydantic models for API I/O + two global in-memory singletons (`SimulationState`, `PDFParamState`) injected via FastAPI `Depends`

`SimulationState` holds loaded Map and Target objects in memory so the WebSocket does not need to hit the database per frame. It must be populated by calling `POST /targets/custom/` or `POST /targets/default/` before opening a WebSocket. The `save_target_state` endpoint (or `load_from_db=True` flag) can reload state from the database.

### Frontend (`frontend/src/`)

- `app/App.tsx` — Root layout: sidebar (`MapConfigUI`) + main canvas (`TacticalMap`). Passes a `configVersion` counter to `TacticalMap` to trigger re-initialization when PDF parameters change.
- `app/Api.tsx` — All HTTP fetch helpers and the `renderTacticalMapWebSocket` factory. API base URL is hardcoded to `http://127.0.0.1:8000`.
- `components/MapConfigUI.tsx` — Sliders for `start_time`, `duration_hours`, `time_steps`, `downsample_step`. Calls `PUT /configure_pdf_parameters/` on submit.
- `components/TacticalMap.tsx` — Handles the full initialization sequence (create/fetch user → create/fetch map → create default targets → save target state → open WebSocket). Renders the ECharts heatmap and a time-scrubbing range slider that sends `{ rel_seconds }` over the WebSocket.

### Key Data Flow

```
POST /users/ → POST /maps/ → POST /targets/default/
  → PUT /save_target_state/{id}  (generates Parquet)
    → WS /ws/tactical_map/{id}
      → slider sends { rel_seconds }
        → server evaluates PDF → sends { x, y, data, max_val }
          → ECharts renders heatmap
```

### Environment & Config

- Backend reads `DATABASE_URL`, `FRONTEND_URL`, `BACKEND_URL`, `HOST_URL`, `WEBSOCKET_URL` from `backend/app/.env` (copy from `.env.example`).
- The default environment (`pixi.toml` `[environments]`) targets Python 3.14. Test environments (`test-py311` through `test-py314`) add pytest/pytest-cov.
- `numpy.random.seed(42)` is set at module import in `target_mechanics.py` for reproducible map generation.
