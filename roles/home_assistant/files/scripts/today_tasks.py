#!/usr/bin/env python3
"""Fetch Todoist tasks due today or overdue (filtered query)."""
import json
import sys
import urllib.parse
from datetime import date

sys.path.insert(0, "/config/scripts")
from todoist_lib import api_get, get_project_names  # noqa: E402


try:
    projects = get_project_names()
    query = urllib.parse.quote("today | overdue", safe="")
    tasks_raw = api_get(f"tasks/filter?query={query}") or []
except Exception as e:
    print(json.dumps({
        "count": 0,
        "today_count": 0,
        "overdue_count": 0,
        "tasks": [],
        "today_and_overdue": [],
        "error": str(e),
    }))
    sys.exit(0)

today = date.today().isoformat()
combined = []
for t in tasks_raw:
    due = (t.get("due") or {}).get("date")
    if not due:
        continue
    due_date = due[:10]
    if due_date > today:
        continue
    status = "today" if due_date == today else "overdue"
    combined.append({
        "task_id": str(t.get("id") or ""),
        "content": t.get("content", ""),
        "due": due_date,
        "status": status,
        "project": projects.get(str(t.get("project_id")), "Todoist"),
    })

combined.sort(key=lambda x: (0 if x["status"] == "overdue" else 1, x["due"], x["content"].lower()))
overdue = [
    {"task_id": t["task_id"], "content": t["content"], "due": t["due"]}
    for t in combined if t["status"] == "overdue"
]
today_count = sum(1 for t in combined if t["status"] == "today")
overdue_count = len(overdue)

print(json.dumps({
    "count": overdue_count,
    "tasks": overdue,
    "today_count": today_count,
    "overdue_count": overdue_count,
    "today_and_overdue": combined,
}))
