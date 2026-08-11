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

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select

from app.features.target_mechanics import get_target_classes
from app.features.target_pdf_helpers import clear_parquet_cache, save_map_state
from app.features.target_pdf_helpers import router as target_pdf_router
from app.schemas.pydmodels import (
    GenericMessage,
    DefaultTargetRequest,
    PDFParamState,
    SimulationState,
    get_param_state,
    get_sim_state,
)
from app.schemas.sqlmodels import (
    Map,
    SessionDep,
    Target,
    DefaultTargets,
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
    result = session.exec(statement)
    user_obj = result.first()
    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user_obj


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


@app.get("/maps/")
def get_maps(session: SessionDep) -> list[Map]:
    """
    Retrieves all existing tactical map configurations from the database.

    Args:
        session (SessionDep): The injected database session.

    Returns:
        list[Map]: A list of all requested map data from the database.
    """
    statement = select(Map).order_by(Map.name)
    result = session.exec(statement)
    map_objs = list(result.fetchall())
    return map_objs


@app.post("/targets/custom/", status_code=status.HTTP_201_CREATED)
def create_targets(
    target: Target,
    session: SessionDep,
    current_sim_state: SimulationState = Depends(get_sim_state),
) -> Target:
    """
    Registers a new target specification into the database.

    Args:
        target (Target): The target schema
            to register and save.
        session (SessionDep): The injected
            database session.
        current_sim_state (SimulationState):
            The current simulation state (injected).
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
    current_sim_state.target_maps[target_map.id] = target_map
    current_sim_state.target_specs[target.id] = target

    return target


@app.post("/targets/default/", status_code=status.HTTP_201_CREATED)
def create_default_targets(
    default_target_request: DefaultTargetRequest,
    session: SessionDep,
    current_sim_state: SimulationState = Depends(get_sim_state),
) -> DefaultTargets:
    """
    Initializes and registers the 3 default
        target specifications.

    Args:
        default_target_request (DefaultTargetRequest):
            The request body containing user ID and map ID.
        session (SessionDep):
            The injected database session.
        current_sim_state (SimulationState):
            The current simulation state (injected).
    Returns:
        DefaultTargets:
            The confirmed default targets with generated UUIDs.
    """

    user_id = default_target_request.user_id
    map_id = default_target_request.map_id
    default_target_specs = get_target_classes(user_id, map_id)

    for target in default_target_specs:
        session.add(target)
    session.commit()
    for target in default_target_specs:
        session.refresh(target)

    default_target_ids = [target.id for target in default_target_specs]
    for target in default_target_specs:
        query = select(Map).where(Map.id == target.map_id)
        target_map = session.exec(query).first()
        if not target_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Map not found"
            )
        if target_map.id not in current_sim_state.target_maps:
            current_sim_state.target_maps[target_map.id] = target_map
        current_sim_state.target_specs[target.id] = target

    default_targets = DefaultTargets(
        user_id=user_id,
        small_target_id=default_target_ids[0],
        medium_target_id=default_target_ids[1],
        large_target_id=default_target_ids[2],
    )
    session.add(default_targets)
    session.commit()
    session.refresh(default_targets)

    return default_targets


@app.get("/targets/")
def get_targets(session: SessionDep) -> list[Target]:
    """
    Retrieves all existing target specifications from the database.

    Args:
        session (SessionDep): The injected database session.
    Returns:
        list[Target]: A list of all requested target specifications from the database.
    """
    statement = select(Target).order_by(Target.name)
    result = session.exec(statement)
    target_objs = list(result.fetchall())
    return target_objs


@app.put("/save_target_state/{target_specs_id}")
def save_target_state(
    target_specs_id: str,
    session: SessionDep,
    load_from_db: bool = False,
    current_sim_state: SimulationState = Depends(get_sim_state),
    current_param_state: PDFParamState = Depends(get_param_state),
) -> GenericMessage:
    """
    Caches the hot spot configuration for a given target specification.

    Args:
        target_specs_id (str): The UUID of the
            target specification to cache.
        load_from_db (bool): Whether to load the target
            specification from the database.
    Returns:
        GenericMessage: A success message payload
            confirming caching.
    """
    if load_from_db:
        statement = select(Target).order_by(Target.name)
        result = session.exec(statement)
        target_objs = [obj for obj in result.fetchall() if obj.id == target_specs_id]
        if not target_objs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target specifications not found.",
            )
        query = select(Map).where(Map.id == target_objs[0].map_id)
        target_map = session.exec(query).first()
        if not target_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated map not found.",
            )
        current_sim_state.target_maps[target_map.id] = target_map
        current_sim_state.target_specs[target_objs[0].id] = target_objs[0]

    if not current_sim_state.target_maps or not current_sim_state.target_specs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target specifications or map not found in current simulation state.",
        )
    target_specs = current_sim_state.target_specs.get(target_specs_id)
    if not target_specs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target specifications not found.",
        )

    target_map = current_sim_state.target_maps.get(
        target_specs.map_id if target_specs.map_id else ""
    )
    if not target_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Associated map not found."
        )

    try:
        save_map_state(target_map, target_specs, current_param_state)
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
    new_param_state: PDFParamState,
    current_param_state: PDFParamState = Depends(get_param_state),
) -> GenericMessage:
    """
    Sets the global timing configuration for the simulation.

    Args:
        new_param_state (PDFParamState): The new PDF parameter state to configure.
        current_param_state (PDFParamState): The current PDF parameter state (injected).
    Returns:
        GenericMessage: A success message payload confirming configuration.
    """

    current_param_state.start_time = new_param_state.start_time
    current_param_state.duration_hours = new_param_state.duration_hours
    current_param_state.time_steps = new_param_state.time_steps
    current_param_state.downsample_step = new_param_state.downsample_step

    return GenericMessage(message="PDF parameters configured.")
