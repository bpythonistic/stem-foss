"""This file contains fixtures for testing the FastAPI application.

It sets up a test database, creates a test client, and provides a fixture for an authenticated user.
The fixtures ensure that each test runs in isolation with a clean database state.
"""

from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy.pool import StaticPool
from yaml import safe_load

from app.main import app
from app.schemas.sqlmodels import get_session

CONFIG_FILE_PATH = Path(__file__).parent / "testdata" / "testconfig.yaml"


@pytest.fixture(scope="session")
def engine():
    """
    Fixture for creating a test database engine.

    :return: A SQLModel engine for the test database.
    :rtype: Engine
    """
    return create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )


@pytest.fixture(scope="session")
def create_db_and_tables(engine):
    """
    Fixture for creating the test database and tables.

    :param engine: The test database engine.
    """
    SQLModel.metadata.create_all(engine)


@pytest.fixture(scope="function")
def session(engine, create_db_and_tables) -> Generator[Session, None, None]:
    """
    Fixture for creating a test database session.

    :param engine: The test database engine.
    :param create_db_and_tables: The fixture for creating the test database and tables.
    :return: A SQLModel session for the test database.
    :rtype: Session
    """
    with Session(engine) as s:
        yield s

    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="module")
def config() -> dict:
    """
    Fixture for loading test data from a YAML file.

    :return: A dictionary containing the test data.
    :rtype: dict
    """
    with open(CONFIG_FILE_PATH, "r") as f:
        data = safe_load(f)["data"]
    return data


@pytest.fixture(scope="module")
def client(session: Session) -> Generator[TestClient, None, None]:
    """
    Fixture for creating a test client for the FastAPI application.

    :param session: The test database session.
    :return: A TestClient instance for the FastAPI application.
    :rtype: TestClient
    """

    def get_session_override():
        with Session(session.bind) as s:
            yield s

    app.dependency_overrides[get_session] = get_session_override

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
