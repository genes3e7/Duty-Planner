"""
main.py

Main Application Entry Point.
Acts as the Controller, coordinating the Planner and Settings tabs.
"""

import customtkinter as ctk

# UPDATED IMPORTS: Pointing to the new 'app' package structure
from app import constants as C
from app.core.data import DataManager
from app.ui.planner import PlannerTab
from app.ui.settings import SettingsTab
from app.utils import logger

# Setup Logging
logger.setup_logger()


class DutySchedulerApp(ctk.CTk):
    """
    Main Window Application Class.
    """

    def __init__(self) -> None:
        """Initializes the main window and constructs the tab layout."""
        super().__init__()

        # Window Configuration
        self.title(C.APP_TITLE)
        self.geometry(C.APP_GEOMETRY)

        # Load Config once to share across tabs
        self.config = DataManager.load_config()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=10)

        # Instantiate Planner Tab
        self.plan = PlannerTab(
            self.tabview.add("Planner"),
            self.config,
            on_update_callback=self.on_data_change,
        )
        self.plan.pack(fill="both", expand=True)

        # Instantiate Settings Tab
        self.sett = SettingsTab(self.tabview.add("Settings"), self.config, self.on_save)
        self.sett.pack(fill="both", expand=True)

    def on_save(self) -> None:
        """
        Callback triggered when Settings are saved.
        Reloads config and refreshes the Planner.
        """
        self.config = DataManager.load_config()
        self.plan.config = self.config
        self.sett.config = self.config

        # Force refresh of planner grid
        self.plan.last_loaded = None
        self.plan.refresh_grid()

        # Switch view back to planner
        self.tabview.set("Planner")

    def on_data_change(self) -> None:
        """
        Callback triggered when Data is changed in Planner.
        Syncs the Settings UI.
        """
        self.sett.config = self.config
        self.sett.refresh_ui()


# --- FIX: Define main() so run.py can import it ---
def main():
    ctk.set_appearance_mode(C.THEME_MODE)
    ctk.set_default_color_theme(C.THEME_COLOR)

    app = DutySchedulerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
