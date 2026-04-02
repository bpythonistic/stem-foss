"""This file contains fixtures for testing the FastAPI application.

It sets up a test database, creates a test client,
and provides a fixture for an authenticated user.
The fixtures ensure that each test runs in isolation
with a clean database state.
"""

from pathlib import Path
from typing import Generator

import pytest
from app.main import app
from app.schemas.sqlmodels import get_session
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine
from yaml import safe_load

CONFIG_FILE_PATH = Path(__file__).parent / "testdata" / "testconfig.yaml"


@pytest.fixture
def engine() -> Engine:
    """
    Fixture for creating a test database engine.

    Returns:
        Engine: A SQLAlchemy engine for the test database.
    """
    return create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )


@pytest.fixture
def create_db_and_tables(engine: Engine):
    """
    Fixture for creating the test database and tables.

    Args:
        engine (Engine): The test database engine.
    """
    SQLModel.metadata.create_all(engine)


@pytest.fixture
def session(engine: Engine, create_db_and_tables) -> Generator[Session, None, None]:
    """
    Fixture for creating a test database session.

    Args:
        engine (Engine): The test database engine.
        create_db_and_tables: The fixture for
            creating the test database and tables.
    Returns:
        Session: A SQLModel session for the test database.
    """
    with Session(engine) as s:
        yield s

    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="module")
def config() -> dict:
    """
    Fixture for loading test data from a YAML file.

    Returns:
        dict: A dictionary containing the test data.
    """
    with open(CONFIG_FILE_PATH, "r") as f:
        data = safe_load(f)["data"]
    return data


@pytest.fixture
def client(session: Session) -> Generator[TestClient, None, None]:
    """
    Fixture for creating a test client for the FastAPI application.

    Args:
        session (Session): The test database session.
    Returns:
        TestClient: A TestClient instance for the FastAPI application.
    """

    def get_session_override() -> Session:
        """
        Override function for the get_session dependency.

        Returns:
            Session: The test database session.
        """
        return session

    app.dependency_overrides[get_session] = get_session_override

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
