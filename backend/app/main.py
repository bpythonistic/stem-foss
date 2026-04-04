"""
Defines the FastAPI application and REST API endpoints.

- read_root: Health check endpoint.
- create_user: Registers a new user.
- get_user: Retrieves a user profile.
- create_map: Registers a new map.
- create_targets: Registers targets and triggers generation.
- configure_pdf_parameters: Sets global simulation parameters.
"""

import os
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select

from app.features.target_pdf_helpers import clear_parquet_cache, save_map_state
from app.features.target_pdf_helpers import router as target_pdf_router
from app.schemas.pydmodels import GenericMessage
from app.schemas.sqlmodels import (
    Map,
    SessionDep,
    Target,
    User,
)

FRONTEND_ORIGINS = [
    os.getenv("FRONTEND_URL", "http://localhost:5173"),
    os.getenv("BACKEND_URL", "http://localhost:8000"),
    os.getenv("HOST_URL", "http://localhost"),
    os.getenv("WEBSOCKET_URL", "ws://localhost:8000"),
]

app = FastAPI(
    title="Project Netfall Backend API",
    description="API for the Project Netfall backend",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(target_pdf_router)


@app.get("/")
def read_root() -> GenericMessage:
    """
    Verifies that the backend API is online and responding.

    Returns:
        GenericMessage: A health check success
            message payload.
    """
    return GenericMessage(message="Welcome to the Project Netfall Backend API!")


@app.post("/users/", status_code=status.HTTP_201_CREATED)
def create_user(user: User, session: SessionDep) -> User:
    """
    Registers a new player profile into the Postgres database.

    Args:
        user (User): The desired profile
            schema to be registered.
        session (SessionDep): The injected
            database session.
    Returns:
        User: The confirmed profile
            with a generated UUID.
    """
    existing_user = session.exec(select(User).where(User.name == user.name)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists"
        )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@app.get("/users/{user_name}")
def get_user(user_name: str, session: SessionDep) -> User:
    """
    Retrieves an existing player profile from the database.

    Args:
        user_name (str): The exact display
            name of the profile.
        session (SessionDep): The injected
            database session.
    Returns:
        User: The requested profile
            data from the database.
    """
    statement = select(User).where(User.name == user_name)
    result = session.exec(statement).first()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return result


@app.post("/maps/", status_code=status.HTTP_201_CREATED)
def create_map(target_map: Map, session: SessionDep) -> Map:
    """
    Initializes and registers a new tactical map environment.

    Args:
        target_map (Map): The map schema
            to register and save.
        session (SessionDep): The injected
            database session.
    Returns:
        Map: The confirmed map schema
            with a generated UUID.
    """

    session.add(target_map)
    session.commit()
    session.refresh(target_map)

    return target_map


@app.post("/targets/", status_code=status.HTTP_201_CREATED)
def create_targets(target: Target, session: SessionDep) -> Target:
    """
    Registers an enemy drone and triggers lane caching.

    Args:
        target (Target): The target schema
            to register and save.
        session (SessionDep): The injected
            database session.
    Returns:
        Target: The confirmed target
            with a generated UUID.
    """

    session.add(target)
    session.commit()
    session.refresh(target)

    query = select(Map).where(Map.id == target.map_id)
    target_map = session.exec(query).first()
    if not target_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Map not found"
        )
    if not (hasattr(app.state, "target_maps") and app.state.target_maps):
        app.state.target_maps = {target_map.id: target_map}
    elif target_map.id not in app.state.target_maps:
        app.state.target_maps.update({target_map.id: target_map})
    if not (hasattr(app.state, "target_specs") and app.state.target_specs):
        app.state.target_specs = {target.id: target}
    elif target.id not in app.state.target_specs:
        app.state.target_specs.update({target.id: target})

    return target


@app.put("/save_target_state/{target_specs_id}")
def save_target_state(target_specs_id: str) -> GenericMessage:
    """
    Caches the lane configuration for a given target specification.

    Args:
        target_specs_id (str): The UUID of the
            target specification to cache.
    Returns:
        GenericMessage: A success message payload
            confirming caching.
    """
    if not (hasattr(app.state, "target_maps") and hasattr(app.state, "target_specs")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No map or target specifications found in application state.",
        )

    target_map = app.state.target_maps.get(
        app.state.target_specs[target_specs_id].map_id
    )
    target_specs = app.state.target_specs[target_specs_id]

    if not target_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Associated map not found."
        )

    try:
        save_map_state(target_map, target_specs)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving map state: {e}",
        )

    return GenericMessage(
        message=f"Map state for target_specs_id {target_specs_id} saved."
    )


@app.delete("/clear_cache/")
def clear_cache() -> GenericMessage:
    """
    Clears all cached Parquet files.

    Returns:
        GenericMessage: A success message payload confirming cache clearing.
    """
    try:
        clear_parquet_cache()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing cache: {e}",
        )

    return GenericMessage(message="Cache cleared.")


@app.put("/configure_pdf_parameters/")
def configure_pdf_parameters(
    hours_before_now: float = 48.0,
    duration_hours: float = 24.0,
    time_steps: int = 50,
    downsample_step: int = 4,
) -> GenericMessage:
    """
    Sets the global timing configuration for the simulation.

    Args:
        hours_before_now (float): The number of hours
            before the current time to start the simulation.
        duration_hours (float): The total duration
            of the simulation in hours.
        time_steps (int): The resolution
            of the time simulation.
        downsample_step (int): The scaling
            factor for matrix size.
    Returns:
        GenericMessage: A success message payload
            confirming configuration.
    """

    app.state.start_time = datetime.now() - timedelta(hours=hours_before_now)
    app.state.duration = timedelta(hours=duration_hours)
    app.state.time_steps = time_steps
    app.state.downsample_step = downsample_step

    return GenericMessage(message="PDF parameters configured.")
