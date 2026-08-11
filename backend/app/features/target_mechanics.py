"""
Defines the mathematical engine for target physics and loot.

- get_target_classes: Retrieves base configurations for tiers.
- generate_hot_spots: Creates randomized congregation centers.
- describe_hot_spots: Assigns density and spread to each hot spot.
- map_hot_spot_density: Maps radial Gaussian spread for hot spots.
- calculate_temporal_hot_spot_density: Simulates dwell surges over time.
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


def get_target_classes(user_id: str, map_id: str) -> tuple[Target, Target, Target]:
    """
    Retrieves the base hardware specifications for target tiers.

    Args:
        user_id (str): The unique identifier
            of the active player.
        map_id (str): The unique identifier
            of the map.
    Returns:
        tuple: The small, medium, and large
            target configurations.
    """
    return (
        Target(
            user_id=user_id,
            map_id=map_id,
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
            map_id=map_id,
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
            map_id=map_id,
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


def generate_hot_spots(target_map: Map, margin: float = 5.00) -> pl.LazyFrame:
    """
    Creates randomized congregation centers for the map.

    Each hot spot is a location where drones pause or gather. Its
    coordinates seed the radial spatial PDF built downstream.

    Args:
        target_map (Map): The map config
            used to define boundaries.
        margin (float): The edge padding
            to prevent clipping hot spots.
    Returns:
        pl.LazyFrame: Generated hot spots
            with coordinate locations.
    """
    return pl.LazyFrame(
        {
            "x": pl.Series(
                "x",
                npr.uniform(
                    margin,
                    target_map.map_size - margin,
                    target_map.num_hot_spots,
                ),
            ),
            "y": pl.Series(
                "y",
                npr.uniform(
                    margin,
                    target_map.map_size - margin,
                    target_map.num_hot_spots,
                ),
            ),  # Random y positions within the map width
        }
    )


def describe_hot_spots(
    target_map: Map,
    hot_spots: pl.LazyFrame,
    target_specs: Target,
    spread_factor: float = 0.2,
) -> pl.LazyFrame:
    """
    Assigns a crowd density and radial spread to each hot spot.

    Args:
        target_map (Map): The operational
            zone configuration.
        hot_spots (pl.LazyFrame): The
            congregation centers generated for the map.
        target_specs (Target): The stats
            used to calculate variance.
        spread_factor (float): The scaling
            modifier for hot spot spread.
    Returns:
        pl.LazyFrame: Hot spot centers with
            density and spread params.
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
    max_spread = (
        spread_factor * (target_specs.top_speed * target_specs.accel_max) ** 0.5
    )
    density_scalar = pl.Series(
        "hot_spot_density", npr.uniform(0, 1, target_map.num_hot_spots)
    )
    hot_spot_spread = pl.Series(
        "hot_spot_spread",
        npr.uniform(0.1 * max_spread, max_spread, target_map.num_hot_spots),
    )
    return hot_spots.with_columns(
        center_x=pl.col("x"),
        center_y=pl.col("y"),
        hot_spot_density=density_scalar
        * (total_targets / target_map.num_hot_spots),  # Random crowd density
        hot_spot_spread=hot_spot_spread,  # Random congregation tightness
    ).select(
        pl.col("center_x"),
        pl.col("center_y"),
        pl.col("hot_spot_density"),
        pl.col("hot_spot_spread"),
    )


def map_hot_spot_density(
    target_map: Map, hot_spots: pl.LazyFrame
) -> Generator[tuple[pl.LazyFrame, pl.LazyFrame], None, None]:
    """
    Calculates the radial Gaussian spread for each hot spot.

    Probability falls off with distance from the congregation center,
    forming a circular blob rather than a ridge along a route.

    Args:
        target_map (Map): The map bounds
            for the spatial grid.
        hot_spots (pl.LazyFrame): The generated
            congregation centers.
    Returns:
        Generator: Generates spatial probability
            matrices per hot spot.
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
    for hot_spot in hot_spots.collect().iter_rows(named=True):
        q2 = (
            q1.with_columns(
                (
                    (pl.col("x") - hot_spot["center_x"]) ** 2
                    + (pl.col("y") - hot_spot["center_y"]) ** 2
                ).alias("dist_sq_to_hot_spot")
            )
            .select(pl.col("x"), pl.col("y"), pl.col("dist_sq_to_hot_spot"))
            .lazy()
        )
        q3 = (
            q2.with_columns(
                (
                    hot_spot["hot_spot_density"]
                    * (
                        -0.5
                        * (
                            pl.col("dist_sq_to_hot_spot")
                            / hot_spot["hot_spot_spread"] ** 2
                        )
                    ).exp()
                ).alias("density")
            )
            .select(pl.col("x"), pl.col("y"), pl.col("density"))
            .lazy()
        )
        yield q3, q1


def calculate_temporal_hot_spot_density(
    hot_spots: pl.LazyFrame,
    start_time: datetime,
    duration: timedelta,
    time_steps: int,
) -> Generator[pl.LazyFrame, None, None]:
    """
    Simulates dwell surges at hot spots using amplitude waves.

    Each hot spot gathers a crowd during randomized dwell windows,
    modelled as Gaussian surges in time around each window.

    Args:
        hot_spots (pl.LazyFrame): The hot spots
            to apply dwell surges to.
        start_time (datetime): The absolute
            start of the simulation.
        duration (timedelta): The total
            simulated cycle duration.
        time_steps (int): The resolution
            of the time simulation.
    Returns:
        Generator: Generates crowd density
            multipliers over time.
    """
    time_series = pl.Series(
        "time",
        pl.linear_space(start_time, start_time + duration, time_steps, eager=True),
    )
    num_dwell_events = pl.Series(
        "num_dwell_events", npr.randint(1, 4, size=hot_spots.collect().shape[0])
    )
    for i, hot_spot in enumerate(hot_spots.collect().iter_rows(named=True)):
        dwell_windows = pl.Series(
            "dwell_windows",
            time_series.sample(num_dwell_events[i], with_replacement=False).sort(),
        ).to_list()
        density_patterns = [
            pl.DataFrame(
                {
                    "time": time_series,
                    "density": (
                        hot_spot["hot_spot_density"]
                        + hot_spot["hot_spot_density"]
                        * (npr.rand() + 1)
                        * 5
                        * (
                            -0.5
                            * (
                                (dwell_window - start_time).total_seconds()
                                - time_series.map_elements(
                                    lambda x: (x - start_time).total_seconds()
                                )
                            )
                            ** 2
                            / (60 * 60) ** 2
                        ).exp()
                    ),
                }
            ).lazy()
            for dwell_window in dwell_windows
        ]
        yield (
            pl.concat(density_patterns)
            .group_by("time")
            .agg(pl.sum("density").alias("total_density"))
        )


def evaluate_total_pdf(
    target_map: Map,
    hot_spots: pl.LazyFrame,
    start_time: datetime,
    duration: timedelta,
    time_steps: int,
) -> Callable[[datetime], pl.LazyFrame]:
    """
    Combines spatial and temporal matrices into a final PDF.

    Args:
        target_map (Map): The map bounds
            for the evaluation grid.
        hot_spots (pl.LazyFrame): The hot spots
            defining the base crowd density.
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

    def total_pdf_at_time_per_hot_spot(
        current_time: datetime,
    ) -> Generator[pl.LazyFrame, None, None]:
        """
        Evaluates the probability matrix for an individual hot spot.

        Args:
            current_time (datetime): The exact
                moment to evaluate crowd density.
        Returns:
            Generator: The probability states
                for each individual hot spot.
        """
        for (spot_density, _), temporal_density in zip(
            map_hot_spot_density(target_map, hot_spots),
            calculate_temporal_hot_spot_density(
                hot_spots, start_time, duration, time_steps
            ),
        ):
            current_density_df = (
                temporal_density.filter(pl.col("time") >= current_time)
                .select("total_density")
                .head(1)
                .collect()
            )
            if current_density_df.height > 0:
                current_density = current_density_df.item(0, 0)
            else:
                current_density = 0.0
            yield (
                spot_density.select(
                    pl.col("x"),
                    pl.col("y"),
                    pl.col("density").alias("spot_density"),
                )
                .with_columns(pdf=(pl.col("spot_density") * current_density))
                .select(pl.col("x"), pl.col("y"), pl.col("pdf").fill_null(0))
                .lazy()
            )

    def total_pdf_at_time(current_time: datetime) -> pl.LazyFrame:
        """
        Sums the individual hot spot matrices into a master heatmap.

        Args:
            current_time (datetime): The exact
                moment to evaluate crowd density.
        Returns:
            pl.LazyFrame: The combined final
                probability state grid.
        """
        return (
            pl.concat(list(total_pdf_at_time_per_hot_spot(current_time)))
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
