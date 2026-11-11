# Gemini handoff — TOEFL Command Center Web

The default branch `main` is now **web-only**. The Windows/PySide6 desktop application and its launch/build scripts have been removed.

## Runtime
This is a **Python + Streamlit** project, not a Node/React project.

Install:
```bash
python -m pip install -r requirements.txt
```

Run:
```bash
python -m streamlit run web_app.py --server.address 0.0.0.0 --server.port 8501
```

The environment must have Python 3.11+ and support a long-running Streamlit process with port 8501 forwarded to the browser. Do not run `npm install` or invent a `package.json` for this Python application. If the selected Gemini workspace only supports Node.js projects, state that limitation; use a Python runtime or port the application to the workspace's supported web stack instead.

## Main files
- `web_app.py`: Streamlit browser interface and SQLite CRUD.
- `workbook_importer.py`: existing Persian Excel workbook importer.
- `requirements.txt`: Python web dependencies.
- `README.md`: setup and deployment instructions.

## Existing pages
Dashboard, daily planner (add/edit/delete/mark complete), mock test records, notes/error analysis, Excel upload/import, and SQLite backup download.

## First tasks
1. Confirm Python version and install requirements.
2. Run `python -m py_compile web_app.py workbook_importer.py`.
3. Launch Streamlit on port 8501 and inspect the actual browser UI.
4. Test each page and all CRUD operations.
5. Import the user's real Excel workbook and compare daily rows, Persian/Jalali date conversion, weekly routine, syllabus and mock-test data with the source workbook.
6. Fix mapping and UI issues; preserve source data rather than silently dropping unrecognized cells.
7. Report exact test results and remaining limitations. Do not claim browser or workbook tests passed unless they were actually run.

## Before public deployment
There is currently no login or per-user access control. SQLite persistence depends on the host's disk. Configure persistent storage or a managed database before production/multi-user use.
