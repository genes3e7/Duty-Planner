# Duty Scheduler Pro v3.0.0

A professional automated rostering tool designed for 24/7 operations. It uses constraint programming (Google OR-Tools) to generate fair, rule-compliant schedules while optimizing for equal point distribution.

## 🚀 Features

* **Interactive Grid:** Excel-like interface to view and edit rosters in real-time.
* **Smart Solver:**
    * **Strict Gap Rule:** Enforces mandatory rest days. No back-to-back duties.
    * **Manpower Constraints:** Enforces daily requirements for AM, PM, 24H, and Standby shifts.
    * **Fairness Optimization:** Mathematically minimizes the variance in "duty points" across all staff.
* **Flexible Scheduling:**
    * **Duty Toggle:** Disable specific days entirely (e.g., weekends or office closures) by unchecking the "Duty?" row.
    * **24H Mode:** Toggle individual days between 3-shift mode (AM/PM) and 24-hour duty mode.
        * *Smart Default:* Only Public Holidays default to 24H mode. Weekends default to standard shifts.
* **Smart Configuration:**
    * **Dynamic Import:** "Import Previous Month" now scans for new names and offers to **overwrite** your settings to keep everything in sync.
    * **GUI Settings:** Adjust staff lists, daily requirements, and point values directly in the app.
* **Data Integrity:** Imports previous month's balances (Carry Over) to ensure long-term fairness.

## 📦 Installation

1.  **Prerequisites:** Python 3.10 or higher.
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the application:**
    ```bash
    python gui.py
    ```

## 📖 User Guide

### 1. Initial Setup
Navigate to the **Settings** tab:
* **Daily Requirements:** Set how many people you need for each shift type.
* **Points Scoring:** Adjust the weight of each shift and multipliers for Weekends/PH.
* **Personnel List:** Enter staff names (separated by commas or new lines).
* Click **Save & Reload** to apply changes.

### 2. Planning a Roster
Switch to the **Planner** tab:
1.  Select the **Month** and **Year** and click **Load Grid**.
2.  **Disable Days (Optional):** If no duty is required on a specific date (e.g., a weekend), uncheck the box in the **"Duty?"** row. The column will turn grey and be excluded from planning.
3.  **24H Toggle:** Use the checkboxes in the **"24H?"** row to force specific days into 24-hour duty mode.
4.  **Manual Constraints:** Click cells to cycle through pre-assigned statuses:
    * `X` = Leave (Solver will NOT assign duty).
    * `AM`/`PM`/`24H` = Forced Duty (Solver will keep this).
5.  **Generate:** Click **GENERATE FILL**. The AI will fill empty slots while respecting your manual inputs and rules.

### 3. Importing & Exporting
* **Import Previous Month:** Loads an Excel file to carry forward point balances.
    * *Note:* If the file contains names not in your config, the app will ask if you want to **overwrite** your personnel list with the file's data.
* **Export xlsx:** Saves the final roster and point summary to Excel.

### 4. Bulk Actions
* **Reset Table:** Wipes the entire grid clean.
* **Clear Duties:** Removes assigned duties (AM/PM/24H/SB) but keeps Leave (`X`) entries intact.

## 🏗 Developer Notes (v3.0 Architecture)

The codebase is modularized for maintainability:
* `gui.py`: Main Entry Point & Controller.
* `planner_tab.py`: Grid UI and Interaction Logic.
* `settings_tab.py`: Configuration UI.
* `scheduler_engine.py`: Google OR-Tools Wrapper (Logic Layer).
* `config_models.py`: Strict Data Classes for configuration.
* `constants.py`: Enums and static constants.

## 📄 License

This project is released under the **Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)**.

* **Usage:** Free for personal and non-commercial organizational use.
* **Commercial Use:** Prohibited without express permission.

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
