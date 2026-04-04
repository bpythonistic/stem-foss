"""
Provides helper functions for formatting and caching PDFs.

- save_map_state: Caches the lane configurations to Parquet.
- get_echarts_payload: Formats PDF matrices for frontend UI.
- tactical_map_stream: WebSocket endpoint for UI streaming.
"""

import asyncio
import json
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import polars as pl
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.features.target_mechanics import (
    describe_lanes,
    evaluate_total_pdf,
    generate_map_heat_points,
)
from app.schemas.sqlmodels import Map as TargetMap
from app.schemas.sqlmodels import Target

router = APIRouter()

PARQUET_DIR = Path(__file__).parent.parent / "data" / "parquet_cache"


def save_map_state(
    target_map: TargetMap, target_specs: Target, parquet_path: Path | None = None
) -> None:
    """
    Caches the static map routes to a file for rapid loading.

    Args:
        target_map (TargetMap): The active
            operational zone map.
        target_specs (Target): The stats
            used to calculate variance.
        parquet_path (Path | None): The path where the Parquet file will be saved.
    Returns:
        None: Operations are saved directly
            to the local disk.
    """

    heat_points = generate_map_heat_points(target_map)
    lanes_lf = describe_lanes(target_map, heat_points, target_specs)
    data_dir = PARQUET_DIR if parquet_path is None else parquet_path
    lanes_lf.collect().write_parquet(
        data_dir / f"current_lanes_for_{target_specs.id}.parquet"
    )


def clear_parquet_cache(parquet_path: Path | None = None) -> None:
    """
    Clears all cached Parquet files from the specified directory.

    Args:
        parquet_path (Path | None): The path to the directory
            containing Parquet files. If None, defaults to
            the standard cache directory.

    Returns:
        None: The function performs file deletion directly
            on the local disk.
    """
    data_dir = PARQUET_DIR if parquet_path is None else parquet_path
    for file in data_dir.glob("current_lanes_for_*.parquet"):
        try:
            file.unlink()
            print(f"Deleted cached file: {file}")
        except Exception as e:
            print(f"Error deleting file {file}: {e}")


@lru_cache(maxsize=128)
def get_echarts_payload(
    target_map_str: str,
    target_specs_id: str,
    target_time: datetime,
    duration: timedelta,
    time_steps: int,
    downsample_step: int = 4,
) -> str:
    """
    Transforms and downsamples the raw PDF into frontend JSON.

    Args:
        target_map_str (str): The JSON
            string of the active map.
        target_specs_id (str): The UUID
            for locating the lane file.
        target_time (datetime): The exact
            time to evaluate the PDF.
        duration (timedelta): The total
            cycle duration length.
        time_steps (int): The resolution
            of the time simulation.
        downsample_step (int): The scaling
            factor for matrix size.
    Returns:
        str: A serialized JSON payload
            configured for ECharts.
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

    # 1. Run the core physics engine
    pdf_at_time = evaluate_total_pdf(
        target_map, lanes, target_time, duration, time_steps
    )
    pdf_df = pdf_at_time(target_time).collect()
    samples = target_map.samples

    # 2. Post-process the Polars DataFrame: filter, round, and add indices
    pdf_df = (
        pdf_df.select("x", "y", "total_pdf")
        .with_columns(
            x_index=pl.arange(0, samples, dtype=pl.Int32),
            y_index=pl.arange(0, samples, dtype=pl.Int32),
        )
        .with_columns(
            total_pdf=pl.when(pl.col("total_pdf") < 0.001)
            .then(None)
            .otherwise(pl.col("total_pdf").round(4))
        )
        .drop_nulls(subset=["total_pdf"])
    )

    # 3. Downsample the grid for performance (e.g., from 100x100 to 25x25)
    pdf_df = pdf_df.with_columns(
        x_down=pl.when(pl.col("x_index") // downsample_step == 0)
        .then(None)
        .otherwise(pl.col("x_index") // downsample_step),
        y_down=pl.when(pl.col("y_index") // downsample_step == 0)
        .then(None)
        .otherwise(pl.col("y_index") // downsample_step),
    ).drop_nulls(subset=["x_down", "y_down"])

    # 4. Format exactly as ECharts expects: [x_index, y_index, value]
    echarts_data = (
        pdf_df.select(
            pl.col("x_index").unique().sort().cast(pl.Int32),
            pl.col("y_index").unique().sort().cast(pl.Int32),
            pl.col("total_pdf"),
        )
        .to_numpy()
        .tolist()
    )

    # 5. Serialize the entire payload as a JSON string and cache it.
    # This avoids Pydantic parsing overhead on the FastAPI side.
    return json.dumps(
        {
            "x": pdf_df.select(pl.col("x_index")).to_series().to_list(),
            "y": pdf_df.select(pl.col("y_index")).to_series().to_list(),
            "data": echarts_data,
            "max_val": pdf_df.select(pl.col("total_pdf"))
            .max()
            .to_series()
            .to_list()[0],
        },
    )


@router.websocket("/ws/tactical-map/{target_id}")
async def tactical_map_stream(websocket: WebSocket, target_id: str):
    """
    Manages the WebSocket connection for real-time map updates.

    Args:
        websocket (WebSocket): The active
            client socket connection.
        target_id (str): The UUID of the
            current target specification to load.
    Returns:
        None: Manages the async event
            loop for the connection.
    """
    await websocket.accept()

    # State pointer for the latest time requested by the client
    latest_requested_time = None
    current_target_specs = websocket.app.state.target_specs.get(target_id)
    if not current_target_specs:
        await websocket.send_text(
            json.dumps({"error": "Target specifications not found."})
        )
        await websocket.close()
        return
    current_map_obj = websocket.app.state.target_maps.get(current_target_specs.map_id)
    if not current_map_obj:
        await websocket.send_text(
            json.dumps({"error": "Current map configuration not found."})
        )
        await websocket.close()
        return
    target_map_str: str = current_map_obj.model_dump_json()
    start_time: datetime = websocket.app.state.start_time
    time_duration: timedelta = websocket.app.state.duration
    time_steps: int = websocket.app.state.time_steps
    downsample_step: int = websocket.app.state.downsample_step

    async def process_and_send():
        """
        Evaluates the latest time request and streams the payload.

        Returns:
            None: Runs continuously in the
                background event loop.
        """
        nonlocal latest_requested_time

        while True:
            # Sleep briefly if no new time has been requested
            if latest_requested_time is None:
                await asyncio.sleep(0.01)
                continue

            # Lock in the target time and clear the pointer
            time_to_process = latest_requested_time
            latest_requested_time = None

            try:
                # Offload the synchronous CPU-bound math to a separate thread
                # This prevents the FastAPI event loop from locking up!
                payload_json = await asyncio.to_thread(
                    get_echarts_payload,
                    target_map_str=target_map_str,
                    target_specs_id=target_id,
                    duration=time_duration,
                    time_steps=time_steps,
                    target_time=time_to_process,
                    downsample_step=downsample_step,
                )

                # Send the pre-serialized string
                await websocket.send_text(payload_json)

            except Exception as e:
                print(f"Error evaluating PDF state: {e}")
                # Optional: Send an error payload back to the client

    # Spin up the background worker for this specific client connection
    sender_task = asyncio.create_task(process_and_send())

    try:
        while True:
            # Wait for incoming slider data from React
            data = await websocket.receive_text()
            message = json.loads(data)

            if "rel_seconds" in message:
                # Update the pointer. We don't await the math here;
                # we just let the background task pick it up on its next loop.
                latest_requested_time = start_time + timedelta(
                    seconds=message["rel_seconds"]
                )

    except WebSocketDisconnect:
        # Client disconnected (closed browser, refreshed, etc.)
        sender_task.cancel()
        print("Tactical map client disconnected.")
