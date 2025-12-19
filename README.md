# Duty Scheduler Pro v6.4

A professional automated rostering tool designed for 24/7 operations. It uses constraint programming (Google OR-Tools) to generate fair, rule-compliant schedules while optimizing for equal point distribution.

## 🚀 Features

* **Interactive Grid:** Excel-like interface to view and edit rosters in real-time.
* **Smart Solver:**
    * **Strict Gap Rule:** Enforces mandatory rest days. No back-to-back duties of any kind (e.g., cannot do PM on Monday and AM on Tuesday).
    * **Manpower Constraints:** Enforces daily requirements for AM, PM, 24H, and Standby shifts.
    * **Fairness Optimization:** Minimizes the variance in "duty points" across all staff.
* **Flexible Modes:**
    * **24H Mode:** All shifts are 24-hour duties.
    * **Shift Mode:** AM/PM splits.
    * **Hybrid:** Auto-switches based on Weekends/Public Holidays.
* **Smart Configuration:**
    * **Dynamic Import:** Automatically detects and adds new staff names when importing balance files.
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
* **Daily Requirements:** Set how many people you need for each shift type (AM, PM, 24H, Standby).
* **Points Scoring:** Adjust the weight of each shift and multipliers for Weekends/PH.
* **Personnel List:** Enter staff names (separated by commas or new lines).
* Click **Save & Reload** to apply changes.

### 2. Planning a Roster
Switch to the **Planner** tab:
1.  Select the **Month** and **Year**.
2.  Click **Load Grid**.
3.  **Import Balances (Optional):** Load an Excel file from the previous month to carry over scores. New names found in the file will be auto-added.
4.  **Manual Constraints:** Click cells to cycle through pre-assigned statuses:
    * `X` = Leave (Solver will NOT assign duty).
    * `AM`/`PM`/`24H` = Forced Duty (Solver will keep this).
5.  **24H Toggle:** Use the checkboxes in the header row (or **Check All 24H**) to force specific days into 24H mode.
6.  **Generate:** Click **GENERATE FILL**. The AI will fill empty slots while respecting your manual inputs and rules.

### 3. Export
* Click **Export to Excel** to save a formatted `.xlsx` file containing the roster and points summary.

## 🏗 Building .exe

To create a standalone executable for Windows (no Python required for end-users):

```bash
python build.py
```

The output file `DutySchedulerPro.exe` will be generated in the `dist/` folder.

## 📄 License

This project is licensed under the **Creative Commons Attribution-NonCommercial 4.0 International License**.

You are free to:
* **Share** — copy and redistribute the material in any medium or format.
* **Adapt** — remix, transform, and build upon the material.

Under the following terms:
* **Attribution** — You must give appropriate credit.
* **NonCommercial** — You may not use the material for commercial purposes.

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)