"""
app/models/config.py

Defines the data structures for application configuration using Pydantic.
Includes validation logic to ensure configuration integrity (defensive coding).
"""

import datetime
import logging
from typing import Any, Container, Dict, List, Optional, Union

import pandas as pd
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


def _get_next_month_year() -> int:
    """Returns the year of the next month relative to today."""
    return (datetime.date.today() + relativedelta(months=1)).year


def _get_next_month_month() -> int:
    """Returns the month (1-12) of the next month relative to today."""
    return (datetime.date.today() + relativedelta(months=1)).month


class ConstraintsConfig(BaseModel):
    """
    Configuration for solver constraints and rules.
    """

    personnel_needed_per_shift: Dict[str, int] = Field(default_factory=lambda: {"AM": 1, "PM": 1, "24H": 1})
    """Number of people required for each shift type."""

    standby_per_day: int = Field(1, ge=0)
    """Number of standby (S/B) personnel required per day."""

    max_consecutive_duties: int = Field(3, ge=1)
    """Maximum number of consecutive days a person can work before a break."""

    solver_timeout_seconds: float = Field(10.0, gt=0)
    """Maximum time in seconds the solver is allowed to run."""

    @field_validator("personnel_needed_per_shift")
    @classmethod
    def validate_needs(cls, v: Dict[str, int]) -> Dict[str, int]:
        """Ensures manpower requirements are non-negative."""
        for key, val in v.items():
            if val < 0:
                raise ValueError(f"Personnel needed for '{key}' cannot be negative.")
        return v


class PointsConfig(BaseModel):
    """
    Configuration for the point scoring system.
    """

    AM: float = Field(1.0, ge=0)
    PM: float = Field(1.0, ge=0)
    FULL_24H: float = Field(2.0, ge=0, serialization_alias="24H", validation_alias="24H")
    SB: float = Field(0.0, ge=0, serialization_alias="S/B", validation_alias="S/B")

    ph_multiplier: float = Field(2.0, ge=0)
    ph_eve_multiplier: float = Field(1.5, ge=0)
    weekend_multiplier: float = Field(1.5, ge=0)

    # Friday Split: AM and PM specific configuration
    friday_am_multiplier: float = Field(1.0, ge=0)
    friday_pm_multiplier: float = Field(1.0, ge=0)

    ph_is_multiplier: bool = True
    ph_eve_is_multiplier: bool = True
    weekend_is_multiplier: bool = True

    friday_am_is_multiplier: bool = True
    friday_pm_is_multiplier: bool = True

    model_config = ConfigDict(populate_by_name=True)

    def get_by_type(self, shift_type: str) -> float:
        """
        Retrieves the base point value for a specific shift type.

        Args:
            shift_type (str): The type of shift (AM, PM, 24H, S/B).

        Returns:
            float: The configured base points.

        Raises:
            ValueError: If the shift_type is unknown.
        """
        if shift_type == "AM":
            return self.AM
        if shift_type == "PM":
            return self.PM
        if shift_type == "24H":
            return self.FULL_24H
        if shift_type == "S/B":
            return self.SB

        logger.error(f"Unknown shift type: {shift_type}")
        raise ValueError(f"Unknown shift type: '{shift_type}'. Expected 'AM', 'PM', '24H', or 'S/B'.")

    def calculate_score(
        self,
        date_obj: Union[pd.Timestamp, datetime.date],
        shift_type: str,
        scale: int = 1,
        holidays_obj: Optional[Container] = None,
    ) -> int:
        """
        Calculates the weighted score for a duty on a specific date.

        Args:
            date_obj: The date of the duty.
            shift_type: The type of duty (AM, PM, etc.).
            scale: Scaling factor for integer arithmetic (default 1).
            holidays_obj: Container supporting `in` operator for holiday checks.

        Returns:
            int: The calculated score multiplied by `scale` and rounded.
        """
        try:
            base = self.get_by_type(shift_type)
        except ValueError:
            return 0

        if base == 0:
            return 0

        is_ph = date_obj in holidays_obj if holidays_obj else False
        is_weekend = date_obj.weekday() >= 5  # 5=Sat, 6=Sun
        is_friday = date_obj.weekday() == 4

        is_ph_eve = False
        if holidays_obj:
            next_day = date_obj + datetime.timedelta(days=1)
            is_ph_eve = next_day in holidays_obj

        multiplier = 1.0
        adder = 0.0

        # Priority: PH > PH Eve > Friday (Split) > Weekend
        if is_ph:
            if self.ph_is_multiplier:
                multiplier = self.ph_multiplier
            else:
                adder = self.ph_multiplier
        elif is_ph_eve:
            if self.ph_eve_is_multiplier:
                multiplier = self.ph_eve_multiplier
            else:
                adder = self.ph_eve_multiplier
        elif is_friday:
            # Handle AM vs PM split for Fridays
            if shift_type == "AM":
                if self.friday_am_is_multiplier:
                    multiplier = self.friday_am_multiplier
                else:
                    adder = self.friday_am_multiplier
            elif shift_type == "PM":
                if self.friday_pm_is_multiplier:
                    multiplier = self.friday_pm_multiplier
                else:
                    adder = self.friday_pm_multiplier
            # If 24H/SB on Friday, we treat it as standard (or fall through to Weekend check if Fri was Sat)

        # Only check weekend if we haven't already applied a higher priority rule (like PH)
        elif is_weekend:
            if self.weekend_is_multiplier:
                multiplier = self.weekend_multiplier
            else:
                adder = self.weekend_multiplier

        final_val = ((base * multiplier) + adder) * scale
        return int(round(final_val))


class AppConfig(BaseModel):
    """
    Root configuration object for the application.
    Aggregates personnel lists, constraints, and point settings.
    """

    # Dynamic default: Next month relative to today
    year: int = Field(default_factory=_get_next_month_year, ge=2000, le=2100)
    """Year for the roster planning."""

    month: int = Field(default_factory=_get_next_month_month, ge=1, le=12)
    """Month for the roster planning (1-12)."""

    personnel: List[str] = Field(default_factory=list)
    """List of staff names available for duties."""

    constraints: ConstraintsConfig = Field(default_factory=ConstraintsConfig)
    """Solver constraint settings."""

    points: PointsConfig = Field(default_factory=PointsConfig)
    """Point calculation settings."""

    @classmethod
    def default(cls) -> "AppConfig":
        """
        Creates a default configuration instance with dummy data.

        Returns:
            AppConfig: A pre-populated configuration object.
        """
        fake_names = [f"Staff {i:02d}" for i in range(1, 21)]
        return cls(personnel=fake_names)

    def to_dict(self) -> Dict[str, Any]:
        """
        Exports the configuration to a dictionary suitable for JSON serialization.
        Uses aliases (e.g., '24H' instead of 'FULL_24H').
        """
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """
        Creates a configuration instance from a dictionary.

        Args:
            data (Dict[str, Any]): Dictionary data (e.g., loaded from JSON).

        Returns:
            AppConfig: The validated configuration object.
        """
        return cls.model_validate(data)
