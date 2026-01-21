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
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.constants import ACTIVE_DUTIES, RuleStatus

logger = logging.getLogger(__name__)


def _get_next_month_year() -> int:
    """Returns the year of the next month relative to today."""
    return (datetime.date.today() + relativedelta(months=1)).year


def _get_next_month_month() -> int:
    """Returns the month (1-12) of the next month relative to today."""
    return (datetime.date.today() + relativedelta(months=1)).month


def _deep_update(target: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively updates a dictionary.
    Used to merge partial uploaded configs into the existing full config.
    """
    for key, value in update.items():
        if isinstance(value, dict) and key in target and isinstance(target[key], dict):
            _deep_update(target[key], value)
        else:
            target[key] = value
    return target


def _default_transition_rules() -> Dict[str, Dict[str, str]]:
    """Generates the default transition matrix (backward compatible)."""
    # Initialize all as Allowed
    shifts = sorted(list(ACTIVE_DUTIES))
    matrix = {s1: {s2: RuleStatus.ALLOWED.value for s2 in shifts} for s1 in shifts}

    # Apply Default Hard Bans
    hard_bans = [
        ("PM", "AM"),
        ("PM", "PM"),
        ("PM", "24H"),
        ("24H", "AM"),
        ("24H", "24H"),
        ("24H", "S/B"),
        ("S/B", "24H"),
    ]
    for s1, s2 in hard_bans:
        if s1 in matrix and s2 in matrix[s1]:
            matrix[s1][s2] = RuleStatus.HARD.value

    # Apply Default Soft Bans
    soft_bans = [("AM", "PM"), ("PM", "S/B"), ("S/B", "AM"), ("S/B", "S/B")]
    for s1, s2 in soft_bans:
        if s1 in matrix and s2 in matrix[s1]:
            matrix[s1][s2] = RuleStatus.SOFT.value

    return matrix


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

    catch_up_limit: float = Field(0.0, ge=0.0)
    """Max extra points above average a person can work. 0 means unlimited."""

    solver_timeout_seconds: float = Field(90.0, ge=1.0)
    """Maximum time (in seconds) the solver is allowed to run."""

    @field_validator("personnel_needed_per_shift")
    @classmethod
    def validate_needs(cls, v: Dict[str, int]) -> Dict[str, int]:
        """Ensures manpower requirements are non-negative and keys are valid."""
        valid_shifts = {"AM", "PM", "24H"}
        for key, val in v.items():
            if key not in valid_shifts:
                raise ValueError(f"Invalid shift key '{key}'. Expected one of {valid_shifts}")
            if val < 0:
                raise ValueError(f"Personnel needed for '{key}' cannot be negative.")
        return v


class PointsConfig(BaseModel):
    """
    Configuration for the point scoring system.
    """

    # Base Points
    AM: float = Field(1.0, ge=0)
    PM: float = Field(1.0, ge=0)
    FULL_24H: float = Field(2.0, ge=0, serialization_alias="24H", validation_alias="24H")
    SB: float = Field(0.0, ge=0, serialization_alias="S/B", validation_alias="S/B")

    # Multipliers
    ph_multiplier: float = Field(2.0, ge=0)
    ph_eve_am_multiplier: float = Field(1.5, ge=0)
    ph_eve_pm_multiplier: float = Field(1.5, ge=0)
    ph_eve_24h_multiplier: float = Field(1.5, ge=0)
    weekend_multiplier: float = Field(1.5, ge=0)
    friday_am_multiplier: float = Field(1.0, ge=0)
    friday_pm_multiplier: float = Field(1.0, ge=0)
    friday_24h_multiplier: float = Field(1.0, ge=0)

    # Boolean Toggles
    ph_is_multiplier: bool = True
    ph_eve_am_is_multiplier: bool = True
    ph_eve_pm_is_multiplier: bool = True
    ph_eve_24h_is_multiplier: bool = True
    weekend_is_multiplier: bool = True
    friday_am_is_multiplier: bool = True
    friday_pm_is_multiplier: bool = True
    friday_24h_is_multiplier: bool = True

    model_config = ConfigDict(populate_by_name=True)

    def get_by_type(self, shift_type: str) -> float:
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
        try:
            base = self.get_by_type(shift_type)
        except ValueError:
            return 0

        if base == 0:
            return 0

        is_ph = date_obj in holidays_obj if holidays_obj else False
        is_weekend = date_obj.weekday() >= 5
        is_friday = date_obj.weekday() == 4

        is_ph_eve = False
        if holidays_obj:
            next_day = date_obj + datetime.timedelta(days=1)
            is_ph_eve = next_day in holidays_obj

        multiplier = 1.0
        adder = 0.0

        if is_ph:
            if self.ph_is_multiplier:
                multiplier = self.ph_multiplier
            else:
                adder = self.ph_multiplier
        elif is_ph_eve:
            if shift_type == "AM":
                if self.ph_eve_am_is_multiplier:
                    multiplier = self.ph_eve_am_multiplier
                else:
                    adder = self.ph_eve_am_multiplier
            elif shift_type == "PM":
                if self.ph_eve_pm_is_multiplier:
                    multiplier = self.ph_eve_pm_multiplier
                else:
                    adder = self.ph_eve_pm_multiplier
            elif shift_type == "24H":
                if self.ph_eve_24h_is_multiplier:
                    multiplier = self.ph_eve_24h_multiplier
                else:
                    adder = self.ph_eve_24h_multiplier
        elif is_friday:
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
            elif shift_type == "24H":
                if self.friday_24h_is_multiplier:
                    multiplier = self.friday_24h_multiplier
                else:
                    adder = self.friday_24h_multiplier
        elif is_weekend:
            if self.weekend_is_multiplier:
                multiplier = self.weekend_multiplier
            else:
                adder = self.weekend_multiplier

        final_val = ((base * multiplier) + adder) * scale
        return int(round(final_val))


class RulesConfig(BaseModel):
    """
    Configuration for shift transition rules (Hard/Soft bans).
    """

    # Map: Current Shift -> Next Shift -> Status
    transitions: Dict[str, Dict[str, str]] = Field(default_factory=_default_transition_rules)


class AppConfig(BaseModel):
    """
    Root configuration object for the application.
    """

    year: int = Field(default_factory=_get_next_month_year, ge=2000, le=2100)
    month: int = Field(default_factory=_get_next_month_month, ge=1, le=12)
    country_code: str = Field("SG")
    personnel: List[str] = Field(default_factory=list)

    constraints: ConstraintsConfig = Field(default_factory=ConstraintsConfig)
    points: PointsConfig = Field(default_factory=PointsConfig)
    rules: RulesConfig = Field(default_factory=RulesConfig)

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not v.isalpha():
            logger.warning(f"Invalid country code '{v}' detected. Defaulting to 'SG'.")
            return "SG"
        return v.upper()

    @classmethod
    def default(cls) -> "AppConfig":
        fake_names = [f"Staff {i:02d}" for i in range(1, 21)]
        return cls(personnel=fake_names)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        return cls.model_validate(data)

    @classmethod
    def from_dict_with_recovery(cls, data: Dict[str, Any], fallback: Optional["AppConfig"] = None) -> "AppConfig":
        if fallback is None:
            fallback = cls()

        current_data = fallback.model_dump(by_alias=True)
        _deep_update(current_data, data)

        retries = 3
        for _ in range(retries):
            try:
                return cls.model_validate(current_data)
            except ValidationError as e:
                for error in e.errors():
                    loc = error["loc"]
                    logger.warning(f"Config Validation Error at {loc}: {error['msg']}. Resetting to fallback value.")

                    if len(loc) == 1:
                        key = loc[0]
                        if key in current_data:
                            del current_data[key]
                    elif len(loc) > 1 and isinstance(current_data.get(loc[0]), dict):
                        sub = current_data[loc[0]]
                        if loc[1] in sub:
                            del sub[loc[1]]

        return fallback
