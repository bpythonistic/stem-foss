"""
Defines the mathematical engine for target physics and loot.

- get_target_classes: Retrieves base configurations for tiers.
- generate_map_heat_points: Creates randomized map nodes.
- describe_lanes: Generates traffic routes connecting nodes.
- map_lane_traffic: Maps spatial Gaussian spread for routes.
- calculate_temporal_lane_traffic: Simulates traffic volume.
- evaluate_total_pdf: Evaluates combined spatiotemporal PDF.
- calculate_loot: Calculates reward payouts based on stats.
"""

from datetime import datetime, timedelta
from typing import Callable, Generator

import numpy as np
import numpy.random as npr
import polars as pl

from app.schemas.sqlmodels import LootDist, Map, Target, TargetClass

npr.seed(42)  # Set a fixed seed for reproducibility


def get_target_classes(user_id: str) -> tuple[Target, Target, Target]:
    """
    Retrieves the base hardware specifications for target tiers.

    Args:
        user_id (str): The unique identifier
            of the active player.
    Returns:
        tuple: The small, medium, and large
            target configurations.
    """
    return (
        Target(
            user_id=user_id,
            map_id=None,  # To be assigned when linked to a map
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
            map_id=None,  # To be assigned when linked to a map
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
            map_id=None,  # To be assigned when linked to a map
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
    Creates randomized anchor nodes for generating map traffic.

    Args:
        target_map (Map): The map config
            used to define boundaries.
        margin (float): The edge padding
            to prevent clipping nodes.
    Returns:
        pl.LazyFrame: Generated heat nodes
            with coordinate locations.
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
    Builds randomized parametric routes connecting map nodes.

    Args:
        target_map (Map): The operational
            zone configuration.
        heat_points (pl.LazyFrame): The
            nodes generated for the map.
        target_specs (Target): The stats
            used to calculate variance.
        stddev_factor (float): The scaling
            modifier for lane variance.
    Returns:
        pl.LazyFrame: Lane routes with
            density and variance params.
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
    Calculates the spatial Gaussian spread for map routes.

    Args:
        target_map (Map): The map bounds
            for the spatial grid.
        lanes (pl.LazyFrame): The generated
            routes connecting nodes.
    Returns:
        Generator: Generates spatial probability
            matrices per lane.
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
    Simulates volume surges across lanes using amplitude waves.

    Args:
        lanes (pl.LazyFrame): The routes
            to apply traffic surges to.
        start_time (datetime): The absolute
            start of the simulation.
        duration (timedelta): The total
            simulated cycle duration.
        time_steps (int): The resolution
            of the time simulation.
    Returns:
        Generator: Generates traffic volume
            multipliers over time.
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
    Combines spatial and temporal matrices into a final PDF.

    Args:
        target_map (Map): The map bounds
            for the evaluation grid.
        lanes (pl.LazyFrame): The routes
            defining the base traffic.
        start_time (datetime): The start
            time of the simulation.
        duration (timedelta): The length
            of the simulated cycle.
        time_steps (int): The resolution
            of the time simulation.
    Returns:
        Callable: A function that evaluates
            the PDF at a specific time.
    """

    def total_pdf_at_time_per_lane(
        current_time: datetime,
    ) -> Generator[pl.LazyFrame, None, None]:
        """
        Evaluates the probability matrix for an individual route.

        Args:
            current_time (datetime): The exact
                moment to evaluate traffic.
        Returns:
            Generator: The probability states
                for each individual lane.
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
        Sums the individual route matrices into a master heatmap.

        Args:
            current_time (datetime): The exact
                moment to evaluate traffic.
        Returns:
            pl.LazyFrame: The combined final
                probability state grid.
        """
        return (
            pl.concat(list(total_pdf_at_time_per_lane(current_time)))
            .group_by(["x", "y"])
            .agg(pl.sum("pdf").alias("total_pdf"))
        )

    return total_pdf_at_time


def calculate_loot(target: Target) -> float:
    """
    Rolls a randomized reward payout based on target metrics.

    Args:
        target (Target): The enemy drone
            containing the drop stats.
    Returns:
        float: The final randomized
            loot payout value.
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
