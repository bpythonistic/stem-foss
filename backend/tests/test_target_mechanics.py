"""
Tests for target mechanics.


"""

from datetime import datetime, timedelta

import pytest
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.features import target_mechanics as tm
import app.schemas.sqlmodels as sql_schemas


class TargetSpecsData(BaseModel):
    """
    A class to represent the target specifications data for testing.

    Attributes:
        specs (list[sql_schemas.Target]):
            A list of target specifications to be used in the tests.
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
        categories (list[sql_schemas.TargetClass]): A list of target classes
        number_of_targets (dict[sql_schemas.TargetClass, int]):
            A dictionary mapping each target class to the
            number of targets of that class
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
        map_size (float): The size of the map (units)
        resolution (float): The resolution of the map (pixels per unit)
        num_heat_points (int): The number of heat points to generate on the map
    """

    map_size: float = 100.0
    samples: int = 200
    num_heat_points: int = 10


class DataModel(BaseModel):
    """
    A class to represent the test data for target mechanics tests.

    Attributes:
        target_map (MapData): The map data for the tests.
        target_data (Targets): The target data for the tests.
    """

    target_map: MapData
    target_data: Targets


@pytest.fixture(name="database_setup", scope="function")
def database_setup_fixture(
    session: Session, request: pytest.FixtureRequest
) -> tuple[sql_schemas.Map, list[sql_schemas.Target]]:
    """
    Fixture for providing test data for target mechanics tests.
    """

    data: DataModel = request.param
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


@pytest.mark.parametrize(
    "database_setup,expected_pdf_dims,time_window,rel_start_time,time_steps",
    [
        (
            DataModel(
                target_map=MapData(
                    map_size=100.0,
                    samples=200,
                    num_heat_points=10,
                ),
                target_data=Targets(
                    number_of_targets={
                        sql_schemas.TargetClass.SMALL: 20,
                        sql_schemas.TargetClass.MEDIUM: 15,
                        sql_schemas.TargetClass.LARGE: 10,
                    }
                ),
            ),
            (200, 200),
            timedelta(hours=12),
            timedelta(hours=5),
            20,
        ),
        (
            DataModel(
                target_map=MapData(
                    map_size=100.0,
                    samples=200,
                    num_heat_points=10,
                ),
                target_data=Targets(
                    number_of_targets={
                        sql_schemas.TargetClass.SMALL: 20,
                        sql_schemas.TargetClass.MEDIUM: 15,
                        sql_schemas.TargetClass.LARGE: 10,
                    }
                ),
            ),
            (200, 200),
            timedelta(hours=12),
            timedelta(hours=5),
            20,
        ),
    ],
    indirect=["database_setup"],
)
def test_evaluate_total_pdf(
    database_setup: tuple[sql_schemas.Map, list[sql_schemas.Target]],
    session: Session,
    expected_pdf_dims: tuple[int, int],
    time_window: timedelta,
    rel_start_time: timedelta,
    time_steps: int,
):
    """
    Test the evaluate_total_pdf function.

    Args:
        database_setup (tuple[sql_schemas.Map, list[sql_schemas.Target]]):
            The fixture that sets up the database with the map and targets.
        expected_pdf_dims (tuple[int, int]):
            The expected dimensions of the resulting PDF DataFrame.
        time_window (timedelta): The time window for evaluating the PDF.
        rel_start_time (timedelta):
            The relative start time for evaluating the PDF.
        time_steps (int): The number of time steps to evaluate the PDF over.
    """

    target_map = session.exec(select(sql_schemas.Map)).first()
    if target_map is None:
        raise ValueError("No map found in the database.")
    targets = session.exec(select(sql_schemas.Target)).all()
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
        assert pdf.collect().shape[0] == expected_pdf_dims[0] * expected_pdf_dims[1]
