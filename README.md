# Library Management System

## Purpose
Book records with issue/return workflow, search and transaction report.

## Technology
Python, Flask, SQLite, HTML and CSS.

## Run
Use Python 3.10 or later. In this folder run:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000. The SQLite database is created automatically.

## Test manually
Create at least two records; search; edit; delete; restart the app and confirm records persist. Test invalid and duplicate values. For library, test issuing and returning a book. For inventory, test positive and negative stock adjustments and ensure stock cannot go below zero.

## Screenshots
Create a `screenshots` folder and save real screenshots of the running app: dashboard, add form, successful record, search, edit, and the task-specific workflow/report. Do not use mock screenshots as evidence.
