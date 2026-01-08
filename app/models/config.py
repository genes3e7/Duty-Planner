from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

class ConstraintsConfig(BaseModel):
    personnel_needed_per_shift: Dict[str, int] = Field(
        default_factory=lambda: {"AM": 1, "PM": 1, "24H": 1}
    )
    standby_per_day: int = 1
    max_consecutive_duties: int = 3

class PointsConfig(BaseModel):
    AM: float = 1.0
    PM: float = 1.0
    # Add alias to serialize as "24H"
    FULL_24H: float = Field(2.0, serialization_alias="24H", validation_alias="24H")
    
    ph_multiplier: float = 2.0
    weekend_multiplier: float = 1.5
    
    ph_is_multiplier: bool = True
    weekend_is_multiplier: bool = True
    
    model_config = ConfigDict(populate_by_name=True)

    def get_by_type(self, shift_type: str) -> float:
        if shift_type == "AM": return self.AM
        if shift_type == "PM": return self.PM
        if shift_type == "24H": return self.FULL_24H
        return 0.0

class AppConfig(BaseModel):
    year: int = 2025
    month: int = 1
    personnel: List[str] = Field(default_factory=list)
    constraints: ConstraintsConfig = Field(default_factory=ConstraintsConfig)
    points: PointsConfig = Field(default_factory=PointsConfig)

    @classmethod
    def default(cls):
        # Generates 20 fake names for easier testing
        fake_names = [f"Staff {i:02d}" for i in range(1, 21)]
        return cls(personnel=fake_names)

    def to_dict(self):
        return self.model_dump(by_alias=True)
    
    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)
