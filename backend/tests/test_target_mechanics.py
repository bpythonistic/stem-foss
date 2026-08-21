"""
Tests for target mechanics.

functions tested:
- evaluate_total_pdf
- calculate_temporal_hot_spot_density
"""

from datetime import datetime, timedelta

import app.schemas.sqlmodels as sql_schemas
import numpy as np
import polars as pl
import pytest
from app.features import target_mechanics as tm
from pydantic import BaseModel, Field
from sqlmodel import Session, select


class TargetSpecsData(BaseModel):
    """
    A class to represent the target specifications data for testing.

    Attributes:
        specs (list[sql_schemas.Target]):
            A list of target specifications to be used in the tests.
    """

    specs: list[sql_schemas.Target] = Field(
        default_factory=lambda: list(tm.get_target_classes("01", "map_01"))
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
        num_hot_spots (int): The number of hot spots to generate on the map
    """

    map_size: float = 100.0
    samples: int = 200
    num_hot_spots: int = 10


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
                id="map_01",
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
                num_hot_spots=map_in.num_hot_spots,
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
                    num_hot_spots=10,
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
                    num_hot_spots=10,
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
            timedelta(hours=15),
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
    hot_spots = tm.generate_hot_spots(target_map)
    target_hot_spots = [
        tm.describe_hot_spots(target_map, hot_spots, target) for target in targets
    ]
    start_time = datetime.now() - timedelta(hours=24)

    total_pdf_funcs = [
        tm.evaluate_total_pdf(target_map, spots, start_time, time_window, time_steps)
        for spots in target_hot_spots
    ]

    for total_pdf_func in total_pdf_funcs:
        pdf = total_pdf_func(start_time + rel_start_time)
        assert pdf.collect().shape[0] == expected_pdf_dims[0] * expected_pdf_dims[1]


# --- Gather-dwell-disperse temporal dynamics (STEM-27) ---------------------

_DWELL_START = datetime(2026, 1, 1, 0, 0, 0)
_DWELL_DURATION = timedelta(hours=12)
_DWELL_BASE = 4.0
# Resting crowd level between dwell events (see target_mechanics._DWELL_BASELINE).
_DWELL_FLOOR = _DWELL_BASE * tm._DWELL_BASELINE


def _hot_spot_frame(center_x: float = 50.0, base: float = _DWELL_BASE) -> pl.LazyFrame:
    """Builds a one-row hot spot frame for temporal-density tests."""
    return pl.LazyFrame(
        {
            "center_x": [center_x],
            "center_y": [50.0],
            "hot_spot_density": [base],
            "hot_spot_spread": [2.0],
        }
    )


def _temporal_curve(
    hot_spots: pl.LazyFrame,
    category: sql_schemas.TargetClass,
    time_steps: int = 240,
) -> np.ndarray:
    """Collects the crowd-density curve for the first hot spot."""
    frame = next(
        tm.calculate_temporal_hot_spot_density(
            hot_spots, _DWELL_START, _DWELL_DURATION, time_steps, category
        )
    ).collect()
    return np.array(frame["total_density"].to_list(), dtype=np.float64)


def _single_event_hot_spot(base: float = _DWELL_BASE) -> pl.LazyFrame:
    """
    Finds a hot spot whose seeded schedule yields exactly one dwell event.

    Isolating a single event makes the per-class amplitude comparison exact:
    the two curves then differ only by their dwell profile.
    """
    for center_x in range(1, 300):
        candidate = {
            "center_x": float(center_x),
            "center_y": 50.0,
            "hot_spot_density": base,
        }
        rng = np.random.default_rng(tm._hot_spot_seed(candidate))
        if int(rng.integers(1, 4)) == 1:
            return _hot_spot_frame(center_x=float(center_x), base=base)
    raise AssertionError("No single-event hot spot found in search range.")


def _longest_elevated_run(mask: np.ndarray) -> int:
    """Returns the longest contiguous run of True values in a boolean mask."""
    longest = current = 0
    for flag in mask:
        current = current + 1 if flag else 0
        longest = max(longest, current)
    return longest


def test_temporal_dwell_is_deterministic_across_calls():
    """
    The same hot spot yields an identical curve on every evaluation.

    This is what lets the gather-dwell-disperse progression stay coherent as
    the time slider is scrubbed; the previous global-RNG approach drifted
    between calls.
    """
    hot_spots = _hot_spot_frame()
    first = _temporal_curve(hot_spots, sql_schemas.TargetClass.MEDIUM)
    second = _temporal_curve(hot_spots, sql_schemas.TargetClass.MEDIUM)
    assert np.array_equal(first, second)


def test_temporal_dwell_forms_a_window_not_a_spike():
    """Crowd density rises into a contiguous plateau above the resting floor."""
    time_steps = 240
    curve = _temporal_curve(
        _hot_spot_frame(), sql_schemas.TargetClass.MEDIUM, time_steps
    )

    assert curve.shape[0] == time_steps
    # Between dwells the hot spot rests at the baseline; surges only add crowd,
    # so density never falls below that floor.
    assert np.all(curve >= _DWELL_FLOOR - 1e-9)

    peak = curve.max()
    assert peak > _DWELL_FLOOR  # a dwell surge occurred

    # The elevated region spans many contiguous steps: a window, not a spike.
    half_height = _DWELL_FLOOR + 0.5 * (peak - _DWELL_FLOOR)
    assert _longest_elevated_run(curve >= half_height) >= 5


def test_temporal_dwell_fades_between_events():
    """
    A hot spot returns close to its resting floor away from its dwell window.

    The floor stays well below the peak so that, after the saturating
    P(at least one target) transform, blobs visibly appear and vanish as the
    time slider moves rather than staying permanently lit.
    """
    curve = _temporal_curve(_single_event_hot_spot(), sql_schemas.TargetClass.MEDIUM)
    assert np.isclose(curve.min(), _DWELL_FLOOR, rtol=1e-6)
    # The resting floor is a small fraction of the dwell peak.
    assert curve.min() < 0.25 * curve.max()


def test_dwell_profile_scales_with_target_class():
    """
    Lighter classes spike higher; heavier classes dwell over a wider window.
    """
    hot_spots = _single_event_hot_spot()
    small = _temporal_curve(hot_spots, sql_schemas.TargetClass.SMALL)
    large = _temporal_curve(hot_spots, sql_schemas.TargetClass.LARGE)

    small_peak = small.max() - _DWELL_FLOOR
    large_peak = large.max() - _DWELL_FLOOR
    # SMALL amplitude (6.0) is twice LARGE (3.0); the peak surge ratio tracks
    # that ~2x (only lightly perturbed by the classes' differing tails).
    assert small_peak > large_peak
    assert np.isclose(small_peak, 2.0 * large_peak, rtol=5e-2)

    # ...but the heavier class dwells over a wider window (its own half-height).
    small_width = int(np.sum(small >= _DWELL_FLOOR + 0.5 * small_peak))
    large_width = int(np.sum(large >= _DWELL_FLOOR + 0.5 * large_peak))
    assert large_width > small_width


def test_pdf_advances_as_evaluation_time_moves():
    """
    A fixed simulation window yields different PDFs at different moments.

    Regression guard for the frozen heatmap: evaluating every frame at the
    window start made the time slider inert. The window must stay anchored at
    ``start_time`` while the evaluation time moves through it.
    """
    target_map = sql_schemas.Map(
        id="map_freeze",
        user_id="01",
        name="Freeze Map",
        description="Regression map for time-advance.",
        map_size=100.0,
        samples=40,
        num_small_targets=0,
        num_medium_targets=15,
        num_large_targets=0,
        num_hot_spots=6,
    )
    hot_spots = pl.LazyFrame(
        {
            "center_x": [20.0, 40.0, 60.0, 80.0, 30.0, 70.0],
            "center_y": [20.0, 40.0, 60.0, 80.0, 70.0, 30.0],
            "hot_spot_density": [1.0, 0.8, 1.2, 0.6, 0.9, 1.1],
            "hot_spot_spread": [5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
        }
    )
    pdf_fn = tm.evaluate_total_pdf(
        target_map,
        hot_spots,
        _DWELL_START,
        _DWELL_DURATION,
        20,
        sql_schemas.TargetClass.MEDIUM,
    )

    def frame_at(current_time):
        return pdf_fn(current_time).collect().sort(["y", "x"])["total_pdf"].to_numpy()

    early = frame_at(_DWELL_START)
    late = frame_at(_DWELL_START + _DWELL_DURATION * 0.6)

    assert early.shape == late.shape
    assert not np.allclose(early, late)
