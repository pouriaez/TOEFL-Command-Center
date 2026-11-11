# Gemini Argon handoff — TOEFL Command Center Web

Continue development from this branch: `web/streamlit-version`.

## Important runtime decision
This repository is a **Python Streamlit web app**, not a Node/React app. The browser UI is served by Streamlit. Do not add a fake `package.json`, do not run `npm install`, and do not try to render the PySide6 desktop window in a browser preview.

## Start command
```bash
python -m pip install -r requirements.txt
python -m streamlit run web_app.py --server.address 0.0.0.0 --server.port 8501
```
Open the forwarded port 8501 in the browser if the environment supports Python processes and port forwarding. If this workspace only supports Node preview, explain that limitation and use a Python/Streamlit runtime or deploy to Streamlit Community Cloud.

## Files
- `web_app.py`: browser UI and SQLite operations
- `workbook_importer.py`: existing Persian Excel importer
- `requirements.txt`: web dependencies
- `requirements-desktop.txt`: desktop dependencies
- `main.py`: preserved Windows desktop application
- `README.md`: run and deployment instructions

## Current web pages
Dashboard, daily planner (CRUD + completion checkboxes), mock tests, notes/error analysis, Excel import, and SQLite backup download.

## Required next steps
1. Install requirements and run a Python syntax check on `web_app.py` and `workbook_importer.py`.
2. Launch Streamlit and test every page in a browser.
3. Test importing the actual Persian TOEFL workbook; verify the daily rows, Jalali-to-Gregorian dates, and mock scores against the source workbook.
4. Fix any import mapping issues without discarding source-sheet content.
5. Test add/edit/delete/check operations and confirm SQLite persistence across reruns.
6. Improve the responsive RTL design while keeping all labels legible.
7. Do not claim the app is fully tested until the above checks pass.

## Known limitations to address before public deployment
- No login / per-user accounts yet.
- SQLite file persistence depends on the host; configure persistent storage or move to managed PostgreSQL for a multi-user deployment.
- Validate uploaded workbook size and report import summaries clearly.
