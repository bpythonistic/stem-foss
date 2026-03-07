"""
This module contains the target mechanics for the RPG game.
It defines the logic for calculating target behavior, loot distribution, and other related mechanics.

"""

# import os
from typing import Callable
from datetime import datetime, timedelta

import numpy.random as npr
import polars as pl

from app.schemas.sqlmodels import Target, TargetClass, LootDist


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
                description="A large target with high health and low agility.",
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


def generate_behavior(
    target: Target,
) -> Callable[[datetime, timedelta, timedelta], pl.DataFrame]:
    """
    Generate a behavior function for the given target.

    Args:
        target (Target): The target for which to generate the behavior.
        time_step (float): The time step for the behavior generation, in seconds.
    Returns:
        Callable[[datetime, timedelta], pl.DataFrame]: A function that generates the target's behavior over time.
    """

    def update_target_position(
        current_position: float, map_width: float, time_step: timedelta
    ) -> float:
        """
        Update the target's position based on its current position, acceleration, and the time step.

        Args:
            current_position (float): The current position of the target.
        Returns:
            float: The updated position of the target.
        """
        accel = npr.normal(0, (target.accel_max - target.decel_max) ** 0.5 / 2)
        velocity = min(
            max(accel * time_step.total_seconds(), target.top_speed),
            -target.top_speed,
        )
        new_position = current_position + velocity * time_step.total_seconds()
        return max(0, min(new_position, map_width))

    def generate_position_series(
        map_width: float, duration: timedelta, time_step: timedelta
    ) -> pl.Series:
        """
        Generate a series of target positions over time.

        Args:
            map_width (float): The width of the map for position constraints.
        Returns:
            pl.Series: A series of target positions over time.
        """
        positions = []
        current_position = npr.uniform(0, map_width)
        for _ in range(
            int(duration.total_seconds() / time_step.total_seconds())
        ):  # Simulate for 1 minute
            current_position = update_target_position(
                current_position, map_width, time_step
            )
            positions.append(current_position)
        return pl.Series(positions, dtype=pl.Float64)

    def calc_behavior_over_time(
        start_time: datetime, duration: timedelta, time_step: timedelta
    ) -> pl.DataFrame:
        """
        Generate the target's behavior over the specified time range.

        Args:
            time_range (tuple[datetime, timedelta]): A tuple containing the start time and duration for the behavior generation.
        Returns:
            pl.DataFrame: A DataFrame containing the target's behavior data over time.
        """
        end_time = start_time + duration
        behavior = pl.DataFrame(
            {
                "timestamp": pl.time_range(
                    start=start_time.time(),
                    end=end_time.time(),
                    interval=duration,
                    eager=True,
                ),
                "x_position": pl.Series(
                    generate_position_series(
                        map_width=100.0, duration=duration, time_step=time_step
                    )
                ),
                "y_position": pl.Series(
                    generate_position_series(
                        map_width=100.0, duration=duration, time_step=time_step
                    )
                ),
            }
        )
        return behavior

    return calc_behavior_over_time
