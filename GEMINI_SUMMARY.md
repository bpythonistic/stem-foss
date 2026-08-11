# Project Netfall: Current State & Context Summary

This document serves as a comprehensive context primer for future GenAI sessions regarding **Project Netfall**, a tactical interception simulator that gamifies STEM concepts (specifically kinematics and Probability Density Functions).

---

## 1. Project Overview & Mechanics

Players act as independent contractors operating a high-altitude UAV. They must intercept mid-sized autonomous drones navigating urban "sky lanes." Because the targets are fast, players use a 24-hour simulation cycle to analyze spatiotemporal Probability Density Functions (PDFs) to find temporal "choke points" (low variance, high probability) to execute perfectly timed net drops.

## 2. Finalized Tech Stack

- **Backend:** Python 3.14, FastAPI, NumPy/SciPy (math kernel), Polars (data manipulation), PostgreSQL & SQLModel (database/ORM).
- **Frontend:** TypeScript 5, React, Vite, Apache ECharts (for the dynamic tactical radar canvas).
- **Removed Dependencies:** Leaflet, Seaborn, and mpld3 were deprecated in favor of native ECharts matrix streaming. All current dependencies are permissive (MIT, BSD, Apache); no GPL licenses are in use.

## 3. Key Architectural Decisions

- **WebSocket Streaming:** To prevent UI freezing during timeline scrubbing, the FastAPI backend calculates the math, downsamples the Polars dataframe, explicitly formats the array as `[x_index, y_index, value]`, and streams a pre-serialized JSON payload directly to the React frontend.
- **Parquet Caching:** Instead of keeping the generated hot spot specs (`pl.LazyFrame`) in RAM, the backend writes them to `.parquet` files. The WebSocket worker lazily scans these files on demand.
- **Dependency Injection for State:** FastAPI global configurations (like simulation duration and time steps) are managed via `Depends()` injected singleton models, avoiding direct and unsafe mutations to `app.state`.
- **Global Dark Mode:** The UI utilizes a custom "tactical radar" aesthetic (neon greens, deep blues, dark backgrounds). Styles are heavily driven by global CSS variables in `index.css`.

## 4. Current Development Phase: Sprint 4 (Minimum Viable Ambush)

Due to external time constraints, Phase II (Database, RPG progression, and stateless loadouts) has been temporarily paused. The current sprint is strictly focused on a stateless, fully playable vertical slice: **Observe, Predict, and Drop.**

**Sprint 4 Objectives:**

1.  **Frontend Pipeline:** Ensure the React `TacticalMap` smoothly scrubs the timeline and updates the ECharts heatmap via the WebSocket. _(Largely Complete)_
2.  **Interception Math:** Build a `/intercept` POST endpoint that takes an X, Y, and Impact Time, evaluates the total PDF at that exact coordinate, and returns a "Hit" or "Miss." _(Pending)_
3.  **UI Loop:** Wire up an `onClick` event on the ECharts canvas to trigger the `/intercept` route. _(Pending)_

## 5. Resolved Technical Hurdles (The "Gotchas")

When modifying the codebase, keep the following resolved bugs in mind:

- **Polars Array Broadcasting:** When adding random NumPy arrays to a Polars `LazyFrame`, the frame must be collected into a `DataFrame` first, and `pl.Series()` must be used instead of `pl.lit()` to prevent dimension mismatch errors.
- **Polars Scalar Extraction:** When fetching a single density multiplier for a specific time step, the temporal dataframe must be actively filtered for the exact `current_time` (using `.head(1)` and checking `.height > 0`) before calling `.item(0, 0)`.
- **JSON NaN Serialization:** Python's `json.dumps()` silently outputs unquoted `NaN` or `Infinity` values if the math engine divides by zero, causing Javascript `SyntaxError` crashes on the frontend. The backend must strictly filter for `is_finite()` and enforce `allow_nan=False` during serialization.
- **React WebSocket Race Conditions:** When switching target classes in the UI, the frontend must explicitly call the backend to generate the Parquet cache for the new target (`saveTargetState`) _before_ opening the new WebSocket, and manually jumpstart the data stream upon connection.

## 6. Immediate Next Steps

1.  Complete the FastAPI `/intercept` endpoint logic.
2.  Add click-handling to the React `TacticalMap` to send interception coordinates to the backend.
