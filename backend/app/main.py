"""
This module defines the main FastAPI application and database connection utilities.

It includes:
- A FastAPI application instance.
- API Endpoints
"""

import os
from datetime import datetime, timedelta

# from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select

from app.features.target_pdf_helpers import router as target_pdf_router
from app.features.target_pdf_helpers import save_map_state
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
def read_root():
    """
    Root endpoint to verify that the API is running.

    Returns:
        dict: A simple message indicating that the API is operational.
    """
    return {"message": "Welcome to the Project Netfall Backend API!"}


@app.post("/users/")
def create_user(user: User, session: SessionDep) -> User:
    """
    Create a new user in the database.

    Args:
        user (User): The user object containing the details of the user to create.
        session (SessionDep): The database session dependency.

    Returns:
        User: The created user object with an assigned ID.
    """
    existing_user = session.exec(select(User).where(User.name == user.name)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@app.get("/users/{user_name}")
def get_user(user_name: str, session: SessionDep) -> User:
    """
    Retrieve a user by their name.

    Args:
        user_name (str): The name of the user to retrieve.
        session (SessionDep): The database session dependency.

    Returns:
        User: The user object if found.

    Raises:
        HTTPException: If the user is not found in the database.
    """
    statement = select(User).where(User.name == user_name)
    result = session.exec(statement).first()
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@app.post("/maps/")
def create_map(target_map: Map, target_id: str, session: SessionDep) -> Map:
    """
    Create a new map in the database.

    Args:
        target_map (Map): The map object containing the details of the map to create.
        target_id (str): The ID of the target associated with the map.
        session (SessionDep): The database session dependency.

    Returns:
        Map: The created map object with an assigned ID.
    """

    session.add(target_map)
    session.commit()
    session.refresh(target_map)
    app.state.current_map = target_map

    return target_map


@app.post("/targets/{map_id}")
def create_targets(target: Target, map_id: str, session: SessionDep) -> Target:
    """
    Create a new target in the database.
        This endpoint is designed to be called after a map has been created,
        and it will save the target specifications to the application
        state for use in PDF calculations.

    Args:
        target (Target): The target object containing the details of the target to create.
        map_id (str): The ID of the map associated with the target.
        session (SessionDep): The database session dependency.

    Returns:
        Target: The created target object with an assigned ID.
    """

    session.add(target)
    session.commit()
    session.refresh(target)

    query = select(Map).where(Map.id == map_id)
    target_map = session.exec(query).first()
    if not target_map:
        raise HTTPException(status_code=404, detail="Map not found")
    app.state.current_map = target_map
    app.state.current_target_specs = target

    save_map_state(target_map, target)

    return target


@app.put("/configure_pdf_parameters/")
def configure_pdf_parameters(
    start_time: datetime = datetime.now() - timedelta(hours=48),
    duration: timedelta = timedelta(hours=24),
    time_steps: int = 50,
    downsample_step: int = 4,
) -> dict:
    """
    Endpoint to configure PDF parameters.

    Args:
        start_time (datetime): The starting time for the PDF evaluation.
        duration (timedelta): The total duration for which to evaluate the PDF.
        time_steps (int): The number of time steps to consider in the evaluation.
        downsample_step (int): The step size for downsampling the PDF grid.
    Returns:
        dict: A message confirming that the PDF parameters have been configured.
    """

    app.state.start_time = start_time
    app.state.duration = duration
    app.state.time_steps = time_steps
    app.state.downsample_step = downsample_step

    return {"message": "PDF parameters configured."}
