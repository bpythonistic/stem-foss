"""
This module defines the data models for the application using Pydantic.

It includes:
"""

import os
from uuid import uuid4
from typing import Annotated, Generator

# from typing import Optional
from fastapi.params import Depends
from sqlmodel import SQLModel, Field, Session, create_engine

DEFAULT_CONNECTION_STRING = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://postgres@localhost:5432/nyquist_db"
)
