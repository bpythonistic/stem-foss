"""
Provides helper functions for formatting and caching PDFs.

- save_map_state: Caches lane configs to Parquet and precomputes all frames.
- get_echarts_payload: Formats PDF matrices for frontend UI.
- tactical_map_stream: WebSocket endpoint for UI streaming.
"""

import asyncio
import json
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np
import polars as pl
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.features.target_mechanics import (
    describe_lanes,
    evaluate_total_pdf,
    generate_map_heat_points,
)
from app.schemas.pydmodels import (
    PDFParamState,
    SimulationState,
    get_param_state,
    get_sim_state,
)
from app.schemas.sqlmodels import Map as TargetMap
from app.schemas.sqlmodels import Target, TargetClass

router = APIRouter()

PARQUET_DIR = Path(__file__).parent.parent / "data" / "parquet_cache"

# Precomputed frame cache: target_id -> {rel_seconds: json_payload}
_frame_cache: dict[str, dict[int, str]] = {}

_INTERCEPT_RADIUS = 5.0  # map units


def _at_least_one_probability(
    pdf_matrix: np.ndarray,
    grid_spacing: float,
    intercept_radius: float,
    num_targets: int,
) -> np.ndarray:
    """
    Converts a normalized single-target PDF matrix to
    P(at least one of num_targets targets lies within intercept_radius).

    Uses a direct disk-kernel convolution (no scipy required).
    """
    radius_cells = intercept_radius / grid_spacing
    r = int(np.ceil(radius_cells))
    js, is_ = np.ogrid[-r : r + 1, -r : r + 1]
    disk = is_**2 + js**2 <= radius_cells**2

    h, w = pdf_matrix.shape
    padded = np.pad(pdf_matrix, r, mode="constant", constant_values=0.0)

    # Sum PDF values within the disk for every cell
    p_within = np.zeros((h, w), dtype=np.float64)
    for di in range(-r, r + 1):
        for dj in range(-r, r + 1):
            if disk[di + r, dj + r]:
                p_within += padded[r + di : r + di + h, r + dj : r + dj + w]

    np.clip(p_within, 0.0, 1.0, out=p_within)
    return 1.0 - (1.0 - p_within) ** num_targets


def _num_targets_for_class(target_map: TargetMap, category: TargetClass) -> int:
    match category:
        case TargetClass.SMALL:
            return target_map.num_small_targets
        case TargetClass.MEDIUM:
            return target_map.num_medium_targets
        case TargetClass.LARGE:
            return target_map.num_large_targets
        case _:
            return 1


def save_map_state(
    target_map: TargetMap,
    target_specs: Target,
    param_state: PDFParamState | None = None,
    parquet_path: Path | None = None,
) -> None:
    """
    Caches the static map routes to a file and precomputes all PDF frames.

    Args:
        target_map (TargetMap): The active operational zone map.
        target_specs (Target): The stats used to calculate variance.
        param_state (PDFParamState | None): When provided, all time steps are
            precomputed and stored in memory so the WebSocket serves lookups
            instead of running the physics engine per frame.
        parquet_path (Path | None): Override for the Parquet output directory.
    Returns:
        None
    """
    heat_points = generate_map_heat_points(target_map)
    lanes_lf = describe_lanes(target_map, heat_points, target_specs)
    data_dir = PARQUET_DIR if parquet_path is None else parquet_path
    lanes_lf.collect().write_parquet(
        data_dir / f"current_lanes_for_{target_specs.id}.parquet"
    )
    if param_state is not None:
        try:
            _precompute_frames(target_map, target_specs, param_state)
        except (ValueError, FileNotFoundError):
            # Lane file was written to a non-default path (e.g. tests); skip.
            pass


def _precompute_frames(
    target_map: TargetMap,
    target_specs: Target,
    param_state: PDFParamState,
) -> None:
    """
    Evaluates the PDF at every time step and stores the results in memory.

    The WebSocket can then serve any frame as a dict lookup instead of
    running the physics engine on demand.
    """
    start_dt = datetime.fromisoformat(param_state.start_time)
    duration = timedelta(hours=param_state.duration_hours)
    time_steps = param_state.time_steps
    downsample_step = param_state.downsample_step
    total_seconds = int(duration.total_seconds())

    target_map_str = target_map.model_dump_json()
    target_id = target_specs.id or ""
    num_targets = _num_targets_for_class(target_map, target_specs.category)
    frames: dict[int, str] = {}

    for step_idx in range(time_steps):
        # Distribute steps evenly across [0, total_seconds]
        rel_secs = (
            round(total_seconds * step_idx / (time_steps - 1))
            if time_steps > 1
            else 0
        )
        target_time = start_dt + timedelta(seconds=rel_secs)
        frames[rel_secs] = get_echarts_payload(
            target_map_str=target_map_str,
            target_specs_id=target_id,
            target_time=target_time,
            duration=duration,
            time_steps=time_steps,
            downsample_step=downsample_step,
            num_targets=num_targets,
        )

    _frame_cache[target_id] = frames


def get_nearest_frame(target_id: str, rel_seconds: int) -> str | None:
    """
    Returns the precomputed JSON payload closest to the requested time.

    Args:
        target_id (str): The UUID of the target specification.
        rel_seconds (int): Seconds from param_state.start_time.
    Returns:
        str | None: The serialized ECharts payload, or None if not cached.
    """
    frames = _frame_cache.get(target_id)
    if not frames:
        return None
    nearest = min(frames.keys(), key=lambda k: abs(k - rel_seconds))
    return frames[nearest]


def clear_parquet_cache(parquet_path: Path | None = None) -> None:
    """
    Clears all cached Parquet files and the in-memory frame cache.

    Args:
        parquet_path (Path | None): Override for the Parquet directory.
    Returns:
        None
    """
    data_dir = PARQUET_DIR if parquet_path is None else parquet_path
    for file in data_dir.glob("current_lanes_for_*.parquet"):
        try:
            file.unlink()
            print(f"Deleted cached file: {file}")
        except Exception as e:
            print(f"Error deleting file {file}: {e}")
    _frame_cache.clear()
    get_echarts_payload.cache_clear()


@lru_cache(maxsize=65536)
def get_echarts_payload(
    target_map_str: str,
    target_specs_id: str,
    target_time: datetime,
    duration: timedelta,
    time_steps: int,
    downsample_step: int = 4,
    num_targets: int = 1,
) -> str:
    """
    Returns P(at least one target within 5 map-units) at every grid cell.

    Args:
        target_map_str (str): JSON string of the active map.
        target_specs_id (str): UUID for locating the lane Parquet file.
        target_time (datetime): The exact moment to evaluate the PDF.
        duration (timedelta): Total simulation cycle length.
        time_steps (int): Temporal resolution of the simulation.
        downsample_step (int): Spatial subsampling factor.
        num_targets (int): Number of independent targets of this class.
    Returns:
        str: Serialized JSON payload formatted for ECharts.
    """
    target_map = TargetMap(**json.loads(target_map_str))
    try:
        lanes = pl.scan_parquet(
            PARQUET_DIR / f"current_lanes_for_{target_specs_id}.parquet"
        )
    except FileNotFoundError:
        raise ValueError(
            "Lane configuration for target_specs_id "
            f"{target_specs_id} not found in cache."
        )

    # 1. Run the physics engine at full resolution
    pdf_at_time = evaluate_total_pdf(
        target_map, lanes, target_time, duration, time_steps
    )
    pdf_df = pdf_at_time(target_time).collect()
    x_axes = pdf_df.select("x").to_series().unique().sort()
    y_axes = pdf_df.select("y").to_series().unique().sort()
    n_x, n_y = len(x_axes), len(y_axes)

    # 2. Pivot to (n_y, n_x) matrix; normalize so the discrete sum equals 1
    raw = pdf_df.sort(["y", "x"])["total_pdf"].to_numpy().astype(np.float64)
    matrix = raw.reshape(n_y, n_x)
    total = matrix.sum()
    if total > 0:
        matrix /= total

    # 3. Transform to P(at least one target within the intercept radius)
    grid_spacing = float(target_map.map_size) / (target_map.samples - 1)
    matrix = _at_least_one_probability(matrix, grid_spacing, _INTERCEPT_RADIUS, num_targets)

    # 4. Downsample by direct matrix slicing
    prob_ds = matrix[::downsample_step, ::downsample_step]
    x_ds = x_axes.to_numpy()[::downsample_step]
    y_ds = y_axes.to_numpy()[::downsample_step]
    n_y_ds, n_x_ds = prob_ds.shape

    # 5. Flatten to a Polars DataFrame and drop non-finite cells
    pdf_df = pl.DataFrame(
        {
            "x": np.tile(x_ds, n_y_ds),
            "y": np.repeat(y_ds, n_x_ds),
            "total_pdf": prob_ds.flatten(),
        }
    ).filter(
        pl.col("total_pdf").is_not_null(),
        pl.col("total_pdf").is_not_nan(),
        pl.col("total_pdf").is_finite(),
    )

    # 6. Map spatial coordinates to ECharts array indices
    x_map_df = pl.DataFrame({"x": pl.Series(x_ds)}).with_row_index("x_index")
    y_map_df = pl.DataFrame({"y": pl.Series(y_ds)}).with_row_index("y_index")
    pdf_df = pdf_df.join(x_map_df, on="x", how="inner").join(
        y_map_df, on="y", how="inner"
    )

    # 7. Format as ECharts expects: [x_index, y_index, value]
    echarts_data = sorted(
        [
            [row["x_index"], row["y_index"], row["total_pdf"]]
            for row in pdf_df.select(
                pl.col("x_index").cast(pl.Int32),
                pl.col("y_index").cast(pl.Int32),
                pl.col("total_pdf").round(6),
            ).to_dicts()
        ],
        key=lambda item: (item[0], item[1]),
    )

    # 8. Safely compute max_val (guards against NaN in JSON serialization)
    safe_max_val = float(
        pdf_df.select(pl.col("total_pdf").max()).to_series().to_list()[0]
    )

    return json.dumps(
        {
            "x": pl.Series(x_ds).round(4).to_list(),
            "y": pl.Series(y_ds).round(4).to_list(),
            "data": echarts_data,
            "max_val": safe_max_val,
        }
    )


@router.websocket("/ws/tactical_map/{target_id}")
async def tactical_map_stream(
    websocket: WebSocket,
    target_id: str,
    sim_state: SimulationState = Depends(get_sim_state),
    param_state: PDFParamState = Depends(get_param_state),
):
    """
    Manages the WebSocket connection for real-time map updates.

    Serves precomputed frames from _frame_cache when available; falls back
    to on-demand computation via asyncio.to_thread otherwise.

    Args:
        websocket (WebSocket): The active client socket connection.
        target_id (str): The UUID of the current target specification.
    """
    await websocket.accept()

    latest_requested_rel_secs: int | None = None

    current_target_specs = sim_state.target_specs.get(target_id)
    if not current_target_specs:
        await websocket.send_text(
            json.dumps({"error": "Target specifications not found."})
        )
        await websocket.close()
        return

    current_map_obj = sim_state.target_maps.get(
        current_target_specs.map_id if current_target_specs.map_id else ""
    )
    if not current_map_obj:
        await websocket.send_text(
            json.dumps({"error": "Current map configuration not found."})
        )
        await websocket.close()
        return

    target_map_str: str = current_map_obj.model_dump_json()
    start_time: str = param_state.start_time
    time_duration: timedelta = timedelta(hours=param_state.duration_hours)
    time_steps: int = param_state.time_steps
    downsample_step: int = param_state.downsample_step
    num_targets: int = _num_targets_for_class(
        current_map_obj, current_target_specs.category
    )

    async def process_and_send():
        nonlocal latest_requested_rel_secs

        while True:
            if latest_requested_rel_secs is None:
                await asyncio.sleep(0.01)
                continue

            rel_secs = latest_requested_rel_secs
            latest_requested_rel_secs = None

            try:
                # Fast path: serve from precomputed cache
                payload_json = get_nearest_frame(target_id, rel_secs)

                if payload_json is None:
                    # Fallback: compute on demand in a thread
                    target_time = datetime.fromisoformat(start_time) + timedelta(
                        seconds=rel_secs
                    )
                    payload_json = await asyncio.to_thread(
                        get_echarts_payload,
                        target_map_str=target_map_str,
                        target_specs_id=target_id,
                        target_time=target_time,
                        duration=time_duration,
                        time_steps=time_steps,
                        downsample_step=downsample_step,
                        num_targets=num_targets,
                    )

                await websocket.send_text(payload_json)

            except Exception as e:
                print(f"Error evaluating PDF state: {e}")

    sender_task = asyncio.create_task(process_and_send())

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if "rel_seconds" in message:
                latest_requested_rel_secs = int(message["rel_seconds"])

    except WebSocketDisconnect:
        sender_task.cancel()
        print("Tactical map client disconnected.")
