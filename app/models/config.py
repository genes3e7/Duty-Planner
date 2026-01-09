import logging
from typing import Dict, List

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
    # Added "S/B" (Standby) default points, assuming 0.0 or low if not specified.
    # The user didn't ask for S/B points explicitly but good to have if we use get_by_type("S/B")
    SB: float = Field(0.0, serialization_alias="S/B", validation_alias="S/B")

    # Existing Multipliers
    ph_multiplier: float = 2.0
    weekend_multiplier: float = 1.5

    # New Multipliers
    ph_eve_multiplier: float = 1.5
    friday_multiplier: float = 1.5

    # Toggle Logic
    ph_is_multiplier: bool = True
    weekend_is_multiplier: bool = True
    ph_eve_is_multiplier: bool = True
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
            return self.SB

        logger.error(f"Unknown shift type: {shift_type}")
        raise ValueError(f"Unknown shift type: '{shift_type}'. Expected 'AM', 'PM', '24H', or 'S/B'.")


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
