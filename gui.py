"""
gui.py

Main Application Entry Point for Duty Scheduler Pro v8.0.
Acts as the Controller, coordinating the Planner and Settings tabs.
"""

import customtkinter as ctk  # type: ignore

import constants as C
import logger

# Internal Modules
from data_manager import DataManager
from planner_tab import PlannerTab
from settings_tab import SettingsTab

# Setup Logging and Theme
logger.setup_logger()
ctk.set_appearance_mode(C.THEME_MODE)

class App(ctk.CTk):
    """
    Main Window Application Class.
    
    Manages the application lifecycle, holds shared configuration state,
    and instantiates the tab controllers.
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
        # Pass callback to notify App if Planner changes data (e.g. imports)
        self.plan = PlannerTab(
            self.tabview.add("Planner"), 
            self.config, 
            on_update_callback=self.on_data_change
        )
        self.plan.pack(fill="both", expand=True)
        
        # Instantiate Settings Tab
        # Pass callback to notify App if Settings change config
        self.sett = SettingsTab(
            self.tabview.add("Settings"), 
            self.config, 
            self.on_save
        )
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
        (e.g. Import overwrites personnel).
        Syncs the Settings UI.
        """
        self.sett.config = self.config
        self.sett.refresh_ui()

if __name__ == "__main__":
    App().mainloop()
