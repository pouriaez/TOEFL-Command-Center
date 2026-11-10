# TOEFL Command Center

A Persian RTL desktop study planner for the 2026 TOEFL preparation workflow.

## Planned stack
- Python 3.11+
- PySide6 desktop UI
- SQLite local persistence
- pandas/openpyxl for workbook import and Excel export
- matplotlib for progress charts
- ReportLab for PDF export

## Run
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python main.py
```

The workbook importer maps the daily plan, weekly routine, weekly syllabus, and mock-test score sheets. Import your study-plan workbook from **Settings → Import workbook**.
