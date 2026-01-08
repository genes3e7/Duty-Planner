"""
app/logic.py
"""
import io
import logging
import pandas as pd
import holidays
from typing import Dict, List, Optional, Tuple

from app import constants as C
from app.core.scheduler import DutySchedulerEngine, SolverRequest
from app.models.config import AppConfig

# Setup logger
logger = logging.getLogger(__name__)

def get_holidays(year: int) -> holidays.HolidayBase:
    return holidays.SG(years=year)

def generate_empty_schedule(year: int, month: int, personnel: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    try:
        num_days = pd.Period(f"{year}-{month}").days_in_month
    except ValueError:
        logger.warning(f"Invalid year/month ({year}/{month}), defaulting to 30 days")
        num_days = 30
        
    sg_holidays = get_holidays(year)
    
    day_data = []
    day_columns = [str(d) for d in range(1, num_days + 1)]
    
    for d in range(1, num_days + 1):
        dt = pd.Timestamp(year=year, month=month, day=d)
        is_ph = dt in sg_holidays
        mode = C.ScheduleMode.FULL_24H.value if is_ph else C.ScheduleMode.SHIFT.value
        
        day_data.append({
            "Day": d, 
            "Date": dt.strftime("%a %d"),
            "Active": True,
            "Mode": mode,
            "Is_PH": is_ph,
            "Is_Weekend": dt.dayofweek >= 5
        })
    
    df_days = pd.DataFrame(day_data)
    df_days.set_index("Day", inplace=True)

    df_roster = pd.DataFrame(index=personnel, columns=day_columns)
    df_roster[:] = ""
    
    return df_roster, df_days

def clear_schedule(df_roster: Optional[pd.DataFrame], clear_constraints: bool = False) -> Optional[pd.DataFrame]:
    """
    Clears the roster grid. Returns None if input is None.
    """
    if df_roster is None:
        return None
    
    df = df_roster.copy()
    
    if clear_constraints:
        df[:] = ""
    else:
        duties_to_remove = [
            C.ShiftType.AM.value,
            C.ShiftType.PM.value,
            C.ShiftType.FULL_24H.value,
            C.ShiftType.STANDBY.value
        ]
        for duty in duties_to_remove:
            mask = (df == duty)
            df[mask] = ""
            
    return df

# ... [prepare_solver_request, run_solver, calculate_stats, export_to_excel_bytes remain unchanged] ...
def prepare_solver_request(
    year: int, 
    month: int, 
    df_roster: pd.DataFrame, 
    df_days: pd.DataFrame, 
    config: AppConfig
) -> SolverRequest:
    fixed_assignments = {}
    day_modes = {}
    inactive_days = []

    for day_num, row in df_days.iterrows():
        if not row["Active"]:
            inactive_days.append(day_num)
        day_modes[day_num] = row["Mode"]

    for person in df_roster.index:
        for day_col in df_roster.columns:
            val = df_roster.at[person, day_col]
            if val:
                try:
                    day_idx = int(day_col)
                    fixed_assignments[(person, day_idx)] = val
                except ValueError:
                    continue

    return SolverRequest(
        staff_ids=config.personnel,
        year=year,
        month=month,
        fixed_assignments=fixed_assignments,
        day_modes=day_modes,
        inactive_days=inactive_days
    )

def run_solver(
    year: int,
    month: int,
    df_roster: pd.DataFrame,
    df_days: pd.DataFrame,
    config: AppConfig,
    prev_balance: Dict[str, float]
) -> Optional[Tuple[Dict, List]]:
    
    req = prepare_solver_request(year, month, df_roster, df_days, config)
    engine = DutySchedulerEngine(config, prev_balance, req)
    engine.build_model()
    return engine.solve()

def calculate_stats(df_roster: pd.DataFrame, df_days: pd.DataFrame, config: AppConfig, prev_balance: Dict) -> pd.DataFrame:
    summary = []
    
    for person in config.personnel:
        bf = prev_balance.get(person, 0.0)
        current_pts = 0.0
        
        if df_roster is not None and person in df_roster.index:
            for day_col in df_roster.columns:
                try:
                    day_idx = int(day_col)
                except ValueError:
                    continue 

                if day_idx not in df_days.index: continue
                if not df_days.loc[day_idx, "Active"]: continue

                val = df_roster.at[person, day_col]
                if val in C.ACTIVE_DUTIES:
                    is_ph = df_days.loc[day_idx, "Is_PH"]
                    is_weekend = df_days.loc[day_idx, "Is_Weekend"]
                    
                    base = config.points.get_by_type(val)
                    
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

        summary.append({
            "Name": person,
            "Brought Fwd": bf,
            "Month Pts": current_pts,
            "Carry Over": bf + current_pts
        })
    return pd.DataFrame(summary)

def export_to_excel_bytes(df_roster: pd.DataFrame, df_stats: pd.DataFrame, config: AppConfig) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Side, PatternFill, Font

    output = io.BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = C.EXCEL_SHEET_TITLE

    days = list(df_roster.columns)
    ws.append(C.EXCEL_HEADERS_STATIC + days + C.EXCEL_HEADERS_SUFFIX)

    stats_map = df_stats.set_index("Name").to_dict("index")

    for person in sorted(config.personnel):
        row = [person]
        for d in days:
            val = df_roster.at[person, d] if person in df_roster.index else ""
            row.append(val)
        
        s = stats_map.get(person, {"Brought Fwd":0, "Month Pts":0, "Carry Over":0})
        row.extend([s["Brought Fwd"], s["Month Pts"], s["Carry Over"]])
        ws.append(row)

    fill_header = PatternFill("solid", fgColor=C.COLOR_HEADER_BG.replace("#", ""))
    fill_x = PatternFill("solid", fgColor=C.COLOR_CONSTRAINT_BG.replace("#", ""))
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

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
