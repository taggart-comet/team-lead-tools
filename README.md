# 📊 Sprint Analytics Dashboard

A simple tool to analyze your sprint performance with accurate capacity metrics.

## How to Use This Tool

### 1. Export Data from Jira

1. **Go to your Jira Sprint Report**
   - Navigate to your project's Sprint Report page

2. **Open in Issue Navigator**
   - Click "Open in Issue Navigator" button at the top right

3. **Download CSV with All Fields**
   - Click "Export" → "CSV (All Fields)"
   - This ensures you get all the data needed for analysis

### 2. Prepare Your Data

1. **Save the CSV file** in the `datasets/` folder
2. **Rename it** to something meaningful (e.g., `q3_sprint_1_2025.csv`)

### 3. Run the Analysis

1. **Install dependencies** (first time only):
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the dashboard**:
   ```bash
   streamlit run app.py
   ```

3. **Open in browser**: Go to `http://localhost:8501`

### 4. Adjust Sprint Dates

**Important**: You'll need to manually set the correct sprint start and end dates because:

- Jira CSV exports don't include precise sprint boundary information
- The tool calculates initial dates from task closure patterns, but these might not match your actual sprint dates
- Tasks closed outside the sprint period shouldn't count as "completed" for that sprint

**Example**: If your sprint ran July 1-14, but someone closed a task on July 16, that task shouldn't count as completed for the July 1-14 sprint analysis.

Ready to get started? Export your Jira data and drop it in the `datasets/` folder! 