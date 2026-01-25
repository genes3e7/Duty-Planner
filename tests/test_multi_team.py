"""
tests/test_multi_team.py

Integration tests for the Multi-Team functionality in the Scheduler Engine.
Verifies variable creation, coverage enforcement, and rule application across teams.
"""

import pytest

from app.constants import RuleStatus, ScheduleMode
from app.core.scheduler import DutySchedulerEngine, SolverRequest
from app.models.config import AppConfig


@pytest.fixture
def multi_team_config():
    """
    Creates a configuration with:
    - 2 Active Teams (AM, PM, 24H per team)
    - 2 Standby Teams
    - 6 Staff members
    """
    cfg = AppConfig.default()
    cfg.personnel = ["A", "B", "C", "D", "E", "F"]
    cfg.constraints.num_active_teams = 2
    cfg.constraints.num_standby_teams = 2

    # Requirement: 1 person per shift type per team
    cfg.constraints.personnel_needed_per_shift = {"AM": 1, "PM": 1, "24H": 1}
    cfg.constraints.standby_per_day = 1

    return cfg


@pytest.fixture
def simple_request(multi_team_config):
    """Creates a simple 2-day request."""
    return SolverRequest(
        staff_ids=multi_team_config.personnel,
        year=2025,
        month=1,
        fixed_assignments={},
        day_modes={1: ScheduleMode.SHIFT.value, 2: ScheduleMode.SHIFT.value},
        inactive_days=[],
        shift_weights={},  # Weights aren't critical for feasibility tests
    )


def test_variable_creation_multi_team(multi_team_config, simple_request):
    """
    Verify that the scheduler creates variables for Team 2 shifts.
    """
    engine = DutySchedulerEngine(multi_team_config, {}, simple_request)
    engine.build_model()

    # Check for Standard Shifts (Team 1)
    assert ("A", 1, "AM") in engine.vars
    assert ("A", 1, "S/B") in engine.vars

    # Check for Team 2 Shifts
    assert ("A", 1, "AM_2") in engine.vars
    assert ("A", 1, "PM_2") in engine.vars
    assert ("A", 1, "S/B_2") in engine.vars


def test_coverage_enforcement(multi_team_config, simple_request):
    """
    Verify that the solver assigns staff to BOTH teams.
    If we need 1 AM per team, and have 2 teams, we need 2 people on AM total.
    """
    # Reduce staff to exactly matches needs to force specific assignments
    # Needs per day:
    #   Team 1: 1 AM, 1 PM (2 people)
    #   Team 2: 1 AM, 1 PM (2 people)
    #   Total: 4 people per day
    multi_team_config.personnel = ["P1", "P2", "P3", "P4"]
    simple_request.staff_ids = multi_team_config.personnel

    # Disable Standby to simplify
    multi_team_config.constraints.num_standby_teams = 0

    # RELAX RULES: Ensure strict PM->PM and PM->AM hard bans don't make
    # the schedule impossible with such a small staff count.
    multi_team_config.rules.transitions["PM"]["AM"] = RuleStatus.ALLOWED.value
    multi_team_config.rules.transitions["PM"]["PM"] = RuleStatus.ALLOWED.value

    engine = DutySchedulerEngine(multi_team_config, {}, simple_request)
    engine.build_model()
    result = engine.solve()

    assert result is not None
    schedule, _ = result

    # Check Day 1 assignments
    day1_assignments = [s for (p, d), s in schedule.items() if d == 1]

    assert "AM" in day1_assignments
    assert "AM_2" in day1_assignments
    assert "PM" in day1_assignments
    assert "PM_2" in day1_assignments
    assert len(day1_assignments) == 4


def test_max_one_shift_per_day_constraint(multi_team_config, simple_request):
    """
    Verify that a single person cannot work Team 1 and Team 2 on the same day.
    """
    # Force 'A' to work AM (Team 1)
    simple_request.fixed_assignments = {("A", 1): "AM"}

    engine = DutySchedulerEngine(multi_team_config, {}, simple_request)
    engine.build_model()
    result = engine.solve()

    assert result is not None
    schedule, _ = result

    # Ensure A does not have any other shift on Day 1
    # Specifically, they should NOT have AM_2 or PM_2
    for shift in ["AM_2", "PM", "PM_2", "S/B", "S/B_2"]:
        assert schedule.get(("A", 1)) != shift


def test_cross_team_transition_rules(multi_team_config, simple_request):
    """
    Verify that transition rules apply across teams based on base type.
    Scenario:
        - Rule: AM -> PM is HARD BAN.
        - Action: User works AM (Team 1) on Day 1.
        - Check: User CANNOT work PM (Team 2) on Day 2.
    """
    # Set Rule: AM -> PM = Hard Ban
    multi_team_config.rules.transitions["AM"]["PM"] = RuleStatus.HARD.value

    # Force A to work AM (Team 1) on Day 1
    simple_request.fixed_assignments = {("A", 1): "AM"}

    # Force A to work PM_2 (Team 2) on Day 2 -> This should fail
    simple_request.fixed_assignments[("A", 2)] = "PM_2"

    engine = DutySchedulerEngine(multi_team_config, {}, simple_request)
    engine.build_model()
    result = engine.solve()

    assert result is None, "Solver failed to enforce cross-team Hard Ban (AM -> PM_2)"


def test_standby_independence(multi_team_config, simple_request):
    """
    Verify that S/B and S/B_2 are treated as distinct requirements.
    """
    # 2 Standby Teams, 1 person per team needed.
    # Total 2 Standby staff needed per day.
    multi_team_config.constraints.num_active_teams = 0  # Disable active duties
    multi_team_config.constraints.num_standby_teams = 2
    multi_team_config.constraints.standby_per_day = 1

    multi_team_config.personnel = ["A", "B"]
    simple_request.staff_ids = ["A", "B"]

    engine = DutySchedulerEngine(multi_team_config, {}, simple_request)
    engine.build_model()
    result = engine.solve()

    assert result is not None
    schedule, _ = result

    day1_shifts = [schedule.get(("A", 1)), schedule.get(("B", 1))]
    assert "S/B" in day1_shifts
    assert "S/B_2" in day1_shifts
