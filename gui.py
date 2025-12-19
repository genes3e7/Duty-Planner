"""
gui.py

The Main Entry Point.
Uses CustomTkinter for the GUI, Threading for responsiveness,
and the Logic Engine for calculations.
"""

import calendar
import datetime
import logging
import threading
from tkinter import filedialog, messagebox
from typing import Dict, List, Tuple, Optional, Any, Union

import customtkinter as ctk  # type: ignore
import pandas as pd

from data_manager import DataManager
from scheduler_engine import DutySchedulerEngine
import constants as C
import logger

# Init Logger
logger.setup_logger()

# Theme Setup
ctk.set_appearance_mode(C.THEME_MODE)
ctk.set_default_color_theme(C.THEME_COLOR)


class App(ctk.CTk):
    """Main Application Window."""

    def __init__(self) -> None:
        super().__init__()
        self.title(C.APP_TITLE)
        self.geometry(C.APP_GEOMETRY)

        logging.info("Initializing GUI...")

        # --- Application State ---
        self.config: Dict[str, Any] = DataManager.load_config()
        self.prev_balance: Dict[str, float] = {}
        self.leaves: List[Tuple[str, int]] = []
        self.generated_schedule: Optional[Dict[Tuple[str, int], str]] = None
        self.generated_summary: Optional[List[Dict[str, Union[str, float]]]] = None

        # --- UI Layout ---
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_plan = self.tabview.add("Planner")
        self.tab_settings = self.tabview.add("Settings")

        self._setup_planner_tab()
        self._setup_settings_tab()

        logging.info("GUI Ready.")

    def _setup_planner_tab(self) -> None:
        """Constructs the main planner dashboard."""
        
        # 1. Configuration Row
        frame_setup = ctk.CTkFrame(self.tab_plan)
        frame_setup.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(frame_setup, text="Workplace:").grid(row=0, column=0, padx=5)
        self.entry_workplace = ctk.CTkEntry(frame_setup, width=200)
        self.entry_workplace.insert(0, str(self.config.get('workplace_name', '')))
        self.entry_workplace.grid(row=0, column=1, padx=5)

        ctk.CTkLabel(frame_setup, text="Date:").grid(row=0, column=2, padx=5)
        self.combo_month = ctk.CTkComboBox(frame_setup, values=list(calendar.month_name)[1:], width=110)
        curr_m = int(self.config.get('month', datetime.datetime.now().month))
        self.combo_month.set(list(calendar.month_name)[1:][curr_m - 1])
        self.combo_month.grid(row=0, column=3, padx=5)

        self.entry_year = ctk.CTkEntry(frame_setup, width=60)
        self.entry_year.insert(0, str(self.config.get('year', datetime.datetime.now().year)))
        self.entry_year.grid(row=0, column=4, padx=5)

        self.btn_import = ctk.CTkButton(frame_setup, text="Import Balance", command=self.import_file)
        self.btn_import.grid(row=0, column=5, padx=10)
        self.lbl_import = ctk.CTkLabel(frame_setup, text="No file loaded", font=("Arial", 10), text_color="gray")
        self.lbl_import.grid(row=1, column=5)

        # 2. Constraints Row
        frame_cons = ctk.CTkFrame(self.tab_plan)
        frame_cons.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(frame_cons, text="Leave Constraints").pack(side="left", padx=10)
        self.combo_person = ctk.CTkComboBox(frame_cons, values=self.config.get('personnel', []))
        self.combo_person.pack(side="left", padx=5)
        self.entry_day = ctk.CTkEntry(frame_cons, placeholder_text="Day", width=50)
        self.entry_day.pack(side="left", padx=5)
        
        ctk.CTkButton(frame_cons, text="+", width=40, command=self.add_constraint).pack(side="left", padx=5)
        ctk.CTkButton(frame_cons, text="Clear", width=50, fg_color="firebrick", command=self.clear_constraints).pack(side="left", padx=5)

        self.listbox_cons = ctk.CTkTextbox(self.tab_plan, height=80)
        self.listbox_cons.pack(fill="x", padx=10, pady=5)
        self.listbox_cons.insert("0.0", "No constraints.\n")

        # 3. Actions
        frame_act = ctk.CTkFrame(self.tab_plan)
        frame_act.pack(fill="x", padx=10, pady=10)
        self.btn_gen = ctk.CTkButton(frame_act, text="GENERATE PREVIEW", command=self.run_generation)
        self.btn_gen.pack(side="left", fill="x", expand=True, padx=5)
        self.btn_save = ctk.CTkButton(frame_act, text="SAVE EXCEL", fg_color="green", state="disabled", command=self.save_excel)
        self.btn_save.pack(side="left", fill="x", expand=True, padx=5)

        # 4. Preview
        self.txt_preview = ctk.CTkTextbox(self.tab_plan)
        self.txt_preview.pack(fill="both", expand=True, padx=10, pady=5)

    def _setup_settings_tab(self) -> None:
        """Constructs the settings configurator."""
        self.frame_sets = ctk.CTkScrollableFrame(self.tab_settings)
        self.frame_sets.pack(fill="both", expand=True)

        ctk.CTkLabel(self.frame_sets, text="Mode").pack(anchor="w", padx=10)
        self.combo_mode = ctk.CTkComboBox(self.frame_sets, values=C.SCHEDULING_MODES)
        self.combo_mode.set(str(self.config.get("mode", "hybrid")))
        self.combo_mode.pack(anchor="w", padx=10, pady=5)

        ctk.CTkLabel(self.frame_sets, text="Personnel (csv)").pack(anchor="w", padx=10)
        self.entry_ppl = ctk.CTkTextbox(self.frame_sets, height=60)
        self.entry_ppl.insert("0.0", ", ".join(self.config.get("personnel", [])))
        self.entry_ppl.pack(fill="x", padx=10, pady=5)

        # Dynamic Points
        self.entries_pts: Dict[str, ctk.CTkEntry] = {}
        for k, v in self.config.get("points", {}).items():
            f = ctk.CTkFrame(self.frame_sets)
            f.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(f, text=f"Points {k}:", width=120, anchor="w").pack(side="left")
            e = ctk.CTkEntry(f)
            e.insert(0, str(v))
            e.pack(side="right", expand=True, fill="x")
            self.entries_pts[k] = e

        ctk.CTkButton(self.tab_settings, text="Save Settings", command=self.save_settings).pack(pady=10)

    # --- Helpers ---
    def _get_max_days(self) -> int:
        try:
            y = int(self.entry_year.get())
            m = list(calendar.month_name).index(self.combo_month.get())
            return pd.Period(f'{y}-{m}').days_in_month
        except Exception:
            return 31

    # --- Actions ---
    def add_constraint(self) -> None:
        p = self.combo_person.get()
        d_str = self.entry_day.get()
        if not p or not d_str.isdigit():
            messagebox.showwarning("Error", "Invalid Input")
            return
        d = int(d_str)
        if not (1 <= d <= self._get_max_days()):
            messagebox.showerror("Error", "Invalid Day")
            return
        
        self.leaves.append((p, d))
        self.listbox_cons.insert("end", f"{p} - Day {d} (Leave)\n")
        self.entry_day.delete(0, "end")

    def clear_constraints(self) -> None:
        if messagebox.askyesno("Confirm", "Clear all?"):
            self.leaves = []
            self.listbox_cons.delete("0.0", "end")

    def save_settings(self) -> None:
        try:
            self.config['mode'] = self.combo_mode.get()
            ppl = self.entry_ppl.get("0.0", "end").strip()
            if not ppl: raise ValueError("Personnel empty")
            self.config['personnel'] = [x.strip() for x in ppl.split(",") if x.strip()]
            
            for k, e in self.entries_pts.items():
                self.config['points'][k] = float(e.get())
            
            DataManager.save_config(self.config)
            self.combo_person.configure(values=self.config['personnel'])
            messagebox.showinfo("Success", "Settings Saved")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def import_file(self) -> None:
        fp = filedialog.askopenfilename()
        if not fp: return
        try:
            self.prev_balance = DataManager.load_previous_balance(fp)
            self.lbl_import.configure(text=f"Loaded: {len(self.prev_balance)}", text_color="green")
            messagebox.showinfo("Success", "Import Complete")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # --- Async Generation ---
    def run_generation(self) -> None:
        if not self.entry_workplace.get():
            messagebox.showwarning("Missing", "Enter Workplace Name")
            return
        
        # Update config state from UI
        self.config['workplace_name'] = self.entry_workplace.get()
        self.config['year'] = int(self.entry_year.get())
        self.config['month'] = list(calendar.month_name).index(self.combo_month.get())

        self.txt_preview.delete("0.0", "end")
        self.txt_preview.insert("0.0", "Calculating... (GUI is active)\n")
        self.btn_gen.configure(state="disabled")
        
        # Threading
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        try:
            engine = DutySchedulerEngine(self.config, self.prev_balance, self.leaves)
            engine.build_model()
            res = engine.solve()
            self.after(0, self._on_success, res)
        except Exception as e:
            self.after(0, self._on_error, str(e))

    def _on_success(self, res: Any) -> None:
        self.btn_gen.configure(state="normal")
        if res:
            self.generated_schedule, self.generated_summary = res
            self.txt_preview.delete("0.0", "end")
            
            # Format Output
            out = f"Plan Generated!\n{'-'*40}\nName\tCarry Over\n{'-'*40}\n"
            for p in self.generated_summary: # type: ignore
                out += f"{p['Name']:<10}\t{float(p['Carry Over']):.1f}\n" # type: ignore
            
            self.txt_preview.insert("0.0", out)
            self.btn_save.configure(state="normal")
        else:
            self.txt_preview.insert("end", "\nNo solution found.")

    def _on_error(self, msg: str) -> None:
        self.btn_gen.configure(state="normal")
        messagebox.showerror("Error", msg)

    def save_excel(self) -> None:
        if not self.generated_schedule: return
        fp = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if fp:
            try:
                DataManager.export_schedule(
                    self.generated_schedule, self.generated_summary, # type: ignore
                    self.config, self.leaves, fp
                )
                messagebox.showinfo("Success", "File Saved")
            except Exception as e:
                messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    app = App()
    app.mainloop()
