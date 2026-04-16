"""
This module defines Pydantic models for data validation
    and serialization in the application. These models
    are used to ensure that the data being processed
    by the API endpoints adheres to the expected structure
    and types. The models include configurations for map
    state, cache management, and timing settings for simulations.

Contains:
- GenericMessage: A simple model for returning string messages in API responses.
"""

from datetime import datetime, timedelta

from pydantic import BaseModel, Field

from app.schemas.sqlmodels import Map, Target


class GenericMessage(BaseModel):
    """
    A generic message model for simple string responses.

    Attributes:
        message (str): A simple message string.
    """

    message: str = Field(..., description="A simple message string.")


class SimulationState(BaseModel):
    """
    A model to represent the state of the simulation,
        including timing and configuration parameters.
    Attributes:
        target_maps (dict[str, Map]):
            A dictionary mapping map IDs to their corresponding map configurations.
        target_specs (dict[str, Target]):
            A dictionary mapping target IDs to their corresponding specifications.
        start_time (datetime):
            The starting time of the simulation.
        duration (timedelta):
            The total duration of the simulation.
        time_steps (int):
            The number of time steps in the simulation.
        downsample_step (int):
            The step size for downsampling data in the simulation.
    """

    target_maps: dict[str, Map]
    target_specs: dict[str, Target]
    start_time: datetime = Field(
        ..., description="The starting time of the simulation."
    )
    duration: timedelta = Field(
        ..., description="The total duration of the simulation."
    )
    time_steps: int = Field(
        ..., description="The number of time steps in the simulation.", ge=1
    )
    downsample_step: int = Field(
        ...,
        description="The step size for downsampling data in the simulation.",
        ge=1,
    )


# Instantiate a global singleton
sim_state = SimulationState(
    target_maps={},
    target_specs={},
    start_time=datetime.now() - timedelta(hours=48),
    duration=timedelta(hours=24),
    time_steps=50,
    downsample_step=4,
)


def get_sim_state() -> SimulationState:
    return sim_state
