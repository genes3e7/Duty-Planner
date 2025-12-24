"""
settings_tab.py

Encapsulates the UI and logic for the 'Settings' tab.
Responsible for validating user inputs and saving the configuration.
"""

from tkinter import messagebox

import customtkinter as ctk
from constants import ShiftType

from app.core.data import DataManager
from app.models.config import AppConfig
from app.ui import helpers as GH


class SettingsTab(ctk.CTkFrame):
    """
    The Settings Tab Frame Controller.
    """

    def __init__(self, parent, config: AppConfig, on_save):
        """
        Args:
            parent: Parent widget.
            config: Shared AppConfig.
            on_save: Callback to trigger when settings are saved.
        """
        super().__init__(parent)
        self.config = config
        self.on_save = on_save
        self.reqs = {}
        self.pts = {}
        self.txt_ppl = None
        self._build()

    def _build(self):
        """Builds the Settings UI."""
        sc = ctk.CTkScrollableFrame(self)
        sc.pack(fill="both", expand=True, padx=10, pady=10)

        # Manpower Section
        ctk.CTkLabel(sc, text="Manpower", font=("Arial", 16, "bold")).pack(pady=10)

        # Fix: Extract long config lookups to variables to pass line length checks
        req_am = self.config.constraints.personnel_needed_per_shift.get(
            ShiftType.AM.value, 1
        )
        GH.create_config_row(sc, "AM:", req_am, self.reqs, "AM")

        req_pm = self.config.constraints.personnel_needed_per_shift.get(
            ShiftType.PM.value, 1
        )
        GH.create_config_row(sc, "PM:", req_pm, self.reqs, "PM")

        req_24h = self.config.constraints.personnel_needed_per_shift.get(
            ShiftType.FULL_24H.value, 1
        )
        GH.create_config_row(sc, "24H:", req_24h, self.reqs, "24H")

        GH.create_config_row(
            sc, "Standby:", self.config.constraints.standby_per_day, self.reqs, "SB"
        )

        # Points Section
        ctk.CTkLabel(sc, text="Points", font=("Arial", 16, "bold")).pack(pady=10)
        GH.create_config_row(sc, "AM:", self.config.points.AM, self.pts, "AM")
        GH.create_config_row(sc, "PM:", self.config.points.PM, self.pts, "PM")
        GH.create_config_row(sc, "24H:", self.config.points.FULL_24H, self.pts, "24H")
        GH.create_config_row(
            sc, "PH Mul:", self.config.points.ph_multiplier, self.pts, "PH"
        )
        GH.create_config_row(
            sc, "Wknd Mul:", self.config.points.weekend_multiplier, self.pts, "WK"
        )

        # Personnel Section
        ctk.CTkLabel(sc, text="Personnel", font=("Arial", 16, "bold")).pack(pady=10)
        self.txt_ppl = ctk.CTkTextbox(sc, height=100)
        self.txt_ppl.insert("0.0", ", ".join(self.config.personnel))
        self.txt_ppl.pack(fill="x")

        # Save Button
        GH.create_button(sc, "Save", self.save, "top", 200, "green").pack(pady=20)

    def refresh_ui(self):
        """Refreshes the personnel textbox from the current config."""
        if self.txt_ppl:
            self.txt_ppl.delete("0.0", "end")
            self.txt_ppl.insert("0.0", ", ".join(self.config.personnel))

    def save(self):
        """Validates inputs and saves to disk."""
        try:
            # Constraints
            self.config.constraints.personnel_needed_per_shift = {
                ShiftType.AM.value: int(self.reqs["AM"].get()),
                ShiftType.PM.value: int(self.reqs["PM"].get()),
                ShiftType.FULL_24H.value: int(self.reqs["24H"].get()),
            }
            self.config.constraints.standby_per_day = int(self.reqs["SB"].get())

            # Points
            self.config.points.AM = float(self.pts["AM"].get())
            self.config.points.PM = float(self.pts["PM"].get())
            self.config.points.FULL_24H = float(self.pts["24H"].get())
            self.config.points.ph_multiplier = float(self.pts["PH"].get())
            self.config.points.weekend_multiplier = float(self.pts["WK"].get())

            # Personnel
            raw = self.txt_ppl.get("0.0", "end").replace("\n", ",")
            self.config.personnel = sorted(
                list(set([x.strip() for x in raw.split(",") if x.strip()]))
            )

            DataManager.save_config(self.config)
            self.on_save()
            messagebox.showinfo("Success", "Settings Saved.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
