# Duty Scheduler Pro

A production-ready, constraint-based roster generation tool designed for complex shift work and 24H duty environments. Built with Python, CustomTkinter, and Google OR-Tools, it solves rostering problems mathematically rather than randomly, ensuring optimal fairness and rule compliance.

## 🚀 Key Features

* **Fairness Engine:** Uses a Constraint Satisfaction Problem (CSP) solver to minimize the variance in "Points" across all staff.
* **Dynamic Scoring:**
    * **Points:** Customizable scores for AM, PM, 24H, and Standby shifts.
    * **Multipliers:** Automatic x1.5 or x2.0 multipliers for Weekends and Public Holidays (Singapore holidays auto-detected).
    * **Rollover:** Import the previous month's Excel file to carry over point imbalances.
* **Hybrid Rostering Modes:**
    * `Shift`: Standard AM/PM rosters.
    * `24H`: Full-day duties only.
    * `Hybrid`: Auto-switches between Shift mode (Weekdays) and 24H mode (PH/Weekends).
* **Smart Rollover:** If User A finished last month with +5 points more than average, the solver starts them with a "virtual penalty" this month to ensure they get fewer shifts.
* **Robust Constraints:** Hard blocks for leaves/off-days and intelligent rest rules (e.g., forced rest day after a 24H shift).

---

## 🧠 How It Works (The Logic Core)

The application does not "guess" the schedule. It translates your requirements into a mathematical model and solves for the optimal solution.

### 1. The Scoring System
Fairness is defined by **Points**, not just duty counts.
* **Base Points:** Assigned per shift type (e.g., 24H = 3 pts, AM = 1 pt).
* **Multipliers:** Applied automatically based on the date.
    * *Example:* A 24H duty on a Public Holiday = `3 (Base) * 2.0 (Multiplier) = 6 Points`.

### 2. Constraint Hierarchy
The solver respects rules in this order of priority:

1.  **Hard Constraints (Must be met):**
    * **Manpower:** Every shift must have exactly the required number of people (e.g., 1x AM, 1x PM).
    * **Exclusivity:** A person can only do **one** shift per day.
    * **Leaves:** If a user is marked on Leave (X), they cannot be assigned any duty.
    * **Rest Rules:** A person cannot work the day immediately after a 24H duty.

2.  **Soft Objectives (Optimization Goals):**
    * **Primary Goal:** Minimize the difference between the highest and lowest total scores among all staff.
    * **Secondary Goal:** Distribute "Standby" duties as evenly as possible (since they carry 0 points).

---

## 🛠️ Project Structure

This project follows a modular architecture for maintainability:

| File | Description |
| :--- | :--- |
| **`gui.py`** | **The Entry Point.** Handles the UI, input validation, and runs the heavy math in a background thread to keep the app responsive. |
| **`scheduler_engine.py`** | **The Brain.** Contains the Google OR-Tools model. It builds the variables and equations that define a valid schedule. |
| **`data_manager.py`** | **The Librarian.** Handles reading config files, safe Excel exports, and "fuzzy matching" to import previous records. |
| **`constants.py`** | **The Settings.** Stores static values, colors, and default configuration templates. |
| **`logger.py`** | **The Recorder.** Sets up logging to `app.log` and the console for debugging errors. |
| **`build.py`** | **The Builder.** A script to package the entire application into a standalone `.exe`. |

---

## 📦 Installation & Setup

### Prerequisites
* Python 3.10 or higher.

### Step 1: Install Dependencies
It is recommended to use a virtual environment.
```bash
# Create venv
python -m venv venv

# Activate venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install libraries
pip install -r requirements.txt
```

### Step 2: Run the App
```bash
python gui.py
```

---

## 📖 User Guide

### 1. Configuration (First Run)
Go to the **Settings** tab.
1.  **Mode:** Select `Hybrid` (recommended for most units).
2.  **Personnel:** Enter names separated by commas (e.g., `Alice, Bob, Charlie`).
3.  **Points:** Adjust the weight of each shift type.
4.  Click **Save Settings**. This creates/updates `config.json`.

### 2. Generating a Roster
Go to the **Planner** tab.
1.  **Details:** Enter your Unit Name and select the Month/Year.
2.  **Rollover (Optional):** Click "Import Last Month" and select the previous Excel file. The app looks for "Name" and "Carry Over" columns.
3.  **Constraints:** Select a person and a day (e.g., Day 5) and click **Add**. This locks them out of duties for that day.
4.  **Run:** Click **PREVIEW SCHEDULE**. The logic engine will run in the background.
5.  **Export:** Review the preview text. If satisfied, click **CONFIRM & SAVE EXCEL**.

---

## 🏗️ Building for Distribution

To give this tool to colleagues who don't have Python installed, build a standalone executable:

```bash
python build.py
```

* The build script cleans up previous artifacts.
* It includes the `customtkinter` theme data automatically.
* The final file `DutySchedulerPro.exe` will be located in the `dist/` folder.

---

## 🧪 Testing

To ensure the logic engine is working correctly (e.g., after modifying code), run the unit test suite:

```bash
python tests.py
```
