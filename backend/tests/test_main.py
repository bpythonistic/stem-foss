"""This file contains tests for the main application functionality.

It includes tests for:
- Database connection
- API endpoints
- User authentication and management
"""

import json
from typing import Self, Any

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

import app.schemas.sqlmodels as sch
from app.features.target_mechanics import get_target_classes


class DataPair(BaseModel):
    """
    A class to represent a pair of input data and expected output for testing.

    Attributes:
        expected_output (tuple[int, dict[str, Any]]):
            The expected HTTP status code and response for the test case.
    """

    expected_output: tuple[int, dict[str, Any]] = (status.HTTP_201_CREATED, {})


class UserPair(DataPair):
    """
    A class to represent a pair of user input data and expected output for testing.

    Attributes:
        input_data (sch.User): The user data to be used as input for the test case.
    """

    input_data: sch.User


class MapPair(DataPair):
    """
    A class to represent a pair of map input data and expected output for testing.

    Attributes:
        input_data (sch.Map): The map data to be used as input for the test case.
    """

    input_data: sch.Map


class TargetPair(DataPair):
    """
    A class to represent a pair of target input data and expected output for testing.

    Attributes:
        input_data (sch.Target): The target data to be used as input for the test case.
    """

    input_data: sch.Target


class DataModel(BaseModel):
    """
    A class to represent the data model for testing.

    Attributes:
        users (list[UserPair]): A list of user data for testing.
        target_map (MapPair | None): The map data for testing.
        targets (list[TargetPair]): A list of target data for testing.
    """

    users: list[UserPair] = Field(default_factory=list)
    target_map: MapPair | None
    targets: list[TargetPair] = Field(default_factory=list)


class DataForTests:
    """
    A class containing all test data for the main application tests.

    Attributes:
        USER_DATA (dict[str, UserPair]): A dictionary of UserPair instances
            containing test data for user-related tests.
        TARGET_MAP_DATA (MapPair): A MapPair instance containing test data
            for map-related tests.
        TARGET_DATA (tuple[sch.Target, sch.Target, sch.Target]):
            A tuple of Target instances containing test data
            for target-related tests.
    """

    USER_DATA: dict[str, UserPair] = {
        "valid_user_1": UserPair(
            input_data=sch.User(id="01", name="testuser1"),
            expected_output=(
                status.HTTP_201_CREATED,
                {
                    "id": ...,
                    "name": "testuser1",
                    "class_name": None,
                },
            ),
        ),
        "valid_user_2": UserPair(
            input_data=sch.User(id="02", name="testuser2"),
            expected_output=(
                status.HTTP_201_CREATED,
                {
                    "id": ...,
                    "name": "testuser2",
                    "class_name": None,
                },
            ),
        ),
        "duplicate_user": UserPair(
            input_data=sch.User(id="03", name="testuser1"),
            expected_output=(
                status.HTTP_400_BAD_REQUEST,
                {"detail": "User already exists"},
            ),
        ),
    }

    TARGET_MAP_DATA: MapPair = MapPair(
        input_data=sch.Map(
            user_id="01",
            name="Test Map",
            description="A test map for unit testing purposes.",
            map_size=100.0,
            samples=50,
            num_small_targets=5,
            num_medium_targets=3,
            num_large_targets=2,
            num_heat_points=8,
        ),
        expected_output=(
            status.HTTP_201_CREATED,
            {
                "id": ...,
                "user_id": "01",
                "name": "Test Map",
                "description": "A test map for unit testing purposes.",
                "map_size": 100.0,
                "samples": 50,
                "num_small_targets": 5,
                "num_medium_targets": 3,
                "num_large_targets": 2,
                "num_heat_points": 8,
            },
        ),
    )

    TARGET_DATA: tuple[sch.Target, sch.Target, sch.Target] = get_target_classes("01")

    @classmethod
    def get_target_model(cls, target_size: sch.TargetClass) -> TargetPair:
        """
        Get a TargetPair instance containing the target data for testing.

        Returns:
            TargetPair: A TargetPair instance containing the target data for testing.
        """
        target_class_translator = {
            sch.TargetClass.SMALL: 0,
            sch.TargetClass.MEDIUM: 1,
            sch.TargetClass.LARGE: 2,
        }
        target_class_idx = target_class_translator[target_size]
        return TargetPair(
            input_data=cls.TARGET_DATA[target_class_idx],
            expected_output=(
                status.HTTP_201_CREATED,
                {
                    "id": ...,
                    "user_id": "01",
                    "name": ...,
                    "description": ...,
                    "category": target_size,
                    "top_speed": ...,
                    "accel_max": ...,
                    "decel_max": ...,
                    "hitbox_size": ...,
                    "loot_dist": ...,
                    "loot_min": ...,
                    "loot_max": ...,
                    "loot_stddev": ...,
                },
            ),
        )


def compare_to_expected_output(
    response_json: dict[str, Any], expected_output: dict[str, Any]
) -> bool:
    """
    Compare the response JSON to the expected output.

    Args:
        response_json (dict[str, Any]): The JSON response from the API.
        expected_output (dict[str, Any]): The expected output for the test case.
    Returns:
        bool: True if the response matches the expected output, False otherwise.
    """
    for k, v in expected_output.items():
        if v is ...:
            if k not in response_json:
                return False
        elif response_json.get(k) != v:
            return False
    return True


@pytest.fixture(scope="function")
def database_setup(client: TestClient, request: pytest.FixtureRequest) -> DataModel:
    """
    Fixture for returning a database state based on the data fixture.
    """
    data: DataModel = request.param
    users_in, target_map_in, targets_in = data.users, data.target_map, data.targets

    def add_users(users_arg: list[UserPair]):
        for user in users_arg:
            response = client.post(
                "/users",
                json={
                    "id": user.input_data.id,
                    "name": user.input_data.name,
                    "class_name": user.input_data.class_name,
                },
            )
            assert response.status_code == user.expected_output[0]
            assert compare_to_expected_output(response.json(), user.expected_output[1])

    def add_map(map_arg: MapPair):
        response = client.post(
            "/maps/",
            json=json.loads(map_arg.input_data.model_dump_json()),
        )
        assert response.status_code == map_arg.expected_output[0]
        assert compare_to_expected_output(response.json(), map_arg.expected_output[1])

    def add_targets(targets_arg: list[TargetPair], map_id: str):
        for target in targets_arg:
            response = client.post(
                f"/targets/{map_id}",
                json=json.loads(target.input_data.model_dump_json()),
            )
            assert response.status_code == target.expected_output[0]
            assert compare_to_expected_output(
                response.json(), target.expected_output[1]
            )

    add_users(users_in)
    if target_map_in:
        add_map(target_map_in)
        add_targets(targets_in, target_map_in.input_data.id)
    return data


class TestEndpoints:
    """
    A class to test the API endpoints of the FastAPI application.

    This class contains tests for the following endpoints:
    - GET /
    - POST /users
    - GET /users/{user_id}
    - POST /maps
    - POST /targets
    - POST /pdf-parameters
    """

    def test_read_root(self: Self, client: TestClient):
        """
        Test the root endpoint to verify that the backend API is online.

        Args:
            client (TestClient): The test client for making API requests.
        """
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "message": "Welcome to the Project Netfall Backend API!"
        }

    @pytest.mark.parametrize(
        "database_setup",
        [
            (
                DataModel(
                    users=[
                        DataForTests.USER_DATA["valid_user_1"],
                    ],
                    target_map=None,
                    targets=[],
                )
            ),
            (
                DataModel(
                    users=[
                        DataForTests.USER_DATA["valid_user_1"],
                        DataForTests.USER_DATA["valid_user_2"],
                    ],
                    target_map=None,
                    targets=[],
                )
            ),
            (
                DataModel(
                    users=[
                        DataForTests.USER_DATA["valid_user_1"],
                        DataForTests.USER_DATA["duplicate_user"],
                    ],
                    target_map=None,
                    targets=[],
                )
            ),
        ],
        indirect=["database_setup"],
    )
    def test_create_user(
        self: Self,
        database_setup: DataModel,
    ):
        """
        Test the user creation endpoint.

        Args:
            database_setup (DataModel): The data model
                for setting up the test database.
                All of the assertions for the test
                case are handled in the fixture,
                so this test function simply verifies
                that the fixture runs without error.
        """
        assert database_setup

    @pytest.mark.parametrize(
        "database_setup,user_name,expected_status_code",
        [
            (
                DataModel(
                    users=[
                        DataForTests.USER_DATA["valid_user_1"],
                        DataForTests.USER_DATA["valid_user_2"],
                    ],
                    target_map=None,
                    targets=[],
                ),
                "testuser1",
                status.HTTP_200_OK,
            ),
            (
                DataModel(
                    users=[
                        DataForTests.USER_DATA["valid_user_1"],
                        DataForTests.USER_DATA["valid_user_2"],
                    ],
                    target_map=None,
                    targets=[],
                ),
                "testuser2",
                status.HTTP_200_OK,
            ),
            (
                DataModel(
                    users=[
                        DataForTests.USER_DATA["valid_user_1"],
                        DataForTests.USER_DATA["valid_user_2"],
                    ],
                    target_map=None,
                    targets=[],
                ),
                "testuser3",
                status.HTTP_404_NOT_FOUND,
            ),
        ],
        indirect=["database_setup"],
    )
    def test_get_user(
        self: Self,
        database_setup: DataModel,
        user_name: str,
        expected_status_code: int,
        client: TestClient,
    ):
        """
        Test the user retrieval endpoint.

        Args:
            database_setup (DataModel):
                The data model for setting up the test database.
            user_name (str): The name of the user to retrieve.
            expected_status_code (int):
                The expected HTTP status code for the response.
            client (TestClient): The test client for making API requests.
        """
        assert database_setup
        response = client.get(f"/users/{user_name}")
        assert response.status_code == expected_status_code
        selected_user = [
            user for user in database_setup.users if user.input_data.name == user_name
        ]
        assert (
            compare_to_expected_output(
                response.json(), selected_user[0].expected_output[1]
            )
            if expected_status_code == status.HTTP_200_OK
            else compare_to_expected_output(
                response.json(), {"detail": "User not found"}
            )
        )

    @pytest.mark.parametrize(
        "database_setup",
        [
            (
                DataModel(
                    users=[
                        DataForTests.USER_DATA["valid_user_1"],
                    ],
                    target_map=DataForTests.TARGET_MAP_DATA,
                    targets=[],
                )
            ),
        ],
        indirect=["database_setup"],
    )
    def test_create_map(
        self: Self,
        database_setup: DataModel,
    ):
        """
        Test the map creation endpoint.

        Args:
            database_setup (DataModel): The data model
                for setting up the test database.
                All of the assertions for the test
                case are handled in the fixture,
                so this test function simply verifies
                that the fixture runs without error.
        """
        assert database_setup

    @pytest.mark.parametrize(
        "database_setup",
        [
            (
                DataModel(
                    users=[
                        DataForTests.USER_DATA["valid_user_1"],
                    ],
                    target_map=DataForTests.TARGET_MAP_DATA,
                    targets=[
                        DataForTests.get_target_model(sch.TargetClass.SMALL),
                        DataForTests.get_target_model(sch.TargetClass.MEDIUM),
                        DataForTests.get_target_model(sch.TargetClass.LARGE),
                    ],
                )
            ),
        ],
        indirect=["database_setup"],
    )
    def test_create_targets(
        self: Self,
        database_setup: DataModel,
    ):
        """
        Test the target creation endpoint.

        Args:
            database_setup (DataModel): The data model
                for setting up the test database.
                All of the assertions for the test
                case are handled in the fixture,
                so this test function simply verifies
                that the fixture runs without error.
        """
        assert database_setup
