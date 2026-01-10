import datetime
import logging
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class ConstraintsConfig(BaseModel):
    personnel_needed_per_shift: Dict[str, int] = Field(default_factory=lambda: {"AM": 1, "PM": 1, "24H": 1})
    standby_per_day: int = 1
    max_consecutive_duties: int = 3
    solver_timeout_seconds: float = 10.0


class PointsConfig(BaseModel):
    AM: float = 1.0
    PM: float = 1.0
    FULL_24H: float = Field(2.0, serialization_alias="24H", validation_alias="24H")
    # S/B points are usually 0, but can be configured if needed.
    # If not present in config JSON, defaults will be used.
    # Note: 'S/B' key handling depends on how it's passed.

    ph_multiplier: float = 2.0
    ph_eve_multiplier: float = 1.5
    weekend_multiplier: float = 1.5
    friday_multiplier: float = 1.0  # Default to 1.0 (no change) if not specified

    ph_is_multiplier: bool = True
    ph_eve_is_multiplier: bool = True
    weekend_is_multiplier: bool = True
    friday_is_multiplier: bool = True

    model_config = ConfigDict(populate_by_name=True)

    def get_by_type(self, shift_type: str) -> float:
        if shift_type == "AM":
            return self.AM
        if shift_type == "PM":
            return self.PM
        if shift_type == "24H":
            return self.FULL_24H
        if shift_type == "S/B":
            # Return 0.0 by default for S/B if not explicitly defined in fields,
            # or add a field for it if needed. For now assuming 0.0 or handled by caller logic
            # if explicit field missing.
            # However, prompt implies generic handling.
            # Let's return 0.0 safely.
            return 0.0

        logger.error(f"Unknown shift type: {shift_type}")
        raise ValueError(f"Unknown shift type: '{shift_type}'. Expected 'AM', 'PM', '24H', or 'S/B'.")

    def calculate_score(
        self,
        date_obj: Union[pd.Timestamp, datetime.date],
        shift_type: str,
        scale: int = 1,
        holidays_obj: Optional[Any] = None,
    ) -> int:
        """
        Centralized scoring logic. Returns SCALED integer points.
        """
        try:
            base = self.get_by_type(shift_type)
        except ValueError:
            return 0

        if base == 0:
            return 0

        # Determine multipliers
        is_ph = date_obj in holidays_obj if holidays_obj else False
        is_weekend = date_obj.weekday() >= 5  # 5=Sat, 6=Sun
        is_friday = date_obj.weekday() == 4

        # PH Eve Check
        is_ph_eve = False
        if holidays_obj:
            next_day = date_obj + datetime.timedelta(days=1)
            is_ph_eve = next_day in holidays_obj

        multiplier = 1.0
        adder = 0.0

        # Priority: PH > PH Eve > Friday > Weekend
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
            if self.friday_is_multiplier:
                multiplier = self.friday_multiplier
            else:
                adder = self.friday_multiplier
        elif is_weekend:
            if self.weekend_is_multiplier:
                multiplier = self.weekend_multiplier
            else:
                adder = self.weekend_multiplier

        # Calculate scaled integer
        final_val = ((base * multiplier) + adder) * scale
        return int(round(final_val))


class AppConfig(BaseModel):
    year: int = 2025
    month: int = 1
    personnel: List[str] = Field(default_factory=list)
    constraints: ConstraintsConfig = Field(default_factory=ConstraintsConfig)
    points: PointsConfig = Field(default_factory=PointsConfig)

    @classmethod
    def default(cls):
        fake_names = [f"Staff {i:02d}" for i in range(1, 21)]
        return cls(personnel=fake_names)

    def to_dict(self):
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: Dict):
        return cls.model_validate(data)
