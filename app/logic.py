"""
app/logic.py

This module serves as the 'Controller' in the MVC pattern.
It bridges the Gap between the Streamlit UI (View) and the Data/Scheduler (Model).
It handles data transformation, safe parsing, and orchestrating the solving process.
"""

import io
import logging
from typing import Dict, List, Optional, Tuple

import holidays
import pandas as pd
from openpyxl.styles import Border, Side  # Import specific classes for Border definition

from app import constants as C
from app.core.scheduler import DutySchedulerEngine, SolverRequest
from app.models.config import AppConfig

# Setup logger for this module
logger = logging.getLogger(__name__)


def get_day_num(col_name: str) -> int:
    """
    Safely extracts the day integer from a column string.

    Args:
        col_name (str): The column name (e.g., "D1", "D25").

    Returns:
        int: The day number (1-31), or 0 if parsing fails.
    """
    try:
        # Remove 'D' prefix and convert to int
        return int(str(col_name).replace("D", ""))
    except ValueError:
        return 0


def get_holidays(year: int) -> holidays.HolidayBase:
    """
    Returns the holiday object for Singapore for the given year.

    Args:
        year (int): The year to fetch holidays for.

    Returns:
        holidays.HolidayBase: Object containing holiday dates.
    """
    return holidays.SG(years=year)


def generate_empty_schedule(year: int, month: int, personnel: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Creates the initial empty DataFrames for the Roster and Day Configuration.

    Args:
        year (int): Year for the schedule.
        month (int): Month for the schedule.
        personnel (List[str]): List of staff names for row indices.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]:
            - df_roster: Grid with names as index and "D1"..."DN" as columns.
            - df_days: Configuration for each day (Is_PH, Mode, Active).
    """
    try:
        num_days = pd.Period(f"{year}-{month}").days_in_month
    except ValueError:
        logger.warning(f"Invalid year/month ({year}/{month}), defaulting to 30 days")
        num_days = 30

    sg_holidays = get_holidays(year)

    day_data = []
    # We use "D" prefix to enforce String type columns in Streamlit/Pandas
    day_columns = [f"D{d}" for d in range(1, num_days + 1)]

    for d in range(1, num_days + 1):
        dt = pd.Timestamp(year=year, month=month, day=d)
        is_ph = dt in sg_holidays
        # Default mode: 24H for holidays, Shift for normal days
        mode = C.ScheduleMode.FULL_24H.value if is_ph else C.ScheduleMode.SHIFT.value

        day_data.append(
            {
                "Day": d,
                "Date": dt.strftime("%a %d"),
                "Active": True,
                "Mode": mode,
                "Is_PH": is_ph,
                "Is_Weekend": dt.dayofweek >= 5,
            }
        )

    df_days = pd.DataFrame(day_data)
    df_days.set_index("Day", inplace=True)

    df_roster = pd.DataFrame(index=personnel, columns=day_columns)
    df_roster[:] = ""

    return df_roster, df_days


def clear_schedule(df_roster: Optional[pd.DataFrame], clear_constraints: bool = False) -> Optional[pd.DataFrame]:
    """
    Clears data from the roster grid.

    Args:
        df_roster (pd.DataFrame): The current roster dataframe.
        clear_constraints (bool):
            - If True: Wipes EVERYTHING (including 'X').
            - If False: Wipes only duties (AM, PM, 24H), keeping 'X'.

    Returns:
        pd.DataFrame: The modified dataframe (or None if input was None).
    """
    if df_roster is None:
        return None

    df = df_roster.copy()

    if clear_constraints:
        df[:] = ""
    else:
        # List of specific duties to remove
        duties_to_remove = [
            C.ShiftType.AM.value,
            C.ShiftType.PM.value,
            C.ShiftType.FULL_24H.value,
            C.ShiftType.STANDBY.value,
        ]
        # Boolean masking is safer than replace() for mixed types
        for duty in duties_to_remove:
            mask = df == duty
            df[mask] = ""

    return df


def prepare_solver_request(
    year: int, month: int, df_roster: pd.DataFrame, df_days: pd.DataFrame, config: AppConfig
) -> SolverRequest:
    """
    Transforms the UI DataFrames into a clean SolverRequest object.
    Parsing involves converting string columns ("D1") back to integers (1).
    """
    fixed_assignments = {}
    day_modes = {}
    inactive_days = []

    # Parse Day Configuration
    for day_num, row in df_days.iterrows():
        if not row["Active"]:
            inactive_days.append(day_num)
        day_modes[day_num] = row["Mode"]

    # Parse Roster Grid (Fixed Constraints)
    for person in df_roster.index:
        for day_col in df_roster.columns:
            val = df_roster.at[person, day_col]
            if val:
                # Convert "D1" -> 1
                try:
                    day_idx = get_day_num(day_col)
                    if day_idx > 0:
                        fixed_assignments[(person, day_idx)] = val
                except ValueError:
                    continue

    return SolverRequest(
        staff_ids=config.personnel,
        year=year,
        month=month,
        fixed_assignments=fixed_assignments,
        day_modes=day_modes,
        inactive_days=inactive_days,
    )


def run_solver(
    year: int,
    month: int,
    df_roster: pd.DataFrame,
    df_days: pd.DataFrame,
    config: AppConfig,
    prev_balance: Dict[str, float],
) -> Optional[Tuple[Dict, List]]:
    """
    Orchestrates the solving process:
    1. Prepares the request.
    2. Initializes the engine.
    3. Runs the solver.
    """
    req = prepare_solver_request(year, month, df_roster, df_days, config)
    engine = DutySchedulerEngine(config, prev_balance, req)
    engine.build_model()
    return engine.solve()


def calculate_stats(
    df_roster: pd.DataFrame, df_days: pd.DataFrame, config: AppConfig, prev_balance: Dict
) -> pd.DataFrame:
    """
    Calculates point statistics for the current roster state.
    Handles logic for multipliers vs additions for PH/Weekends.
    """
    summary = []

    for person in config.personnel:
        bf = prev_balance.get(person, 0.0)
        current_pts = 0.0

        if df_roster is not None and person in df_roster.index:
            for day_col in df_roster.columns:
                try:
                    day_idx = get_day_num(day_col)
                except ValueError:
                    continue
                if day_idx <= 0:
                    continue

                # Skip if day not in config or inactive
                if day_idx not in df_days.index:
                    continue
                if not df_days.loc[day_idx, "Active"]:
                    continue

                val = df_roster.at[person, day_col]
                if val in C.ACTIVE_DUTIES:
                    is_ph = df_days.loc[day_idx, "Is_PH"]
                    is_weekend = df_days.loc[day_idx, "Is_Weekend"]

                    base = config.points.get_by_type(val)

                    # Logic: Apply PH rule first, else apply Weekend rule
                    if is_ph:
                        if config.points.ph_is_multiplier:
                            base = base * config.points.ph_multiplier
                        else:
                            base = base + config.points.ph_multiplier
                    elif is_weekend:
                        if config.points.weekend_is_multiplier:
                            base = base * config.points.weekend_multiplier
                        else:
                            base = base + config.points.weekend_multiplier

                    current_pts += base

        summary.append({"Name": person, "Brought Fwd": bf, "Month Pts": current_pts, "Carry Over": bf + current_pts})
    return pd.DataFrame(summary)


def export_to_excel_bytes(df_roster: pd.DataFrame, df_stats: pd.DataFrame, config: AppConfig) -> bytes:
    """Generates a downloadable Excel file from the DataFrames."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    output = io.BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = C.EXCEL_SHEET_TITLE

    # Convert "D1", "D2" -> 1, 2 for the Header row
    header_days = [get_day_num(c) for c in df_roster.columns]

    ws.append(C.EXCEL_HEADERS_STATIC + header_days + C.EXCEL_HEADERS_SUFFIX)

    stats_map = df_stats.set_index("Name").to_dict("index")

    for person in sorted(config.personnel):
        row = [person]
        for d_col in df_roster.columns:
            val = df_roster.at[person, d_col] if person in df_roster.index else ""
            row.append(val)

        s = stats_map.get(person, {"Brought Fwd": 0, "Month Pts": 0, "Carry Over": 0})
        row.extend([s["Brought Fwd"], s["Month Pts"], s["Carry Over"]])
        ws.append(row)

    # Styles
    fill_header = PatternFill("solid", fgColor=C.COLOR_HEADER_BG.replace("#", ""))
    fill_x = PatternFill("solid", fgColor=C.COLOR_CONSTRAINT_BG.replace("#", ""))

    # Fix: Define reuseable Side to keep line length under 120 chars
    thin_side = Side(style="thin")
    thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
        for cell in row:
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center")
            if cell.row == 1:
                cell.fill = fill_header
                cell.font = Font(bold=True)
            if cell.value == "X":
                cell.fill = fill_x

    wb.save(output)
    return output.getvalue()
