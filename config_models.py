"""
config_models.py

Defines Data Classes for App Configuration.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any
from constants import ShiftType

@dataclass
class ConstraintsConfig:
    """Manpower Rules."""
    standby_per_day: int = 1
    personnel_needed_per_shift: Dict[str, int] = field(default_factory=lambda: {
        ShiftType.AM.value: 1, 
        ShiftType.PM.value: 1, 
        ShiftType.FULL_24H.value: 1
    })

@dataclass
class PointsConfig:
    """Scoring Rules."""
    AM: float = 1.0
    PM: float = 1.0
    FULL_24H: float = 3.0 
    STANDBY: float = 0.0
    weekend_multiplier: float = 1.5
    ph_multiplier: float = 2.0

    def get_by_type(self, shift_type: str) -> float:
        if shift_type == ShiftType.AM: return self.AM
        if shift_type == ShiftType.PM: return self.PM
        if shift_type == ShiftType.FULL_24H: return self.FULL_24H
        if shift_type == ShiftType.STANDBY: return self.STANDBY
        return 0.0

@dataclass
class AppConfig:
    """Root Config."""
    year: int
    month: int
    personnel: List[str]
    mode: str
    points: PointsConfig
    constraints: ConstraintsConfig

    @classmethod
    def default(cls) -> 'AppConfig':
        """Default factory."""
        return cls(
            year=2025,
            month=1,
            mode="hybrid",
            personnel=["A", "B", "C", "D", "E", "F", "G", "H", "I"],
            points=PointsConfig(),
            constraints=ConstraintsConfig()
        )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['points']['24H'] = data['points'].pop('FULL_24H')
        data['points']['S/B'] = data['points'].pop('STANDBY')
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        try:
            pts = data.get('points', {})
            p_conf = PointsConfig(
                AM=pts.get('AM', 1.0),
                PM=pts.get('PM', 1.0),
                FULL_24H=pts.get('24H', 3.0),
                STANDBY=pts.get('S/B', 0.0),
                weekend_multiplier=pts.get('weekend_multiplier', 1.5),
                ph_multiplier=pts.get('ph_multiplier', 2.0)
            )
            c_data = data.get('constraints', {})
            c_conf = ConstraintsConfig(
                standby_per_day=c_data.get('standby_per_day', 1),
                personnel_needed_per_shift=c_data.get('personnel_needed_per_shift', {
                    "AM": 1, "PM": 1, "24H": 1
                })
            )
            return cls(
                year=data.get('year', 2025),
                month=data.get('month', 1),
                mode=data.get('mode', 'hybrid'),
                personnel=data.get('personnel', []),
                points=p_conf,
                constraints=c_conf
            )
        except Exception:
            return cls.default()
