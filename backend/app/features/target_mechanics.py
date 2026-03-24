"""
This module contains the target mechanics for the RPG game.
It defines the logic for calculating target behavior,
loot distribution, and other related mechanics.

"""

# import os
from datetime import datetime, timedelta
from typing import Callable, Generator

import numpy as np
import numpy.random as npr
import polars as pl

from app.schemas.sqlmodels import LootDist, Map, Target, TargetClass

npr.seed(42)  # Set a fixed seed for reproducibility


def get_target_classes(user_id: str) -> tuple[Target, Target, Target]:
    """
    Get the target configuration based on the target class.

    Args:
        user_id (str): The ID of the user for whom to generate the target.
    Returns:
        tuple[Target, Target, Target]: A tuple containing the target
        configurations for small, medium, and large targets.
    """
    return (
        Target(
            user_id=user_id,
            name="Small Target",
            description="A small target with high agility.",
            category=TargetClass.SMALL,
            top_speed=10.0,
            accel_max=5.0,
            decel_max=-5.0,
            hitbox_size=0.5,
            loot_dist=LootDist.GAUSSIAN,
            loot_min=3,
            loot_max=8,
            loot_mean=5,
            loot_stddev=1,
        ),
        Target(
            user_id=user_id,
            name="Medium Target",
            description="A medium target with balanced stats.",
            category=TargetClass.MEDIUM,
            top_speed=8.0,
            accel_max=4.0,
            decel_max=-4.0,
            hitbox_size=1.0,
            loot_dist=LootDist.GAUSSIAN,
            loot_min=5,
            loot_max=12,
            loot_mean=8,
            loot_stddev=2,
        ),
        Target(
            user_id=user_id,
            name="Large Target",
            description="A large target with low agility.",
            category=TargetClass.LARGE,
            top_speed=6.0,
            accel_max=3.0,
            decel_max=-3.0,
            hitbox_size=1.5,
            loot_dist=LootDist.GAUSSIAN,
            loot_min=8,
            loot_max=15,
            loot_mean=11,
            loot_stddev=2,
        ),
    )


def generate_map_heat_points(target_map: Map, margin: float = 5.00) -> pl.LazyFrame:
    """
    Generate random heat points for the map.

    Args:
        num_points (int): The number
            of heat points to generate.
        map_width (float): The width of the map
            for position constraints.
        margin (float): The margin to avoid placing heat
            points too close to the edges of the map.
    Returns:
        pl.LazyFrame: A LazyFrame containing the
            generated heat points with
            their positions and visit durations.
    """
    return pl.LazyFrame(
        {
            "x": pl.Series(
                "x",
                npr.uniform(
                    margin,
                    target_map.map_size - margin,
                    target_map.num_heat_points,
                ),
            ),
            "y": pl.Series(
                "y",
                npr.uniform(
                    margin,
                    target_map.map_size - margin,
                    target_map.num_heat_points,
                ),
            ),  # Random y positions within the map width
        }
    )


def describe_lanes(
    target_map: Map,
    heat_points: pl.LazyFrame,
    target_specs: Target,
    stddev_factor: float = 0.2,
) -> pl.LazyFrame:
    """
    Describe the lanes on the map based on the heat points.

    Args:
        target_map (Map): The map on which the lanes are located.
        heat_points (pl.LazyFrame): The heat points on the map.
        target_specs (Target): The specifications for the targets
            for which to describe lanes.
        stddev_factor (float): A factor to scale the standard
            deviation of traffic variability. Default is 0.2,
            which means the variability will be 20% of the
            maximum possible variability based on the target's
            speed and acceleration.

    Returns:
        pl.LazyFrame: A LazyFrame containing the description of the lanes.
    """

    match target_specs.category:
        case TargetClass.SMALL:
            total_targets = target_map.num_small_targets
        case TargetClass.MEDIUM:
            total_targets = target_map.num_medium_targets
        case TargetClass.LARGE:
            total_targets = target_map.num_large_targets
        case _:
            raise ValueError("Invalid target category")
    max_stddev = (
        stddev_factor * (target_specs.top_speed * target_specs.accel_max) ** 0.5
    )
    return heat_points.with_columns(
        x_start=pl.col("x"),
        y_start=pl.col("y"),
        x_end=pl.col("x").shift(-1).fill_null(pl.col("x").first()),
        y_end=pl.col("y").shift(-1).fill_null(pl.col("y").first()),
        traffic_density=pl.lit(npr.uniform(0, 1, target_map.num_heat_points))
        * (total_targets / target_map.num_heat_points),  # Random traffic density
        traffic_stddev=pl.lit(
            npr.uniform(0.1 * max_stddev, max_stddev, target_map.num_heat_points)
        ),  # Random traffic variability
    )


def map_lane_traffic(
    target_map: Map, lanes: pl.LazyFrame
) -> Generator[tuple[pl.LazyFrame, pl.LazyFrame], None, None]:
    """
    Map the traffic on the lanes based on the traffic density and variability.

    Args:
        target_map (Map): The map on which the lanes are located.
        lanes (pl.LazyFrame): The LazyFrame containing the description of the lanes.

    Returns:
        Generator: A generator that yields LazyFrames
            containing the traffic mapped on the lanes and the grid points.
    """
    x_values = pl.Series(
        "x_values",
        np.linspace(0, target_map.map_size, target_map.samples),
    )
    y_values = pl.Series(
        "y_values",
        np.linspace(0, target_map.map_size, target_map.samples),
    )

    q1 = (
        pl.DataFrame({"x": x_values})
        .select(pl.col("x").alias("x"))
        .join(pl.DataFrame({"y": y_values}), how="cross")
        .select(pl.col("x"), pl.col("y").alias("y"))
        .lazy()
    )
    for lane in lanes.collect().iter_rows(named=True):
        q2 = (
            q1.with_columns(
                (
                    abs(
                        pl.col("x") * (lane["y_end"] - lane["y_start"])
                        - pl.col("y") * (lane["x_end"] - lane["x_start"])
                        + lane["y_start"] * lane["x_end"]
                        - lane["y_end"] * lane["x_start"],
                    )
                    / (
                        (lane["x_end"] - lane["x_start"]) ** 2
                        + (lane["y_end"] - lane["y_start"]) ** 2
                    )
                    ** 0.5
                ).alias("dist_to_lane")
            )
            .select(pl.col("x"), pl.col("y"), pl.col("dist_to_lane"))
            .lazy()
        )
        q3 = (
            q2.with_columns(
                (
                    lane["traffic_density"]
                    * np.exp(
                        -0.5
                        * (pl.col("dist_to_lane") ** 2 / lane["traffic_stddev"] ** 2)
                    )
                ).alias("traffic")
            )
            .select(pl.col("x"), pl.col("y"), pl.col("traffic"))
            .lazy()
        )
        yield q3, q1


def calculate_temporal_lane_traffic(
    lanes: pl.LazyFrame,
    start_time: datetime,
    duration: timedelta,
    time_steps: int,
) -> Generator[pl.LazyFrame, None, None]:
    """
    Calculate the temporal lane traffic based on the traffic density and variability.

    Args:
        lanes (pl.LazyFrame): The LazyFrame containing the
            description of the lanes.
        start_time (datetime): The start time for the
            temporal traffic evaluation.
        duration (timedelta): The duration over which
            to evaluate the temporal traffic.
        time_steps (int): The number of time steps over a day to simulate.

    Returns:
        Generator: A generator that yields LazyFrames
            containing the temporal traffic patterns for each lane.
    """
    time_series = pl.Series(
        "time",
        pl.linear_space(start_time, start_time + duration, time_steps, eager=True),
    )
    num_rush_hours = npr.randint(1, 4, size=lanes.collect().shape[0])
    for i, lane in enumerate(lanes.collect().iter_rows(named=True)):
        rush_hours = pl.Series(
            time_series.sample(num_rush_hours[i], with_replacement=False),
        )
        traffic_patterns = [
            pl.DataFrame(
                {
                    "time": time_series,
                    "traffic": (
                        lane["traffic_density"]
                        + lane["traffic_density"]
                        * (npr.rand() + 1)
                        * 5
                        * np.exp(
                            -0.5
                            * (
                                rush_hour
                                - time_series.map_elements(
                                    lambda x: (x - start_time).total_seconds()
                                )
                            )
                            ** 2
                            / (60 * 60) ** 2
                        )
                    ),
                }
            ).lazy()
            for rush_hour in rush_hours
        ]
        yield (
            pl.concat(traffic_patterns)
            .group_by("time")
            .agg(pl.sum("traffic").alias("total_traffic"))
        )


def evaluate_total_pdf(
    target_map: Map,
    lanes: pl.LazyFrame,
    start_time: datetime,
    duration: timedelta,
    time_steps: int,
) -> Callable[[datetime], pl.LazyFrame]:
    """
    Evaluate the total PDF state of the map by combining lane and temporal traffic.

    Args:
        target_map (Map): The map on which the lanes are located.
        lanes (pl.LazyFrame): The LazyFrame containing the
            description of the lanes.
        start_time (datetime): The start time for the
            temporal traffic evaluation.
        duration (timedelta): The duration over which
            to evaluate the temporal traffic.
        time_steps (int): The number of time steps to evaluate.

    Returns:
        Callable:
            A function that takes a datetime and returns a generator of LazyFrames
            containing the total PDF state of the map at that time.
    """

    def total_pdf_at_time_per_lane(
        current_time: datetime,
    ) -> Generator[pl.LazyFrame, None, None]:
        """
        Evaluate the total PDF state of the map at a specific time.

        Args:
            current_time (datetime): The time at which to evaluate the PDF.

        Returns:
            Generator: A generator of LazyFrames containing the total PDF
                state of the map at the specified time.
        """
        for (lane_traffic, _), temporal_traffic in zip(
            map_lane_traffic(target_map, lanes),
            calculate_temporal_lane_traffic(lanes, start_time, duration, time_steps),
        ):
            current_traffic = (
                temporal_traffic.select(
                    pl.col("total_traffic").alias("current_traffic"),
                    pl.when(pl.col("time") > current_time)
                    .then(pl.col("total_traffic"))
                    .otherwise(pl.lit(None)),
                )
                .select(pl.col("current_traffic").first(ignore_nulls=True))
                .collect()
            ).item(0, 0)
            if current_traffic is None:
                current_traffic = 0.0
            yield (
                lane_traffic.select(
                    pl.col("x"),
                    pl.col("y"),
                    pl.col("traffic").alias("lane_traffic"),
                )
                .with_columns(pdf=(pl.col("lane_traffic") * current_traffic))
                .select(pl.col("x"), pl.col("y"), pl.col("pdf").fill_null(0))
                .lazy()
            )

    def total_pdf_at_time(current_time: datetime) -> pl.LazyFrame:
        """
        Evaluate the total PDF state of the map at a specific time.

        Args:
            current_time (datetime): The time at which to evaluate the PDF.

        Returns:
            Generator: A generator of LazyFrames containing the total PDF
                state of the map at the specified time.
        """
        return (
            pl.concat(list(total_pdf_at_time_per_lane(current_time)))
            .group_by(["x", "y"])
            .agg(pl.sum("pdf").alias("total_pdf"))
        )

    return total_pdf_at_time


def calculate_loot(target: Target) -> float:
    """
    Calculates the dropped loot value based on the target's statistical parameters.

    Args:
        target (Target): The target for which to calculate the loot.

    Returns:
        float: The calculated loot value, constrained
            within the target's loot_min and loot_max.
    """
    loot = 0.0
    if target.loot_dist == LootDist.UNIFORM:
        loot = npr.uniform(target.loot_min, target.loot_max)
    elif target.loot_dist in (LootDist.NORMAL, LootDist.GAUSSIAN):
        mean = (
            target.loot_mean
            if target.loot_mean is not None
            else (target.loot_min + target.loot_max) / 2
        )
        stddev = target.loot_stddev if target.loot_stddev is not None else 1.0
        loot = npr.normal(mean, stddev)

    # Ensure loot stays within physical constraints (bounds)
    return float(np.clip(loot, target.loot_min, target.loot_max))
