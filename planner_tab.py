"""
planner_tab.py

Encapsulates the UI and logic for the 'Planner' tab.
Handles grid generation, user interaction (cell clicks), solver execution,
and exporting.
"""

import calendar
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk  # type: ignore
import holidays
import pandas as pd

import constants as C
import gui_helpers as GH
from config_models import AppConfig
from data_manager import DataManager
from scheduler_engine import DutySchedulerEngine, SolverRequest
from ui_components import ShiftGridCell


class PlannerTab(ctk.CTkFrame):
    """
    The Planner Tab Frame Controller.

    Attributes:
        config (AppConfig): Shared app configuration containing personnel and rules.
        prev_balance (Dict[str, float]): Points carried forward from imported files.
        last_loaded (Tuple[int, int]): (month, year) for the currently displayed grid.
        all_24h_active (bool): Toggle state for the global "Check All 24H" button.
        cells (Dict): Map of (person_name, day) -> ShiftGridCell widget.
        day_mode_vars (Dict): Map of day_index -> StringVar ("Shift"/"24H").
        day_active_vars (Dict): Map of day_index -> BooleanVar (Active/Inactive).
        stat_labels (Dict): Map of person_name -> Dict of UI Labels (BF, MP, CO).
    """

    def __init__(self, parent, config: AppConfig, on_update_callback=None):
        """
        Initializes the Planner Tab.

        Args:
            parent: The parent UI widget (usually the TabView).
            config: The shared AppConfig data object.
            on_update_callback: Optional function to call when data changes.
        """
        super().__init__(parent)
        self.config = config
        self.on_update = on_update_callback

        # State Tracking
        self.prev_balance = {}
        self.last_loaded = None
        self.all_24h_active = False

        # UI Component Storage
        self.cells = {}
        self.day_mode_vars = {}
        self.day_active_vars = {}
        self.stat_labels = {}

        self._build_ui()

    def _build_ui(self):
        """
        Constructs the main layout: Top Toolbar, Scrollable Grid, and Bottom Toolbar.
        Includes updated button labels and positions.
        """
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- 1. Top Control Bar ---
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # Date Selection (Month Dropdown)
        self.cmb_month = ctk.CTkComboBox(
            top, values=list(calendar.month_name)[1:], width=110
        )
        self.cmb_month.set(list(calendar.month_name)[self.config.month])
        self.cmb_month.pack(side="left", padx=5)

        # Date Selection (Year Entry)
        self.ent_year = ctk.CTkEntry(top, width=60)
        self.ent_year.insert(0, str(self.config.year))
        self.ent_year.pack(side="left", padx=5)

        # Primary Action: Load Grid
        GH.create_button(top, "Load Grid", self.refresh_grid, "left")

        # Toggle: Global 24H Mode
        self.btn_24 = GH.create_button(
            top, "Check All 24H", self.toggle_all_24h, "left", 120, "#7B1FA2"
        )

        # Right Side Actions (Reset, Clear, Import)
        GH.create_button(top, "Reset Table", self.reset_all, "right", 100, "#D32F2F")
        GH.create_button(
            top, "Clear Duties", self.clear_duties, "right", 110, "#EF5350"
        )
        GH.create_button(
            top, "Import Previous Month", self.import_balances, "right", 160
        )

        # --- 2. Main Grid Area ---
        cont = ctk.CTkFrame(self, fg_color="transparent")
        cont.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        self.scroll = ctk.CTkScrollableFrame(cont, orientation="horizontal")
        self.scroll.pack(fill="both", expand=True)

        # --- 3. Bottom Status Bar ---
        bot = ctk.CTkFrame(self, height=50, fg_color="transparent")
        bot.grid(row=2, column=0, sticky="ew", padx=5, pady=10)

        self.lbl_stat = ctk.CTkLabel(bot, text="Ready.", text_color="#555555")
        self.lbl_stat.pack(side="left", padx=10)

        # Action Buttons (Export, Generate)
        self.btn_exp = GH.create_button(
            bot, "Export xlsx", self.save_excel, "right", 120, "#2E7D32"
        )
        self.btn_exp.configure(state="disabled")  # Disabled until grid loaded

        self.btn_run = GH.create_button(
            bot, "GENERATE FILL", self.run_solver, "right", 140, "#1565C0"
        )

    def refresh_grid(self):
        """
        Rebuilds the visual grid based on the selected Month and Year.
        Calculates weekends, holidays, and renders rows for all personnel.
        """
        try:
            # Parse Date
            y = int(self.ent_year.get())
            m = list(calendar.month_name).index(self.cmb_month.get())
            if m == 0:
                m = 1

            # Optimization: Skip reload if nothing changed
            if self.last_loaded == (m, y):
                return

            days = pd.Period(f"{y}-{m}").days_in_month
            self.sg_holidays = holidays.SG(years=y)

            # Clean up old widgets
            for w in self.scroll.winfo_children():
                w.destroy()
            self.cells.clear()
            self.day_mode_vars.clear()
            self.day_active_vars.clear()
            self.stat_labels.clear()

            # 1. Build Header Rows
            headers = ["Date", "Day", "Duty?", "24H?", "NAME"]
            for i, t in enumerate(headers):
                GH.create_grid_header(
                    self.scroll, t, i, 0, width=(80 if i == 4 else 50)
                )

            # 2. Build Day Columns (1..31)
            for d in range(1, days + 1):
                dt = pd.Timestamp(year=y, month=m, day=d)
                is_ph = dt in self.sg_holidays
                is_wknd = dt.dayofweek >= 5

                # Visual Cues: Red for PH, Grey for Weekend
                bg = (
                    C.COLOR_PH_BG
                    if is_ph
                    else (C.COLOR_HEADER_BG if is_wknd else "transparent")
                )

                GH.create_grid_header(self.scroll, str(d), 0, d, bg)
                GH.create_grid_header(self.scroll, dt.strftime("%a"), 1, d, bg)

                # Row 2: Active Toggle ("Duty?")
                avar = ctk.BooleanVar(value=True)
                self.day_active_vars[d] = avar
                ctk.CTkCheckBox(
                    self.scroll,
                    text="",
                    variable=avar,
                    width=20,
                    command=lambda x=d: self.toggle_active(x),
                ).grid(row=2, column=d)

                # Row 3: 24H Toggle
                # Logic: Default to 24H only if it's a Public Holiday.
                # Weekends default to Shift.
                default_mode = (
                    C.ScheduleMode.FULL_24H.value
                    if is_ph
                    else C.ScheduleMode.SHIFT.value
                )
                mvar = ctk.StringVar(value=default_mode)
                self.day_mode_vars[d] = mvar
                ctk.CTkCheckBox(
                    self.scroll,
                    text="",
                    variable=mvar,
                    onvalue=C.ScheduleMode.FULL_24H.value,
                    offvalue=C.ScheduleMode.SHIFT.value,
                    width=20,
                ).grid(row=3, column=d)

            # 3. Build Stats Headers (Brought Fwd, etc)
            sc = days + 1  # Start column for stats
            for i, txt in enumerate(C.EXCEL_HEADERS_SUFFIX):
                GH.create_grid_header(self.scroll, txt, 4, sc + i + 1, width=80)

            # 4. Build Personnel Rows
            for idx, p in enumerate(sorted(self.config.personnel)):
                r = idx + 5
                ctk.CTkLabel(self.scroll, text=p).grid(
                    row=r, column=0, sticky="w", padx=5
                )

                # Create Cells
                for d in range(1, days + 1):
                    c = ShiftGridCell(self.scroll, p, d, self.on_click)
                    c.grid(row=r, column=d, padx=1, pady=1, sticky="nsew")
                    self.cells[(p, d)] = c

                # Create Stats Labels
                self.stat_labels[p] = {
                    "BF": ctk.CTkLabel(self.scroll, text="0.0"),
                    "MP": ctk.CTkLabel(self.scroll, text="0.0"),
                    "CO": ctk.CTkLabel(self.scroll, text="0.0"),
                }
                for i, k in enumerate(["BF", "MP", "CO"]):
                    self.stat_labels[p][k].grid(row=r, column=sc + i + 1)

            # Finalize
            self.recalculate()
            self.last_loaded = (m, y)
            self.current_days = days
            # UPDATED: Now includes Year
            self.lbl_stat.configure(text=f"Loaded {self.cmb_month.get()} {y}")
            self.btn_exp.configure(state="normal")

        except Exception as e:
            messagebox.showerror("Grid Error", str(e))

    def on_click(self, cell):
        """
        Handles clicks on a grid cell. Cycles the value (AM->PM->X)
        based on the column's mode (Shift vs 24H).

        Args:
            cell (ShiftGridCell): The cell object that was clicked.
        """
        mode = self.day_mode_vars[cell.day].get()
        cycle = ["", "X", "24H"] if mode == "24H" else ["", "X", "AM", "PM"]
        try:
            next_val = cycle[(cycle.index(cell.current_val) + 1) % len(cycle)]
        except Exception:
            next_val = ""
        cell.set_val(next_val)
        self.recalculate()

    def toggle_active(self, d):
        """
        Enables/Disables an entire day column.
        Disabled columns are excluded from logic and points.

        Args:
            d (int): The day index (1-31).
        """
        active = self.day_active_vars[d].get()
        for p in self.config.personnel:
            if (p, d) in self.cells:
                self.cells[(p, d)].set_disabled(not active)
        self.recalculate()

    def toggle_all_24h(self):
        """Bulk toggles all 24H checkboxes in the header row."""
        self.all_24h_active = not self.all_24h_active
        if self.all_24h_active:
            v = C.ScheduleMode.FULL_24H.value
        else:
            v = C.ScheduleMode.SHIFT.value

        for var in self.day_mode_vars.values():
            var.set(v)

    def recalculate(self):
        """
        Recalculates points for all personnel.
        Sums daily points * multipliers + brought forward balance.
        """
        try:
            y = int(self.ent_year.get())
            m = list(calendar.month_name).index(self.cmb_month.get())

            for p in self.config.personnel:
                bf = self.prev_balance.get(p, 0.0)
                cur = 0.0
                for d in range(1, self.current_days + 1):
                    # Skip disabled days
                    if not self.day_active_vars[d].get():
                        continue

                    if (p, d) in self.cells:
                        val = self.cells[(p, d)].current_val
                        if val in C.ACTIVE_DUTIES:
                            dt = pd.Timestamp(year=y, month=m, day=d)

                            # Multiplier Logic
                            mult = 1.0
                            if dt in self.sg_holidays:
                                mult = self.config.points.ph_multiplier
                            elif dt.dayofweek >= 5:
                                mult = self.config.points.weekend_multiplier

                            cur += self.config.points.get_by_type(val) * mult

                # Update Labels
                if p in self.stat_labels:
                    self.stat_labels[p]["BF"].configure(text=f"{bf:.1f}")
                    self.stat_labels[p]["MP"].configure(text=f"{cur:.1f}")
                    self.stat_labels[p]["CO"].configure(text=f"{bf + cur:.1f}")
        except Exception:
            pass

    def run_solver(self):
        """Gathers grid state and launches the Solver thread."""
        self.btn_run.configure(state="disabled")
        self.lbl_stat.configure(text="Solving...")

        # 1. Collect Manual Constraints
        fixed = {k: v.current_val for k, v in self.cells.items() if v.current_val}
        modes = {d: v.get() for d, v in self.day_mode_vars.items()}
        inactive = [d for d, v in self.day_active_vars.items() if not v.get()]

        y = int(self.ent_year.get())
        m = list(calendar.month_name).index(self.cmb_month.get())

        # 2. Package into DTO
        req = SolverRequest(self.config.personnel, y, m, fixed, modes, inactive)

        # 3. Start Thread
        threading.Thread(target=self._worker, args=(req,), daemon=True).start()

    def _worker(self, req):
        """Background thread logic for the engine."""
        try:
            eng = DutySchedulerEngine(self.config, self.prev_balance, req)
            eng.build_model()
            res = eng.solve()
            self.after(0, self._success, res)
        except Exception as e:
            # Fix: Assign to variable first to resolve scope/linting ambiguity
            err_msg = str(e)
            self.after(0, lambda: messagebox.showerror("Solver Error", err_msg))

    def _success(self, res):
        """Callback on solver success."""
        self.btn_run.configure(state="normal")
        if res:
            sched, _ = res
            # Fill Grid
            for (p, d), v in sched.items():
                if (p, d) in self.cells:
                    self.cells[(p, d)].set_val(v)
            self.recalculate()
            self.lbl_stat.configure(text="Done")
        else:
            self.lbl_stat.configure(text="Failed")
            messagebox.showwarning(
                "Solver", "No solution found. Check your constraints."
            )

    def save_excel(self):
        """Exports the current grid to .xlsx."""
        sched = {k: v.current_val for k, v in self.cells.items() if v.current_val}
        summ = []
        for p in self.config.personnel:
            if p in self.stat_labels:
                summ.append(
                    {
                        "Name": p,
                        "Brought Fwd": float(self.stat_labels[p]["BF"].cget("text")),
                        "Month Pts": float(self.stat_labels[p]["MP"].cget("text")),
                        "Carry Over": float(self.stat_labels[p]["CO"].cget("text")),
                    }
                )

        fp = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel Files", "*.xlsx")]
        )
        if fp:
            DataManager.export_schedule(sched, summ, self.config, fp)
            messagebox.showinfo("Export", "File saved successfully.")

    def reset_all(self):
        """Clears ALL cells in the grid."""
        if messagebox.askyesno("Confirm", "Reset entire table? All data will be lost."):
            for c in self.cells.values():
                c.set_val("")
            self.recalculate()

    def clear_duties(self):
        """Clears only duties (AM/PM/24H/SB) but preserves Leaves (X)."""
        if messagebox.askyesno(
            "Confirm", "Clear assigned duties? (Leaves will remain)"
        ):
            for c in self.cells.values():
                if c.current_val in C.ACTIVE_DUTIES:
                    c.set_val("")
            self.recalculate()

    def import_balances(self):
        """
        Imports 'Carry Over' balances from a previous month's Excel file.

        Feature:
        - Overwrites the current personnel list in settings with names from file.
        - Updates config.json immediately.
        """
        fp = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx")])
        if fp:
            self.prev_balance = DataManager.load_previous_balance(fp)
            imported_names = sorted(list(self.prev_balance.keys()))

            if not imported_names:
                messagebox.showwarning("Import", "No names found.")
                return

            msg = (
                f"Found {len(imported_names)} names in file.\n\n"
                "This will OVERWRITE the current personnel list.\n"
                "Proceed?"
            )

            if messagebox.askyesno("Overwrite?", msg):
                # 1. Update Config
                self.config.personnel = imported_names
                DataManager.save_config(self.config)

                # 2. Force Grid Refresh (Critical: clear last_loaded cache)
                self.last_loaded = None
                self.refresh_grid()

                # 3. Notify App to sync Settings Tab
                if self.on_update:
                    self.on_update()

            self.recalculate()
            messagebox.showinfo("Success", f"Imported {len(imported_names)} records.")
