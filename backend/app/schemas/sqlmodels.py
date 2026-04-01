"""
Defines the SQLModel data structures and database sessions.

- Category: Enum classifying traits by subsystem.
- Stat: Enum defining core interception metrics.
- TargetClass: Enum categorizing target size and agility.
- LootDist: Enum for loot generation statistical curves.
- User: Database model for player accounts.
- RPGClass: Database model for selectable operator classes.
- Trait: Database model for passive gameplay modifiers.
- Stats: Database model for tracking dynamic player attributes.
- Upgrade: Database model for purchasable hardware enhancements.
- Target: Database model for enemy drone definitions.
- Map: Database model for operational zone configurations.
- get_session: Dependency injector yielding a database session.
"""

import os
from enum import Enum
from typing import Annotated, Generator
from uuid import uuid4

from fastapi.params import Depends
from sqlmodel import Field, Session, SQLModel, create_engine

DEFAULT_CONNECTION_STRING = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://postgres@localhost:5432/stem_db"
)


class Category(str, Enum):
    """
    Classifies traits to determine which subsystem they modify.

    Attributes:
        MONITOR (str): Represents traits affecting
            sensor grids and data gathering.
        CAPTURE (str): Represents traits affecting
            net drop physics and interception.
        REFINE (str): Represents traits affecting
            data processing and PDF analysis.
        OTHER (str): Represents general traits
            outside standard categories.
    """

    MONITOR = "Monitor"
    CAPTURE = "Capture"
    REFINE = "Refine"
    OTHER = "Other"


class Stat(str, Enum):
    """
    Defines the core metrics dictating physical capabilities.

    Attributes:
        RESOLUTION (str): Enhances the spatial
            accuracy of the generated PDF maps.
        NETSPEED (str): Decreases the time of
            flight for dropped capture nets.
        NETSIZE (str): Expands the physical hit
            radius for target interception.
        STEALTH (str): Reduces the player's
            detectability by enemy sensors.
    """

    RESOLUTION = "Resolution"
    NETSPEED = "Net Speed"
    NETSIZE = "Net Size"
    STEALTH = "Stealth"


class TargetClass(str, Enum):
    """
    Categorizes enemy drones by physical size to govern physics.

    Attributes:
        SMALL (str): Highly agile drones that are
            difficult to track and capture.
        MEDIUM (str): Standard courier drones
            with balanced speed and evasion.
        LARGE (str): Heavy transport drones that
            move slowly but yield high loot.
    """

    SMALL = "Small"
    MEDIUM = "Medium"
    LARGE = "Large"


class LootDist(str, Enum):
    """
    Specifies the statistical distribution curve for loot drops.

    Attributes:
        UNIFORM (str): Generates loot evenly
            between defined minimum and maximums.
        NORMAL (str): Generates loot centered
            around a mean value.
        GAUSSIAN (str): Generates loot using a
            Gaussian probability curve.
    """

    UNIFORM = "Uniform"
    NORMAL = "Normal"
    GAUSSIAN = "Gaussian"


class User(SQLModel, table=True):
    """
    Stores player profiles to track individual progression.

    Attributes:
        id (str): Unique UUID4 primary key for
            identifying the player.
        name (str): The player's chosen
            display name or handle.
        class_name (str | None): The selected RPG class
            defining the player's playstyle.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(..., max_length=100)
    class_name: str | None = Field(default=None, max_length=100)


class RPGClass(SQLModel, table=True):
    """
    Defines operator backgrounds providing baseline multipliers.

    Attributes:
        id (str): Unique UUID4 primary key for
            the RPG class entry.
        name (str): The functional title of the
            operator background.
        description (str): Narrative summary of
            the class's tactical approach.
        trait_1 (str): The primary inherent trait
            granted to this class.
        trait_2 (str | None): An optional
            secondary trait for this class.
        trait_3 (str | None): An optional
            tertiary trait for this class.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(..., max_length=100)
    description: str = Field(..., max_length=255)
    trait_1: str = Field(..., max_length=100)
    trait_2: str | None = Field(default=None, max_length=100)
    trait_3: str | None = Field(default=None, max_length=100)


class Trait(SQLModel, table=True):
    """
    Represents passive modifiers that alter a player's stats.

    Attributes:
        id (str): Unique UUID4 primary key for
            the trait entry.
        name (str): The designated title of the
            gameplay modifier.
        description (str): A summary of how the
            trait impacts the simulation.
        category (Category): The subsystem
            classification for this trait.
        modifies (Stat): The specific player stat
            targeted by this modifier.
        multiplier (float): The multiplicative
            factor applied to the target stat.
        offset (float): The additive bonus
            applied to the target stat.
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
    Tracks the dynamic attributes to evaluate match performance.

    Attributes:
        id (str): Unique UUID4 primary key for
            the stat record.
        user_id (str): Foreign key linking the
            stats to a specific user profile.
        stat_type (Stat): The classification of
            the tracked metric.
        stat_min (float): The absolute minimum
            allowable value for this stat.
        stat_max (float): The absolute maximum
            allowable value for this stat.
        base_value (float): The inherent starting
            value before applied modifiers.
        current_value (float): The active value
            after traits and upgrades.
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
    Defines purchasable hardware boosting user stats permanently.

    Attributes:
        id (str): Unique UUID4 primary key for
            the hardware upgrade.
        user_id (str): Foreign key linking the
            upgrade to a specific player.
        name (str): The designated title of the
            hardware component.
        description (str): Narrative detail on
            the component's tactical function.
        cost (int): The required currency
            expenditure to acquire the item.
        effected_stat (Stat): The specific metric
            improved by this purchase.
        stat_multiplier (float): The factor by
            which the target stat is multiplied.
        stat_offset (float): The flat bonus added
            to the target stat.
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
    Models physical characteristics of enemy drones for physics.

        Attributes:
            id (str): Unique UUID4 primary key for
                the enemy drone profile.
            user_id (str): Foreign key linking the
                target generation to a user state.
            name (str): The classification title of
                the specific drone model.
            description (str): Narrative detail of
                the drone's operational role.
            category (TargetClass): The size tier
                dictating agility and physics.
            top_speed (float): The maximum velocity
                achievable during flight.
            accel_max (float): The maximum forward
                acceleration capability.
            decel_max (float): The maximum braking or
                reverse acceleration capacity.
            hitbox_size (float): The radial dimension
                required for a successful net hit.
            loot_dist (LootDist): The statistical
                model used for reward generation.
            loot_min (float): The absolute baseline
                reward for a successful capture.
            loot_max (float): The absolute ceiling
                reward for a successful capture.
            loot_mean (float | None): The central
                average for normal distributions.
            loot_stddev (float | None): The variance
                spread for randomized loot pulls.
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


class Map(SQLModel, table=True):
    """
    Defines spatial boundaries and zone traffic configurations.

    Attributes:
        id (str): Unique UUID4 primary key for
            the map configuration instance.
        user_id (str): Foreign key linking the
            map state to an active session.
        name (str): The designated title of the
            operational sector.
        description (str): Narrative summary of
            the zone's environment and hazards.
        map_size (float): The total Cartesian
            dimension of the grid area.
        samples (int): The grid resolution for
            matrix granularity.
        num_small_targets (int): Total volume of
            agile courier drones in the zone.
        num_medium_targets (int): Total volume of
            standard drones in the zone.
        num_large_targets (int): Total volume of
            heavy transport drones in the zone.
        num_heat_points (int): The number of origin
            and destination nodes for lanes.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: str = Field(...)
    name: str = Field(...)
    description: str = Field(...)
    map_size: float = Field(..., gt=0)
    samples: int = Field(..., gt=0)
    num_small_targets: int = Field(..., gt=0)
    num_medium_targets: int = Field(..., gt=0)
    num_large_targets: int = Field(..., gt=0)
    num_heat_points: int = Field(..., gt=0)


def get_session() -> Generator[Session, None, None]:
    """
    Injects a PostgreSQL database session into route handlers.

    Yields:
        Generator: An active SQLModel db session instance.
    """
    engine = create_engine(DEFAULT_CONNECTION_STRING)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
