"""
This module contains the target mechanics for the RPG game.
It defines the logic for calculating target behavior,
loot distribution, and other related mechanics.

"""

# import os
from typing import Generator

import numpy.random as npr
import numpy as np
import polars as pl

from app.schemas.sqlmodels import Target, TargetClass, LootDist, Map


def generate_random_target(target_class: TargetClass, user_id: str) -> Target:
    """
    Generate a random target based on the specified target class.

    Args:
        target_class (TargetClass): The class of the target to generate.
    Returns:
        Target: A randomly generated target object.
    """
    match target_class:
        case TargetClass.SMALL:
            return Target(
                user_id=user_id,
                name="Small Target",
                description="A small target with high agility.",
                category=target_class,
                top_speed=10.0,
                accel_max=5.0,
                decel_max=-5.0,
                hitbox_size=0.5,
                loot_dist=LootDist.GAUSSIAN,
                loot_min=3,
                loot_max=8,
                loot_mean=5,
                loot_stddev=1,
            )
        case TargetClass.MEDIUM:
            return Target(
                user_id=user_id,
                name="Medium Target",
                description="A medium target with balanced stats.",
                category=target_class,
                top_speed=8.0,
                accel_max=4.0,
                decel_max=-4.0,
                hitbox_size=1.0,
                loot_dist=LootDist.GAUSSIAN,
                loot_min=5,
                loot_max=12,
                loot_mean=8,
                loot_stddev=2,
            )
        case TargetClass.LARGE:
            return Target(
                user_id=user_id,
                name="Large Target",
                description="A large target with low agility.",
                category=target_class,
                top_speed=6.0,
                accel_max=3.0,
                decel_max=-3.0,
                hitbox_size=1.5,
                loot_dist=LootDist.GAUSSIAN,
                loot_min=8,
                loot_max=15,
                loot_mean=11,
                loot_stddev=2,
            )
        case _:
            raise ValueError(f"Invalid target class: {target_class}")


def generate_map_heat_points(target_map: Map, margin: float = 5.00) -> pl.DataFrame:
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
        pl.DataFrame: A DataFrame containing the
            generated heat points with
            their positions and visit durations.
    """
    return pl.DataFrame(
        {
            "x": npr.uniform(
                margin, target_map.map_size - margin, target_map.num_heat_points
            ),  # Random x positions within the map width
            "y": npr.uniform(
                margin, target_map.map_size - margin, target_map.num_heat_points
            ),  # Random y positions within the map width
            "visit_duration": min(
                max(npr.normal(180, 30, target_map.num_heat_points), 30), 360
            ),  # Random visit durations with a normal distribution
        }
    )


def describe_lanes(target_map: Map, heat_points: pl.DataFrame) -> pl.DataFrame:
    """
    Describe the lanes on the map based on the heat points.

    Args:
        target_map (Map): The map on which the lanes are located.
        heat_points (pl.DataFrame): The heat points on the map.

    Returns:
        pl.DataFrame: A DataFrame containing the description of the lanes.
    """
    return pl.DataFrame(
        {
            "lane_id": pl.arange(0, target_map.num_heat_points),
            "x_start": heat_points["x"],
            "y_start": heat_points["y"],
            "x_end": heat_points["x"].shift(-1).fill_null(heat_points["x"].first()),
            "y_end": heat_points["y"].shift(-1).fill_null(heat_points["y"].first()),
            "traffic_density": npr.uniform(0, 1, target_map.num_heat_points)
            * (
                target_map.num_targets / target_map.num_heat_points
            ),  # Random traffic density
            "traffic_stddev": npr.uniform(
                0.1, 0.5, target_map.num_heat_points
            ),  # Random traffic variability
        }
    )


def map_lane_traffic(
    target_map: Map, lanes: pl.DataFrame
) -> Generator[pl.LazyFrame, None, None]:
    """
    Map the traffic on the lanes based on the traffic density and variability.

    Args:
        target_map (Map): The map on which the lanes are located.
        lanes (pl.DataFrame): The DataFrame containing the description of the lanes.

    Returns:
        pl.DataFrame: A DataFrame containing the mapped traffic on the lanes.
    """
    x_values = pl.linear_space(0, target_map.map_size, target_map.resolution)
    y_values = pl.linear_space(0, target_map.map_size, target_map.resolution)

    lane_indices = pl.Series("lane_idx", pl.arange(0, target_map.num_heat_points))
    for i in lane_indices:
        q1 = pl.DataFrame(
            {
                "x": x_values.slice(lanes[i, "x_start"], lanes[i, "x_end"]),
                "y": y_values.slice(lanes[i, "y_start"], lanes[i, "y_end"]),
            }
        ).lazy()
        q2 = (
            q1.select(pl.col("x"))
            .join(q1.select(pl.col("y")), how="cross")
            .with_columns(
                (
                    pl.col("x") * (lanes[i, "y_end"] - lanes[i, "y_start"])
                    - pl.col("y") * (lanes[i, "x_end"] - lanes[i, "x_start"])
                    + lanes[i, "y_start"] * lanes[i, "x_end"]
                    - lanes[i, "y_end"] * lanes[i, "x_start"]
                )
                .abs()
                .alias("dist_to_lane")
            )
        ).lazy()
        q3 = q2.with_columns(
            (
                lanes[i, "traffic_density"]
                * np.exp(
                    -0.5
                    * (pl.col("dist_to_lane") ** 2 / lanes[i, "traffic_stddev"] ** 2)
                )
            ).alias("traffic")
        ).lazy()
        yield q3


def calculate_temporal_lane_traffic(
    target_map: Map, lanes: pl.DataFrame, time_steps: int
) -> Generator[pl.LazyFrame, None, None]:
    """
    Calculate the temporal lane traffic based on the traffic density and variability.

    Args:
        target_map (Map): The map on which the lanes are located.
        lanes (pl.DataFrame): The DataFrame containing the description of the lanes.
        time_steps (int): The number of time steps over a day to simulate.

    Returns:
        pl.DataFrame: A DataFrame containing the temporal lane traffic.
    """
    lane_indices = pl.Series("lane_idx", pl.arange(0, target_map.num_heat_points))
    time_series = pl.Series(
        "time",
        pl.linear_space(
            0, 24 * 60 * 60, time_steps
        ),  # Simulate every second of the day
    )
    for i in lane_indices:
        rush_hours = npr.randint(1, 4)  # Random number of rush hours
        rush_hour_df = pl.DataFrame(
            {
                "rush_hour_times": time_series.sample(
                    rush_hours, with_replacement=False
                ).alias("rush_hour_times"),
            }
        )
        traffic_patterns = [
            pl.DataFrame(
                {
                    "time": time_series,
                    "traffic": (
                        lanes[i, "traffic_density"]
                        + lanes[i, "traffic_density"]
                        * (npr.rand() + 1)
                        * 5
                        * np.exp(
                            -0.5
                            * (rush_hour_df[j, "rush_hour_times"] - time_series) ** 2
                            / (60 * 60) ** 2
                        )
                    ),
                }
            ).lazy()
            for j in range(rush_hours)
        ]
        yield (
            pl.concat(traffic_patterns)
            .group_by("time")
            .agg(pl.sum("traffic").alias("total_traffic"))
        )
