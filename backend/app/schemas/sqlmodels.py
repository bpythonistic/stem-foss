"""
This module defines the data models for the application using SQLModel.

It includes:

- User: Represents a user in the system with attributes like id,
    name, and class_name.
- RPGClass: Represents a role-playing game class in the system
    with attributes like id, name, and description.
- Trait: Represents a trait in the system with attributes like id,
    name, description, category, and modifies.
- get_session: A utility function to provide a database session
    for executing queries.
"""

import os
from uuid import uuid4
from typing import Annotated, Generator
from enum import Enum

# from typing import Optional
from fastapi.params import Depends
from sqlmodel import SQLModel, Field, Session, create_engine

DEFAULT_CONNECTION_STRING = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://postgres@localhost:5432/stem_db"
)


class Category(str, Enum):
    """
    Enum representing the categories of traits in the system.

    Attributes:
        MONITOR: Represents monitoring traits.
        CAPTURE: Represents capturing traits.
        REFINE: Represents refining traits.
        OTHER: Represents other traits.
    """

    MONITOR = "Monitor"
    CAPTURE = "Capture"
    REFINE = "Refine"
    OTHER = "Other"


class Stat(str, Enum):
    """
    Enum representing the stats that traits can modify in the system.

    Attributes:
        RESOLUTION: Represents resolution stat.
        NETSPEED: Represents net speed stat.
        NETSIZE: Represents net size stat.
        STEALTH: Represents stealth stat.
    """

    RESOLUTION = "Resolution"
    NETSPEED = "Net Speed"
    NETSIZE = "Net Size"
    STEALTH = "Stealth"


class TargetClass(str, Enum):
    """
    Enum representing the classes of targets in the system.

    Attributes:
        SMALL: Represents small targets.
        MEDIUM: Represents medium targets.
        LARGE: Represents large targets.
    """

    SMALL = "Small"
    MEDIUM = "Medium"
    LARGE = "Large"


class LootDist(str, Enum):
    """
    Enum representing the loot distribution types for targets in the system.

    Attributes:
        UNIFORM: Represents a uniform loot distribution.
        NORMAL: Represents a normal loot distribution.
        GAUSSIAN: Represents a Gaussian loot distribution.
    """

    UNIFORM = "Uniform"
    NORMAL = "Normal"
    GAUSSIAN = "Gaussian"


class User(SQLModel, table=True):
    """
    Represents a user in the system.

    Attributes:
        id (str): Unique identifier for the user, generated using UUID4.
        name (str): The name of the user.
        class_name (str): The name of the RPG class associated with the user.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(..., max_length=100)
    class_name: str = Field(..., max_length=100)


class RPGClass(SQLModel, table=True):
    """
    Represents a role-playing game class in the system.

    Attributes:
        id (str): Unique identifier for the RPG class, generated using UUID4.
        name (str): The name of the RPG class.
        description (str): A brief description of the RPG class.
        trait_1 (str): The first trait of the RPG class.
        trait_2 (str | None): The second trait of the RPG class.
        trait_3 (str | None): The third trait of the RPG class.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(..., max_length=100)
    description: str = Field(..., max_length=255)
    trait_1: str = Field(..., max_length=100)
    trait_2: str | None = Field(default=None, max_length=100)
    trait_3: str | None = Field(default=None, max_length=100)


class Trait(SQLModel, table=True):
    """
    Represents a trait in the system.

    Attributes:
        id (str): Unique identifier for the trait, generated using UUID4.
        name (str): The name of the trait.
        description (str): A brief description of the trait.
        category (Category): The category of the trait, represented as an enum.
        modifies (Stat): The stat that the trait modifies,
            represented as an enum.
        multiplier (float): The multiplier applied to the modified stat, with a
            default value of 1 and constraints to ensure it's
            greater than 0 and less than or equal to 10.
        offset (float): The offset applied to the modified stat,
            with a default value of 0.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(..., max_length=100)
    description: str = Field(..., max_length=255)
    category: Category = Field(...)
    modifies: Stat = Field(...)
    multiplier: float = Field(default=1, gt=0, le=10)
    offset: float = Field(default=0, ge=0)


class Stats(SQLModel, table=True):
    """
    Represents the stats of a user in the system.

    Attributes:
        id (str): Unique identifier for the stats entry, generated using UUID4.
        user_id (str): The ID of the user to whom these stats belong.
        stat_type (Stat): The type of stat, represented as an enum.
        stat_min (float): The minimum value of the stat, with a default value of
            0 and a constraint to ensure it's greater than or equal to 0.
        stat_max (float): The maximum value of the stat, with a constraint to
            ensure it's greater than 1.
        base_value (float): The base value of the stat, with a default value of
            1 and a constraint to ensure it's greater than 0.
        current_value (float): The current value of the stat, with a default value
            of 1 and a constraint to ensure it's greater than 0.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: str = Field(...)
    stat_type: Stat = Field(...)
    stat_min: float = Field(default=0, ge=0)
    stat_max: float = Field(..., gt=1)
    base_value: float = Field(default=1, gt=0)
    current_value: float = Field(default=1, gt=0)


class Upgrade(SQLModel, table=True):
    """
    Represents an upgrade applied to a user in the system.

    Attributes:
        id (str): Unique identifier for the upgrade entry, generated using UUID4.
        user_id (str): The ID of the user to whom this upgrade belongs.
        name (str): The name of the upgrade.
        description (str): A brief description of the upgrade.
        cost (int): The cost of the upgrade, with a constraint to ensure it's
            greater than or equal to 0.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: str = Field(...)
    name: str = Field(...)
    description: str = Field(...)
    cost: int = Field(..., ge=0)
    effected_stat: Stat = Field(...)
    stat_multiplier: float = Field(default=1, gt=0, le=10)
    stat_offset: float = Field(default=0, ge=0)


class Target(SQLModel, table=True):
    """
    Represents a target in the system.

    Attributes:
        id (str): Unique identifier for the target entry, generated using UUID4.
        user_id (str): The ID of the user to whom this target belongs.
        name (str): The name of the target.
        description (str): A brief description of the target.
        category (TargetClass): The category of the target,
            represented as an enum.
        top_speed (float): The top speed of the target, with a
            constraint to ensure it's greater than 0.
        accel_max (float): The maximum acceleration of the target, with a
            constraint to ensure it's greater than 0.
        decel_max (float): The maximum deceleration of the target, with a
            constraint to ensure it's less than 0.
        hitbox_size (float): The size of the target's hitbox, with a
            constraint to ensure it's greater than 0.
        loot_dist (LootDist): The loot distribution type for the target,
            represented as an enum, with a default value of LootDist.UNIFORM.
        loot_min (float): The minimum loot value for the target, with a default
            value of 0 and a constraint to ensure it's greater than or equal to 0.
        loot_max (float): The maximum loot value for the target, with a
            constraint to ensure it's greater than 0.
        loot_mean (float | None): The mean loot value for the target, with a
            default value of None and a constraint to ensure
            it's greater than 0 if provided.
        loot_stddev (float | None): The standard deviation of the loot
            value for the target, with a default value of None and a
            constraint to ensure it's greater than or equal to 0 if provided.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: str = Field(...)
    name: str = Field(...)
    description: str = Field(...)
    category: TargetClass = Field(...)
    top_speed: float = Field(..., gt=0)
    accel_max: float = Field(..., gt=0)
    decel_max: float = Field(..., lt=0)
    hitbox_size: float = Field(..., gt=0)
    loot_dist: LootDist = Field(default=LootDist.UNIFORM)
    loot_min: float = Field(default=0, ge=0)
    loot_max: float = Field(..., gt=0)
    loot_mean: float | None = Field(default=None, gt=0)
    loot_stddev: float | None = Field(default=None, ge=0)


def get_session() -> Generator[Session, None, None]:
    """
    Provides a database session for executing queries.

    Yields:
        Session: A SQLModel session object for database operations.
    """
    engine = create_engine(DEFAULT_CONNECTION_STRING)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
