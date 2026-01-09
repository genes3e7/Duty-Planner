[![Supported Python](https://img.shields.io/badge/python-3.12_to_3.15-blue)](https://www.python.org/downloads/)

# **📅 Duty Planner**

**Duty Planner** is a specialized scheduling application designed to automate the creation of monthly duty rosters. It uses **Google OR-Tools** (CP-SAT solver) to generate fair and compliant schedules while respecting strict constraints, and **Streamlit** for a modern, reactive web interface.

## **🌟 Key Features**

* **Automated Scheduling:** Generates a full month's roster in seconds, balancing fairness across all personnel.  
* **Flexible Constraints:**  
  * Define manpower requirements per shift (AM, PM, 24H, Standby).  
  * Respect Public Holidays (PH) and Weekends automatically.  
  * Prevent consecutive duty overload (e.g., max 3 days in a row).  
* **Smart Pre-Assignment:** Manually assign duties or leave (e.g., 'X' for unavailability) before running the solver—the algorithm fills in the rest.  
* **Bulk Management:**  
  * **Excel Import:** Upload constraints for the whole team via Excel.  
  * **Balance Carry-Over:** Import points from the previous month to ensure long-term fairness.  
* **Points-Based Fairness:** Assigns weights to different shift types (e.g., 24H duties are worth more than AM shifts).  
* **Excel Export:** Download the final roster in a formatted `.xlsx` file ready for distribution.

## **🏗 Architecture**

The project is built on a clean separation of concerns using Python 3.12+:

| Component | Technology | Description |
| :---- | :---- | :---- |
| **Frontend** | [Streamlit](https://streamlit.io/) | `streamlit_app.py` handles the UI, state management, and user interaction. |
| **Logic Layer** | Python | `app/logic.py` acts as the bridge, preparing data for the solver and calculating statistics. |
| **Solver Engine** | [Google OR-Tools](https://developers.google.com/optimization) | `app/core/scheduler.py` defines the constraint programming model and finds optimal solutions. |
| **Data Models** | Pydantic | `app/models/config.py` ensures strict type validation for configuration and settings. |
| **Persistence** | JSON / Excel | Configuration is saved to `config.json`; Rosters are exported/imported via `openpyxl`. |

## **🚀 Getting Started**

### **Prerequisites**

* Python **3.12** or higher.  
* `pip` package manager.

### **Installation**

1. **Clone the Repository**
   ```ps1
   git clone [https://github.com/genes3e7/duty-planner.git](https://github.com/genes3e7/duty-planner.git)  
   cd duty-planner
   ```
2. **Create a Virtual Environment (Recommended)**  
   ```ps1
   python -m venv venv  
   # Windows  
   venv\Scripts\activate  
   # Mac/Linux  
   source venv/bin/activate
   ```
3. **Install Dependencies**  
   ```ps1
   pip install -r requirements.txt
   ```
### **Running the App**

Start the local web server:
```ps1
streamlit run streamlit_app.py
```
Your browser will automatically open to `http://localhost:8501`.

## **📖 User Guide**

### **1\. Initial Setup (Sidebar)**

* **Select Date:** Choose the Month and Year you are planning for using the date picker.  
* **Load / Reset Grid:** Click this button to generate a fresh, empty table for the selected month.  
* **Import Balance (Optional):** If you have the Excel file from last month, upload it here. The system will read the "Carry Over" points for each person to ensure fairness continues.

### **2\. Configuring the Month (Planner Tab)**

Before assigning names, configure the days:

* **Day Settings Expander:**  
  * **Mode:** Set days to **Shift** (AM/PM) or **24H** (Full day). Use the "Set All" buttons for quick setup.  
  * **PH (Public Holiday):** Check the box if a day is a holiday. This usually triggers higher points or 24H logic depending on your settings.  
  * **Active:** Uncheck a day to exclude it from planning entirely (no duties will be assigned).

### **3\. Setting Constraints (The Grid)**

* **Manual Entry:** Click any cell in the "Roster Grid" to assign a specific duty or status:  
  * `X`: Unavailable / Leave.  
  * `AM` / `PM` / `24H`: Pre-assigned duty.  
  * `S/B`: Standby duty.  
* **Bulk Upload:** Use the "Bulk Constraint Upload" expander to upload an Excel file containing pre-filled constraints (Columns: `Name`, `1`, `2`, ...).

### **4\. Generation & Export**

1. **Generate:** Click **🚀 GENERATE FILL**. The solver will calculate the optimal schedule filling all empty cells.  
2. **Review:** Check the "Statistics" panel to see the point distribution and fairness standard deviation.  
3. **Download:** Click **📥 Download Excel** to get the final schedule.

## **⚙️ Configuration (Settings Tab)**

You can customize how the algorithm works in the **Settings** tab:

### **Manpower Requirements**

Define how many people are needed for each shift type per day.

* *Example:* `AM: 2` means the solver must find 2 people for every AM shift.

### **Scoring Logic**

* **Base Points:** How many points is a duty worth? (e.g., `24H \= 2.0`, `AM \= 1.0`).  
* **Multipliers:**  
  * **Public Holidays:** Apply a multiplier (e.g., `2x`) or addition (`+2`) to points earned on holidays.  
  * **Weekends:** Similar logic for Saturdays and Sundays.

### **Personnel List**

A simple comma-separated list of names used to populate the rows of the roster.

## **📂 Project Structure**
```
duty-planner/  
├── .github/workflows/    \# CI/CD Pipeline (Tests & Linting)  
├── .streamlit/           \# Streamlit UI configuration  
├── app/  
│   ├── core/  
│   │   ├── data.py       \# JSON/Excel I/O operations  
│   │   └── scheduler.py  \# OR-Tools Solver Engine  
│   ├── models/  
│   │   └── config.py     \# Pydantic Data Models  
│   ├── constants.py      \# App-wide constants (colors, column names)  
│   └── logic.py          \# Business logic & Middleman  
├── tests/                \# Pytest suite  
├── requirements.in       \# High-level dependencies  
├── requirements.txt      \# Locked dependencies  
└── streamlit\_app.py      \# Main Application Entry Point
```

## **🧪 Developer Guide**

### **Running Tests**

The project uses `pytest` for unit and integration testing.
```ps1
pytest
```

### **Code Formatting**

We use `ruff` for linting and formatting.
```ps1
# Check for issues  
ruff check .

# Fix auto-fixable issues  
ruff check . --fix

# Format code  
ruff format .  
```