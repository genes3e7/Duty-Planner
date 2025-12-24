# Duty Scheduler Pro v3.0.0

A professional automated rostering tool designed for 24/7 operations. It uses constraint programming (Google OR-Tools) to generate fair, rule-compliant schedules while optimizing for equal point distribution.

## 🌟 Features

* **Interactive Grid:** Excel-like interface to view and edit rosters in real-time.
* **Smart Solver:**
    * **Strict Gap Rule:** Enforces mandatory rest days. No back-to-back duties.
    * **Manpower Constraints:** Enforces daily requirements for AM, PM, 24H, and Standby shifts.
    * **Fairness Optimization:** Mathematically minimizes the variance in "duty points" across all staff.
* **Flexible Scheduling:**
    * **Duty Toggle:** Disable specific days entirely (e.g., weekends or office closures).
    * **24H Mode:** Toggle individual days between 3-shift mode (AM/PM) and 24-hour duty mode.
* **Smart Configuration:**
    * **Dynamic Import:** "Import Previous Month" scans for new names and keeps balances in sync.
    * **GUI Settings:** Adjust staff lists, requirements, and scoring rules directly in the app.
* **Data Integrity:** Imports previous month's balances to ensure long-term fairness.

## 🚀 Installation & Usage

1.  **Prerequisites:** Python 3.11 - 3.13
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the application:**
    ```bash
    python run.py
    ```

## 📖 User Guide

### 1. Initial Setup
Navigate to the **Settings** tab:
* **Daily Requirements:** Set manpower needs for each shift.
* **Points Scoring:** Adjust shift weights and multipliers.
* **Personnel List:** Manage your staff list.
* Click **Save & Reload** to apply changes.

### 2. Planning a Roster
Switch to the **Planner** tab:
1.  Select **Month** and **Year**, then click **Load Grid**.
2.  **Manual Constraints:** Click cells to pre-assign duties or leave:
    * `X` = Leave (Solver will skip).
    * `AM`/`PM`/`24H` = Forced Duty (Solver will respect).
3.  **Generate:** Click **GENERATE FILL** to auto-fill the rest.

### 3. Importing & Exporting
* **Import Previous Month:** Load an Excel file to carry forward point balances.
* **Export xlsx:** Save the final roster to Excel.

---

## 🛠️ Developer & CI/CD Guide

The codebase uses a modular architecture (`app/` package) for maintainability and testing.

### Project Structure
```text
Duty-Planner/
├── app/
│   ├── core/       # Business Logic & Data Management
│   ├── models/     # Configuration Data Classes
│   ├── ui/         # GUI Components (Planner, Settings)
│   ├── utils/      # Logging & Helpers
│   └── main.py     # Application Controller
├── tests/          # Pytest Suite
├── tools/          # CI/CD Scripts
├── run.py          # Entry Point
└── build.py        # PyInstaller Build Script
```

### Running Tests
The project uses `pytest` for unit testing. The CI pipeline automatically runs these on every push to ensure logic integrity.

```bash
# Run all tests
pytest tests/
```

### Building the Executable
To create a standalone `.exe` (Windows) or binary (Linux/Mac):

```bash
python build.py
```
The output file will be located in the `dist/` folder.

### Automated Workflows (GitHub Actions)
This repository features a robust CI pipeline that:
1.  **Tests:** Runs the test suite across Python 3.10–3.13 matrix.
2.  **Lints:** Automatically fixes code style issues using `ruff`.
3.  **Updates Docs:** Automatically updates `README.md` with the currently supported Python versions.

## 📄 License

This project is released under the **Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)**.

* **Usage:** Free for personal and non-commercial organizational use.
* **Commercial Use:** Prohibited without express permission.

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
