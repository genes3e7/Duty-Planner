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
    participant Main as streamlit_app.py
    participant Sidebar as app/ui/sidebar.py
    participant Planner as app/ui/planner.py
    participant Logic as app/logic.py
    participant Data as app/core/data.py
    participant Engine as app/core/scheduler.py
    participant ORTools as CP-SAT Solver

    User->>Main: Opens Application
    Main->>Sidebar: render_sidebar()
    activate Sidebar
    Sidebar->>Data: load_config()
    Data-->>Sidebar: AppConfig
    Sidebar->>Data: load_previous_balance()
    Data-->>Sidebar: Balance Dict
    Sidebar-->>Main: Navigation Selection (Planner/Settings)
    deactivate Sidebar

    alt User Selects "Planner"
        Main->>Planner: render_planner(config)
        activate Planner
        
        opt Data Initialization
            Planner->>Logic: generate_empty_schedule(year, month)
            Logic-->>Planner: RosterDF, DayConfigDF
        end

        Planner-->>User: Displays Editable Roster Grid & Toolbar
        
        User->>Planner: Modifies Constraints (Grid/Day Config)
        
        User->>Planner: Clicks "Auto-Fill Schedule"
        Planner->>Logic: run_solver(df_roster, df_days, config, balance)
        activate Logic
        
        Logic->>Logic: prepare_solver_request()
        Note right of Logic: Transforms DataFrames to SolverRequest
        
        Logic->>Engine: Init DutySchedulerEngine(config, request)
        activate Engine
        
        Engine->>Engine: build_model()
        Engine->>ORTools: Create Variables (Person, Day, Shift)
        Engine->>ORTools: Add Hard Constraints (Coverage, 24H rules, etc.)
        Engine->>ORTools: Add Soft Constraints (Fairness/Objectives)
        
        Engine->>Engine: solve()
        Engine->>ORTools: Solve()
        ORTools-->>Engine: Status, Solution Values
        
        Engine-->>Logic: Schedule Dictionary
        deactivate Engine
        
        Logic-->>Planner: Schedule Dictionary
        deactivate Logic
        
        Planner->>Planner: Update Roster DataFrame
        Planner->>Logic: calculate_stats(df_roster...)
        Logic-->>Planner: Statistics DataFrame
        
        Planner-->>User: Displays Updated Roster & Stats
        deactivate Planner

    else User Selects "Settings"
        Main->>Settings: render_settings(config)
        User->>Settings: Updates Config (In-Memory)
        User->>Sidebar: Clicks "Save Configuration"
        Sidebar->>Data: save_config(config)
    end
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

* **Tests:** Run `pytest` to execute the test suite.
* **Linting:** Uses `ruff` for linting and formatting.
* **Dependency Management:** Uses `pip-tools` (`requirements.in`).
