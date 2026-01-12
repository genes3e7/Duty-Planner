# Duty Planner

A Streamlit-based application for scheduling staff duties. This tool provides an interactive interface to plan rosters, configure constraints, and optimize schedules using Google's OR-Tools.

<!-- BADGES_START -->
[![Supported Python](https://img.shields.io/badge/python-3.12_to_3.14-blue)](https://www.python.org/downloads/)
<!-- BADGES_END -->

## Features

* **Interactive Planner:** Visual grid to manually assign or view duties.
* **Automated Scheduling:** Uses constraint programming (OR-Tools) to auto-fill the roster while respecting rules.
* **Fairness Optimization:** Attempts to balance points (workload) across all staff, considering carried-over balances.
* **Configurable Rules:**
  * Set daily manpower needs (AM, PM, 24H, Standby).
  * Define point values for different shifts.
  * Apply multipliers for weekends and public holidays.
* **Excel Export:** Download the final roster and statistics as an Excel file.

## Architecture

The application follows a Model-View-Controller (MVC) pattern adapted for Streamlit.

```mermaid
sequenceDiagram
    actor User
    participant Browser as Streamlit UI
    participant Sidebar as Sidebar
    participant Logic as Logic Layer
    participant Solver as DutySchedulerEngine
    participant DataMgr as DataManager

    User->>Browser: open app / choose Planner or Settings
    Browser->>Sidebar: load/save config, upload .xlsx (balances/constraints)
    Browser->>Logic: generate_empty_schedule(year, month, personnel)
    Browser->>Logic: prepare_solver_request(year, month, roster, days, config)
    Logic->>Solver: build_model(SolverRequest)
    Logic->>Solver: solve()
    Solver-->>Logic: solution or failure
    Logic->>DataMgr: save_config / load_previous_balance / load_constraints
    Logic-->>Browser: roster_df, stats, excel_bytes (for download)
    Browser-->>User: display roster, stats, download link
```

## Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/genes3e7/duty-planner.git
    cd duty-planner
    ```

2.  **Create a virtual environment (Recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application:**
    ```bash
    streamlit run streamlit_app.py
    ```

## Configuration

The application settings are stored in `config.json` (created on first save). You can modify these via the **Settings** page in the UI or by editing the JSON file directly.

* **Personnel:** List of names.
* **Constraints:**
  * `personnel_needed_per_shift`: Dictionary defining needs (e.g., `{"AM": 1, "PM": 1}`).
  * `max_consecutive_duties`: Max days a person can work in a row.
* **Points:**
  * **Base Points:** How many points is a duty worth? (e.g., `24H = 2.0`, `AM = 1.0`).
  * **Multipliers:** Configure multipliers for Weekends, Public Holidays, etc.

## Development

* **Dependency Management:** Uses `pip-tools`.
  * To update deps: `pip-compile requirements.in`
  * To install dev deps: `pip install -r requirements-dev.txt`
* **Linting:** Uses `ruff` for linting and formatting.
  * Check: `ruff check .`
  * Format: `ruff format .`
* **Tests:** Run `pytest` to execute the test suite.
  * Run with coverage: `pytest --cov=app tests/`

## Testing Methodology

The project employs a robust testing strategy:
* **Unit Tests (`tests/test_logic.py`, `tests/test_data.py`):** Verify individual components in isolation, mocking external dependencies like file I/O.
* **Core Logic Tests (`tests/test_core_scheduler.py`):** Validate the solver engine against specific constraints.
* **Integration Tests (`tests/test_app_integration.py`):** Use Streamlit's `AppTest` framework to simulate user interactions and verify UI state persistence.
