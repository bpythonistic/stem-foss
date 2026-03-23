"""
This module defines the main FastAPI application and database connection utilities.

It includes:
- A FastAPI application instance.
- API Endpoints
"""

import os

# from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select

from app.schemas.sqlmodels import (
    SessionDep,
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
