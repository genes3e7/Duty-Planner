"""
gui.py v7.0
Features:
- New "Duty?" Toggle Row to disable specific days.
- Dynamic column disabling/clearing.
- Robust state management for inactive days.
"""

import calendar
import datetime
import threading
import logging
import sys
from typing import Dict, List, Tuple, Any, Optional
from tkinter import filedialog, messagebox

import customtkinter as ctk # type: ignore
import pandas as pd
import holidays

from data_manager import DataManager
from scheduler_engine import DutySchedulerEngine
import constants as C
import logger

logger.setup_logger()
ctk.set_appearance_mode(C.THEME_MODE)
ctk.set_default_color_theme(C.THEME_COLOR)

class ShiftGridCell(ctk.CTkButton):
    def __init__(self, master, person: str, day: int, parent_app):
        super().__init__(
            master, 
            text="", 
            width=42, 
            height=30, 
            corner_radius=4, 
            border_width=1, 
            border_color="#D0D0D0", 
            fg_color=C.COLOR_CELL_DEFAULT,
            text_color=C.COLOR_TEXT_BLACK,
            hover_color="#E0E0E0", 
            command=self._on_click
        )
        self.person = person
        self.day = day
        self.app = parent_app
        self.current_val = "" 
        self._is_disabled = False

    def _on_click(self) -> None:
        if self._is_disabled: return # Defensive check
        
        mode = self.app.get_day_mode(self.day)
        if mode == "24H":
            cycle = ["", "X", "24H"]
        else:
            cycle = ["", "X", "AM", "PM"]
        try:
            idx = cycle.index(self.current_val)
            next_val = cycle[(idx + 1) % len(cycle)]
        except ValueError:
            next_val = ""
        self.set_val(next_val)

    def set_val(self, val: str) -> None:
        if self._is_disabled and val != "": return # Prevent setting values if disabled
        
        self.current_val = val
        bg = C.COLOR_CELL_DEFAULT
        txt = C.COLOR_TEXT_BLACK
        
        if val == "X": bg, txt = C.COLOR_CELL_X, C.COLOR_TEXT_WHITE
        elif val == "AM": bg, txt = C.COLOR_CELL_AM, C.COLOR_TEXT_WHITE
        elif val == "PM": bg, txt = C.COLOR_CELL_PM, C.COLOR_TEXT_WHITE
        elif val == "24H": bg, txt = C.COLOR_CELL_24H, C.COLOR_TEXT_WHITE
        elif val == "S/B": bg, txt = C.COLOR_CELL_PH, C.COLOR_TEXT_BLACK
        
        self.configure(text=val, fg_color=bg, text_color=txt, state="normal")
        self.configure(hover_color="#E0E0E0" if val == "" else bg)
        self.app.recalculate_points()

    def set_disabled(self, disabled: bool):
        self._is_disabled = disabled
        if disabled:
            self.set_val("") # Clear value defensively
            self.configure(state="disabled", fg_color="#E0E0E0", text="") # Grey out
        else:
            self.configure(state="normal", fg_color=C.COLOR_CELL_DEFAULT)

class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(C.APP_TITLE)
        self.geometry(C.APP_GEOMETRY)
        self.after(0, lambda: self.state('zoomed') if "win" in sys.platform else self.attributes('-zoomed', True))
        
        self.config = DataManager.load_config()
        self.prev_balance: Dict[str, float] = {}
        self.last_loaded_date: Optional[Tuple[int, int]] = None
        self.all_24h_active = False
        
        self.cells: Dict[Tuple[str, int], ShiftGridCell] = {}
        self.day_mode_vars: Dict[int, ctk.StringVar] = {} 
        self.day_active_vars: Dict[int, ctk.BooleanVar] = {} # New: Track active days
        self.stat_labels: Dict[str, Dict[str, ctk.CTkLabel]] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        
        self.tab_plan = self.tabview.add("Planner")
        self.tab_settings = self.tabview.add("Settings")
        
        self._init_planner_tab()
        self._init_settings_tab()

    def _init_planner_tab(self) -> None:
        self.tab_plan.grid_columnconfigure(0, weight=1)
        self.tab_plan.grid_rowconfigure(1, weight=1)
        self._setup_top_bar(self.tab_plan)
        
        self.grid_container = ctk.CTkFrame(self.tab_plan, fg_color="transparent")
        self.grid_container.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        self.scroll_frame = ctk.CTkScrollableFrame(self.grid_container, orientation="horizontal")
        self.scroll_frame.pack(fill="both", expand=True)
        
        self._setup_bottom_bar(self.tab_plan)

    def _init_settings_tab(self) -> None:
        frame = ctk.CTkScrollableFrame(self.tab_settings)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text="Configuration", font=("Arial", 20, "bold")).pack(pady=10)
        
        # Requirements
        ctk.CTkLabel(frame, text="Daily Manpower Requirements", font=("Arial", 14, "bold")).pack(anchor="w", pady=(10, 5))
        self.entries_reqs: Dict[str, ctk.CTkEntry] = {}
        
        f1 = ctk.CTkFrame(frame)
        f1.pack(fill="x", pady=2)
        ctk.CTkLabel(f1, text="AM Shift:", width=80).pack(side="left")
        e1 = ctk.CTkEntry(f1, width=50)
        e1.insert(0, str(self.config['constraints']['personnel_needed_per_shift'].get('AM', 1)))
        e1.pack(side="left")
        self.entries_reqs['AM'] = e1
        
        ctk.CTkLabel(f1, text="PM Shift:", width=80).pack(side="left", padx=20)
        e2 = ctk.CTkEntry(f1, width=50)
        e2.insert(0, str(self.config['constraints']['personnel_needed_per_shift'].get('PM', 1)))
        e2.pack(side="left")
        self.entries_reqs['PM'] = e2

        f2 = ctk.CTkFrame(frame)
        f2.pack(fill="x", pady=2)
        ctk.CTkLabel(f2, text="24H Duty:", width=80).pack(side="left")
        e3 = ctk.CTkEntry(f2, width=50)
        e3.insert(0, str(self.config['constraints']['personnel_needed_per_shift'].get('24H', 1)))
        e3.pack(side="left")
        self.entries_reqs['24H'] = e3

        ctk.CTkLabel(f2, text="Standby:", width=80).pack(side="left", padx=20)
        e4 = ctk.CTkEntry(f2, width=50)
        e4.insert(0, str(self.config['constraints'].get('standby_per_day', 1)))
        e4.pack(side="left")
        self.entries_reqs['SB'] = e4

        # Points
        ctk.CTkLabel(frame, text="Points Scoring", font=("Arial", 14, "bold")).pack(anchor="w", pady=(20, 5))
        self.entries_pts: Dict[str, ctk.CTkEntry] = {}
        keys = ["AM", "PM", "24H", "S/B", "weekend_multiplier", "ph_multiplier"]
        for k in keys:
            val = self.config.get("points", {}).get(k, 1.0)
            sub = ctk.CTkFrame(frame)
            sub.pack(fill="x", pady=2)
            lbl = k.replace("_", " ").title() + (" (x)" if "multiplier" in k else " (pts)")
            ctk.CTkLabel(sub, text=lbl, width=180, anchor="w").pack(side="left", padx=5)
            e = ctk.CTkEntry(sub)
            e.insert(0, str(val))
            e.pack(side="right", expand=True, fill="x", padx=5)
            self.entries_pts[k] = e

        # Personnel
        ctk.CTkLabel(frame, text="Personnel List", font=("Arial", 14, "bold")).pack(anchor="w", pady=(20,5))
        self.entry_ppl = ctk.CTkTextbox(frame, height=120)
        ppl_str = ", ".join(self.config.get("personnel", []))
        self.entry_ppl.insert("0.0", ppl_str)
        self.entry_ppl.pack(fill="x", pady=5)
        
        self.combo_mode = ctk.CTkComboBox(frame, values=C.SCHEDULING_MODES)
        self.combo_mode.set(str(self.config.get("mode", "hybrid")))

        ctk.CTkButton(frame, text="Save & Reload", fg_color="green", height=40, command=self.save_settings).pack(pady=30)

    def _setup_top_bar(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        self.cmb_month = ctk.CTkComboBox(frame, values=list(calendar.month_name)[1:], width=110)
        curr_m = self.config.get('month', datetime.datetime.now().month)
        try: self.cmb_month.set(list(calendar.month_name)[curr_m]) 
        except: self.cmb_month.set("January")
        self.cmb_month.pack(side="left", padx=5)

        self.ent_year = ctk.CTkEntry(frame, width=60)
        self.ent_year.insert(0, str(self.config.get('year', datetime.datetime.now().year)))
        self.ent_year.pack(side="left", padx=5)

        ctk.CTkButton(frame, text="Load Grid", command=self.refresh_grid).pack(side="left", padx=10)
        self.btn_toggle_24 = ctk.CTkButton(frame, text="Check All 24H", width=100, fg_color="#7B1FA2", hover_color="#4A148C", command=self.toggle_all_24h)
        self.btn_toggle_24.pack(side="left", padx=10)

        ctk.CTkButton(frame, text="Import Balances", width=110, command=self.import_balances).pack(side="right", padx=5)
        ctk.CTkButton(frame, text="Clear Duties", fg_color="#EF5350", hover_color="#C62828", width=90, command=self.clear_duties).pack(side="right", padx=5)
        ctk.CTkButton(frame, text="Reset All", fg_color="#D32F2F", hover_color="#B71C1C", width=80, command=self.reset_all).pack(side="right", padx=5)

    def _setup_bottom_bar(self, parent):
        frame = ctk.CTkFrame(parent, height=50, fg_color="transparent")
        frame.grid(row=2, column=0, sticky="ew", padx=5, pady=10)
        self.lbl_status = ctk.CTkLabel(frame, text="Ready.", text_color="#555555")
        self.lbl_status.pack(side="left", padx=10)
        self.btn_save = ctk.CTkButton(frame, text="Export Excel", state="disabled", fg_color="#2E7D32", hover_color="#1B5E20", command=self.save_excel_safely)
        self.btn_save.pack(side="right", padx=10)
        self.btn_run = ctk.CTkButton(frame, text="GENERATE FILL", font=("Arial", 13, "bold"), fg_color="#1565C0", hover_color="#0D47A1", command=self.run_solver)
        self.btn_run.pack(side="right", padx=10)

    # --- Actions ---
    def goto_settings(self): self.tabview.set("Settings")

    def save_settings(self):
        saved_duties = {k: v.current_val for k, v in self.cells.items() if v.current_val}
        saved_modes = {d: v.get() for d, v in self.day_mode_vars.items()}
        try:
            am = int(self.entries_reqs['AM'].get())
            pm = int(self.entries_reqs['PM'].get())
            h24 = int(self.entries_reqs['24H'].get())
            sb = int(self.entries_reqs['SB'].get())
            if am < 0 or pm < 0 or h24 < 0: raise ValueError("Requirements cannot be negative.")

            self.config['constraints']['personnel_needed_per_shift'] = {'AM': am, 'PM': pm, '24H': h24}
            self.config['constraints']['standby_per_day'] = sb

            for k, e in self.entries_pts.items():
                self.config['points'][k] = float(e.get())

            raw = self.entry_ppl.get("0.0", "end").replace("\n", ",")
            ppl_clean = [x.strip() for x in raw.split(",") if x.strip()]
            if not ppl_clean: raise ValueError("Personnel list empty.")
            self.config['personnel'] = ppl_clean
            
            DataManager.save_config(self.config)
            self.config = DataManager.load_config()
            self.last_loaded_date = None
            self.refresh_grid()
            
            for d, mode in saved_modes.items():
                if d in self.day_mode_vars: self.day_mode_vars[d].set(mode)
            for (p, d), val in saved_duties.items():
                if (p, d) in self.cells: self.cells[(p, d)].set_val(val)

            messagebox.showinfo("Success", "Settings Saved.")
            self.tabview.set("Planner")
        except Exception as e:
            messagebox.showerror("Error", f"Save Failed: {str(e)}")

    def toggle_all_24h(self):
        new_state = "24H" if not self.all_24h_active else "Shift"
        for var in self.day_mode_vars.values(): var.set(new_state)
        self.all_24h_active = not self.all_24h_active
        self.btn_toggle_24.configure(text="Uncheck All" if self.all_24h_active else "Check All 24H")

    def toggle_day_active(self, day: int):
        """Callback for 'Duty?' toggle. Disables/Enables columns."""
        is_active = self.day_active_vars[day].get()
        
        # Iterate through all personnel for this day
        for p in self.config.get('personnel', []):
            if (p, day) in self.cells:
                self.cells[(p, day)].set_disabled(not is_active)
        
        self.recalculate_points()

    def clear_duties(self):
        if not messagebox.askyesno("Confirm", "Clear duties?"): return
        for cell in self.cells.values():
            if cell.current_val in ["AM", "PM", "24H", "S/B"]: cell.set_val("")
        self.recalculate_points()

    def reset_all(self):
        if not messagebox.askyesno("Confirm", "Reset all?"): return
        for cell in self.cells.values(): cell.set_val("")
        self.recalculate_points()

    def get_day_mode(self, day: int) -> str:
        return self.day_mode_vars.get(day, ctk.StringVar(value="Shift")).get()

    def refresh_grid(self):
        try:
            year = int(self.ent_year.get())
            month_idx = list(calendar.month_name).index(self.cmb_month.get())
            if month_idx == 0: month_idx = 1
            if self.last_loaded_date == (month_idx, year):
                self.lbl_status.configure(text=f"Loaded {self.cmb_month.get()}")
                return
            self.current_days = pd.Period(f'{year}-{month_idx}').days_in_month
            personnel = self.config.get('personnel', [])
            self.sg_holidays = holidays.SG(years=year)
            if not personnel:
                messagebox.showerror("Config", "No personnel.")
                return
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        for widget in self.scroll_frame.winfo_children(): widget.destroy()
        self.cells.clear()
        self.day_mode_vars.clear()
        self.day_active_vars.clear()
        self.stat_labels.clear()
        self.all_24h_active = False
        self.btn_toggle_24.configure(text="Check All 24H")

        try:
            # Row 0: Date
            ctk.CTkLabel(self.scroll_frame, text="Date", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, sticky="w")
            # Row 1: Day
            ctk.CTkLabel(self.scroll_frame, text="Day", font=("Arial", 10, "bold")).grid(row=1, column=0, padx=5, sticky="w")
            # Row 2: Duty Active? (New)
            ctk.CTkLabel(self.scroll_frame, text="Duty?", font=("Arial", 10, "bold")).grid(row=2, column=0, padx=5, sticky="w")
            # Row 3: 24H Toggle
            ctk.CTkLabel(self.scroll_frame, text="24H?", font=("Arial", 10, "bold")).grid(row=3, column=0, padx=5, sticky="w")
            # Row 4: Name Header
            ctk.CTkLabel(self.scroll_frame, text="NAME", font=("Arial", 12, "bold")).grid(row=4, column=0, padx=5, sticky="w")

            for d in range(1, self.current_days + 1):
                dt = pd.Timestamp(year=year, month=month_idx, day=d)
                is_ph = dt in self.sg_holidays
                is_wknd = dt.dayofweek >= 5
                bg = C.COLOR_PH_BG if is_ph else (C.COLOR_HEADER_BG if is_wknd else "transparent")
                
                # Headers
                ctk.CTkLabel(self.scroll_frame, text=str(d), width=40, fg_color=bg).grid(row=0, column=d, padx=1, sticky="nsew")
                ctk.CTkLabel(self.scroll_frame, text=dt.strftime("%a"), width=40, fg_color=bg).grid(row=1, column=d, padx=1, sticky="nsew")
                
                # Active Checkbox (Row 2)
                active_var = ctk.BooleanVar(value=True)
                self.day_active_vars[d] = active_var
                ctk.CTkCheckBox(self.scroll_frame, text="", variable=active_var, width=20, 
                                command=lambda day=d: self.toggle_day_active(day)).grid(row=2, column=d)

                # 24H Checkbox (Row 3)
                val = "24H" if (is_wknd or is_ph) else "Shift"
                var = ctk.StringVar(value=val)
                self.day_mode_vars[d] = var
                ctk.CTkCheckBox(self.scroll_frame, text="", variable=var, onvalue="24H", offvalue="Shift", width=20).grid(row=3, column=d)

            # Stats Headers (Row 4, shifted right)
            start_col = self.current_days + 1
            ctk.CTkLabel(self.scroll_frame, text="Brought Fwd", font=("Arial", 10, "bold")).grid(row=4, column=start_col+1, padx=5)
            ctk.CTkLabel(self.scroll_frame, text="Month Pts", font=("Arial", 10, "bold")).grid(row=4, column=start_col+2, padx=5)
            ctk.CTkLabel(self.scroll_frame, text="Carry Over", font=("Arial", 10, "bold")).grid(row=4, column=start_col+3, padx=5)

            # Personnel Rows
            for idx, person in enumerate(personnel):
                r = idx + 5 # Start from row 5
                ctk.CTkLabel(self.scroll_frame, text=person).grid(row=r, column=0, sticky="w", padx=5)
                for d in range(1, self.current_days + 1):
                    cell = ShiftGridCell(self.scroll_frame, person, d, self)
                    cell.grid(row=r, column=d, padx=1, pady=1, sticky="nsew")
                    self.cells[(person, d)] = cell
                
                self.stat_labels[person] = {
                    "BF": ctk.CTkLabel(self.scroll_frame, text="0.0"),
                    "MP": ctk.CTkLabel(self.scroll_frame, text="0.0"),
                    "CO": ctk.CTkLabel(self.scroll_frame, text="0.0")
                }
                self.stat_labels[person]["BF"].grid(row=r, column=start_col+1, padx=5)
                self.stat_labels[person]["MP"].grid(row=r, column=start_col+2, padx=5)
                self.stat_labels[person]["CO"].grid(row=r, column=start_col+3, padx=5)

            self.scroll_frame.update_idletasks()
            self.recalculate_points()
            self.last_loaded_date = (month_idx, year)
            self.lbl_status.configure(text=f"Loaded {self.cmb_month.get()}")
            self.btn_save.configure(state="normal")
        except Exception as e:
            messagebox.showerror("Render Error", str(e))

    def recalculate_points(self):
        try:
            year = int(self.ent_year.get())
            month_idx = list(calendar.month_name).index(self.cmb_month.get())
            if month_idx == 0: month_idx = 1
            points = self.config.get('points', {})
            for p in self.config.get('personnel', []):
                bf = self.prev_balance.get(p, 0.0)
                cur = 0.0
                for d in range(1, self.current_days + 1):
                    # Defensive: check if day is active
                    if not self.day_active_vars.get(d, ctk.BooleanVar(value=True)).get():
                        continue

                    if (p, d) in self.cells:
                        val = self.cells[(p, d)].current_val
                        if val in C.SHIFT_TYPES:
                            dt = pd.Timestamp(year=year, month=month_idx, day=d)
                            mult = 1.0
                            if dt in self.sg_holidays: mult = points.get('ph_multiplier', 1.0)
                            elif dt.dayofweek >= 5: mult = points.get('weekend_multiplier', 1.0)
                            cur += (points.get(val, 0) * mult)
                if p in self.stat_labels:
                    self.stat_labels[p]["BF"].configure(text=f"{bf:.1f}")
                    self.stat_labels[p]["MP"].configure(text=f"{cur:.1f}")
                    self.stat_labels[p]["CO"].configure(text=f"{bf+cur:.1f}")
        except: pass

    def validate_schedule(self):
        errors = []
        for p in self.config.get('personnel', []):
            for d in range(1, self.current_days):
                # Ignore if either day is disabled
                if not self.day_active_vars[d].get() or not self.day_active_vars[d+1].get():
                    continue

                if (p, d) in self.cells and (p, d+1) in self.cells:
                    c1 = self.cells[(p, d)].current_val
                    c2 = self.cells[(p, d+1)].current_val
                    if c1 in C.SHIFT_TYPES and c2 in C.SHIFT_TYPES:
                        errors.append(f"{p}: Consecutive duty Day {d}")
        return errors

    def run_solver(self):
        self.btn_run.configure(state="disabled")
        self.lbl_status.configure(text="Solving...", text_color="blue")
        fixed = {k: v.current_val for k, v in self.cells.items() if v.current_val}
        modes = {d: v.get() for d, v in self.day_mode_vars.items()}
        
        # Gather inactive days
        inactive = [d for d, var in self.day_active_vars.items() if not var.get()]
        
        self.config['year'] = int(self.ent_year.get())
        self.config['month'] = list(calendar.month_name).index(self.cmb_month.get())
        threading.Thread(target=self._worker, args=(fixed, modes, inactive), daemon=True).start()

    def _worker(self, fixed, modes, inactive):
        try:
            # Pass inactive days to engine
            engine = DutySchedulerEngine(self.config, self.prev_balance, [], modes, fixed, inactive_days=inactive)
            engine.build_model()
            res = engine.solve()
            self.after(0, self._on_success, res)
        except Exception as e:
            self.after(0, self._on_error, str(e))

    def _on_success(self, res):
        self.btn_run.configure(state="normal")
        if res:
            sched, _ = res
            for (p, d), val in sched.items():
                if (p, d) in self.cells: self.cells[(p, d)].set_val(val)
            self.recalculate_points()
            self.lbl_status.configure(text="Filled!", text_color="green")
        else:
            self.lbl_status.configure(text="Failed.", text_color="red")
            messagebox.showwarning("Solver", "No solution found.")

    def _on_error(self, msg):
        self.btn_run.configure(state="normal")
        messagebox.showerror("Error", msg)

    def save_excel_safely(self):
        errs = self.validate_schedule()
        if errs and not messagebox.askyesno("Warning", "Issues found:\n" + "\n".join(errs[:3])): return
        sched = {k: v.current_val for k, v in self.cells.items() if v.current_val}
        summ = []
        for p in self.config['personnel']:
            if p in self.stat_labels:
                summ.append({'Name': p, 'Brought Fwd': float(self.stat_labels[p]["BF"].cget("text")),
                    'Month Pts': float(self.stat_labels[p]["MP"].cget("text")),
                    'Carry Over': float(self.stat_labels[p]["CO"].cget("text"))})
        fp = filedialog.asksaveasfilename(defaultextension=".xlsx")
        if fp:
            try:
                DataManager.export_schedule(sched, summ, self.config, [], fp)
                messagebox.showinfo("Success", "Saved")
            except Exception as e: messagebox.showerror("Error", str(e))

    def import_balances(self):
        fp = filedialog.askopenfilename()
        if fp:
            try:
                self.prev_balance = DataManager.load_previous_balance(fp)
                
                imported_names = list(self.prev_balance.keys())
                current_names = set(self.config.get('personnel', []))
                new_names = [n for n in imported_names if n not in current_names]
                
                if new_names:
                    msg = f"Found {len(new_names)} new names in file:\n{', '.join(new_names[:5])}...\n\nAdd them to configuration?"
                    if messagebox.askyesno("Update Personnel", msg):
                        self.config['personnel'].extend(new_names)
                        self.config['personnel'].sort() 
                        DataManager.save_config(self.config)
                        self.refresh_grid()
                        
                self.recalculate_points() 
                messagebox.showinfo("Success", f"Loaded balances for {len(self.prev_balance)} people")
            except Exception as e: messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    app = App()
    app.mainloop()
