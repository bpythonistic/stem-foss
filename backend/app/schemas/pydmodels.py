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

from pydantic import BaseModel, Field


class GenericMessage(BaseModel):
    """
    A generic message model for simple string responses.

    Attributes:
        message (str): A simple message string.
    """

    message: str = Field(..., description="A simple message string.")
