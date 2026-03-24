"""
This module contains helper functions for handling PDF files related to target data.
    It includes functions for extracting text from PDFs, converting PDFs to images,
    and other utilities that assist in processing PDF files for the application.

"""

import asyncio
import json
from datetime import datetime, timedelta
from functools import lru_cache

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


def save_map_state(target_map: TargetMap, target_specs: Target) -> None:
    """
    Evaluates the current state of the target map
        and saves the lane descriptions to a Parquet file.

    Args:
    - target_map (TargetMap): The target map containing the
        current state of the map.
    - target_specs (Target): The specifications of the target,
        which may include parameters such as speed, size,
        and other relevant attributes.
    Returns:
    - None: This function does not return any value.
        It performs its operations and saves the
        lane descriptions to a Parquet file named
        "current_lanes_for_{target_specs.id}.parquet".
    """

    heat_points = generate_map_heat_points(target_map)
    lanes_lf = describe_lanes(target_map, heat_points, target_specs)
    lanes_lf.collect().write_parquet(f"current_lanes_for_{target_specs.id}.parquet")


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
    Evaluates the math, downsamples the grid, formats for ECharts,
    and caches the serialized JSON string to bypass Pydantic overhead.

    Args:
        target_map (TargetMap): The target map with its associated data.
        target_time (datetime): The specific time at which to evaluate the PDF.
        duration (timedelta): The total duration for which to evaluate the PDF.
        time_steps (int): The number of time steps to consider in the evaluation.
        downsample_step (int): The factor by which to downsample the grid.
    Returns:
        str: A JSON string formatted for ECharts consumption,
            containing x/y indices, PDF values,
            and the maximum PDF value for scaling.
    """

    target_map = TargetMap(**json.loads(target_map_str))
    lanes = pl.scan_parquet(f"current_lanes_for_{target_specs_id}.parquet")

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


@router.websocket("/ws/tactical-map")
async def tactical_map_stream(websocket: WebSocket):
    """
    WebSocket endpoint for streaming tactical map PDF
        data to the client in real-time.
        This endpoint listens for incoming
        messages containing the relative time (in seconds)

    """
    await websocket.accept()

    # State pointer for the latest time requested by the client
    latest_requested_time = None
    target_map_str: str = websocket.app.state.current_map.model_dump_json()
    target_specs_id: str = websocket.app.state.current_target_specs.id
    start_time: datetime = websocket.app.state.start_time
    time_duration: timedelta = websocket.app.state.duration
    time_steps: int = websocket.app.state.time_steps
    downsample_step: int = websocket.app.state.downsample_step

    async def process_and_send():
        """
        Background task that processes the latest state and ignores stale requests.

        This function runs in an infinite loop, checking for the
            latest requested time from the client. If a new time
            has been requested, it evaluates the PDF for that
            time and sends the result back to the client. If no
            new time has been requested, it sleeps briefly to avoid busy-waiting.
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
                    target_specs_id=target_specs_id,
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
