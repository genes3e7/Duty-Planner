# Duty Scheduler Pro v6.0

A professional automated rostering tool designed for 24/7 operations. It uses constraint programming (Google OR-Tools) to generate fair, rule-compliant schedules while optimizing for equal point distribution.

## 🚀 Features

* **Interactive Grid:** Excel-like interface to view and edit rosters in real-time.
* **Smart Solver:**
    * Enforces daily manpower requirements (AM, PM, 24H, Standby).
    * **Strict Gap Rule:** No back-to-back duties of any kind. If a user works Day X, they cannot work Day X+1.
    * Optimizes for fairness (minimizing point variance between staff).
* **Flexible Modes:**
    * **24H Mode:** All shifts are 24-hour duties.
    * **Shift Mode:** AM/PM splits.
    * **Hybrid:** Auto-switches based on Weekends/Public Holidays.
* **Robust Configuration:** Customize points, multipliers, and staff list directly in the app.
* **Data Integrity:** Imports previous month's balances (Carry Over) to ensure long-term fairness.

## 📦 Installation

1.  Install Python 3.10 or higher.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the application:
    ```bash
    python gui.py
    ```

## 📖 User Guide

1.  **Setup:** Go to the **Settings** tab.
    * Enter your **Personnel** list (comma-separated or new lines).
    * Set your **Daily Requirements** (e.g., 1 AM, 1 PM, 1 Standby).
    * Adjust **Points Scoring** if necessary.
    * Click **Save & Reload**.
2.  **Planner:**
    * Select Month/Year and click **Load Grid**.
    * **Manual Overrides:** Click any cell to cycle through `X` (Leave), `AM`, `PM`, `24H`, etc.
    * **24H Toggle:** Use the checkboxes in the header row (or "Check All 24H") to force specific days into 24H mode.
    * **Generate:** Click **GENERATE FILL**. The solver will fill empty slots while respecting your manual inputs.
3.  **Export:** Click **Export to Excel** to save a formatted `.xlsx` file.

## 🏗 Building .exe

To create a standalone executable for Windows:
```bash
python build.py
```
The output file will be in the `dist/` folder.
