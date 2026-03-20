"""
Tests for target mechanics.


"""

from datetime import datetime, timedelta

import pytest
from pydantic import BaseModel, Field
import polars as pl
from sqlmodel import Session

from app.features import target_mechanics as tm
import app.schemas.sqlmodels as sql_schemas


class TargetSpecsData(BaseModel):
    """
    A class to represent the target specifications data for testing.
    """

    specs: list[sql_schemas.Target] = Field(
        default_factory=lambda: list(tm.get_target_classes("01"))
    )


class Targets(TargetSpecsData):
    """
    A class to represent the targets data for testing,
        including the target specifications and the number of targets for each class.
        Inherits from TargetSpecsData to include the target specifications.

    Attributes:
        categories: A list of target classes
        number_of_targets: A dictionary mapping each target
            class to the number of targets of that class
    """

    categories: list[sql_schemas.TargetClass] = [
        sql_schemas.TargetClass.SMALL,
        sql_schemas.TargetClass.MEDIUM,
        sql_schemas.TargetClass.LARGE,
    ]
    number_of_targets: dict[sql_schemas.TargetClass, int] = Field(default_factory=dict)


class MapData(BaseModel):
    """
    A class to represent the map data for testing.

    Attributes:
        map_size: The size of the map (units)
        resolution: The resolution of the map (pixels per unit)
        num_heat_points: The number of heat points to generate on the map
    """

    map_size: float = 100.0
    samples: int = 200
    num_heat_points: int = 10


class TestData(BaseModel):
    """
    A class to represent the test data for target mechanics tests.

    Attributes:
        target_map: MapData
        target_data: Targets
    """

    target_map: MapData
    target_data: Targets


@pytest.fixture
def database_setup(session: Session, request: pytest.FixtureRequest):
    """
    Fixture for providing test data for target mechanics tests.

    :param config: The configuration fixture that loads test data from a YAML file.
    :return: A tuple containing the created map and targets for testing.
    :rtype: tuple[sql_schemas.Map, list[sql_schemas.Target]]
    """
    data: TestData = request.param
    map_in, targets_in = data.target_map, data.target_data

    def create_map_and_targets() -> tuple[sql_schemas.Map, list[sql_schemas.Target]]:
        """
        Create the map and targets in the database for testing.

        :return: A tuple containing the created map and targets.
        :rtype: tuple[sql_schemas.Map, list[sql_schemas.Target]]
        """

        with session:
            for target in targets_in.specs:
                session.add(target)
                session.commit()
                session.refresh(target)
            target_map = sql_schemas.Map(
                user_id="01",
                name="Test Map",
                description="A test map for target mechanics tests.",
                map_size=map_in.map_size,
                samples=map_in.samples,
                num_small_targets=targets_in.number_of_targets.get(
                    sql_schemas.TargetClass.SMALL, 0
                ),
                num_medium_targets=targets_in.number_of_targets.get(
                    sql_schemas.TargetClass.MEDIUM, 0
                ),
                num_large_targets=targets_in.number_of_targets.get(
                    sql_schemas.TargetClass.LARGE, 0
                ),
                num_heat_points=map_in.num_heat_points,
            )
            session.add(target_map)
            session.commit()
            session.refresh(target_map)
        return target_map, targets_in.specs

    return create_map_and_targets()


@pytest.fixture(scope="session")
def setup_target_mechanics_tests(database_setup) -> list[pl.DataFrame]:
    """
    Fixture for setting up the target mechanics tests.

    :param database_setup: The fixture that sets up the database with test data.
    :return: A list of DataFrames containing the lane descriptions for each target.
    :rtype: list[pl.DataFrame]
    """
    target_map, targets = database_setup
    heat_points = tm.generate_map_heat_points(target_map)
    lanes = [tm.describe_lanes(target_map, heat_points, target) for target in targets]
    return lanes


@pytest.mark.parametrize(
    "target_map,target_data,expected_pdf_dims,time_window,rel_start_time,time_steps",
    [
        (
            MapData(
                map_size=100.0,
                samples=200,
                num_heat_points=10,
            ),
            Targets(
                number_of_targets={
                    sql_schemas.TargetClass.SMALL: 20,
                    sql_schemas.TargetClass.MEDIUM: 15,
                    sql_schemas.TargetClass.LARGE: 10,
                }
            ),
            (200, 200),
            timedelta(hours=12),
            timedelta(hours=5),
            20,
        )
    ],
    indirect=["target_map", "target_data"],
)
def test_evaluate_total_pdf(
    database_setup, expected_pdf_dims, time_window, rel_start_time, time_steps
):
    """
    Test the evaluate_total_pdf function.

    :param database_setup: The fixture that sets up the database with test data.
    :param expected_pdf_dims: The expected dimensions of the PDF for the test data.
    :type expected_pdf_dims: tuple[int, int]
    :param time_window: The time window for the PDF evaluation.
    :type time_window: timedelta
    :param rel_start_time: The relative start time for the PDF evaluation.
    :type rel_start_time: timedelta
    :param time_steps: The number of time steps for the PDF evaluation.
    :type time_steps: int
    :return: None
    """
    target_map, targets = database_setup
    heat_points = tm.generate_map_heat_points(target_map)
    target_lanes = [
        tm.describe_lanes(target_map, heat_points, target) for target in targets
    ]
    start_time = datetime.now() - timedelta(hours=24)

    total_pdf_funcs = [
        tm.evaluate_total_pdf(target_map, lanes, start_time, time_window, time_steps)
        for lanes in target_lanes
    ]

    for total_pdf_func in total_pdf_funcs:
        pdf = total_pdf_func(start_time + rel_start_time)
        assert pdf.collect().shape == expected_pdf_dims
