#!/usr/bin/env python3
"""Fetch Todoist Meal Prep project as a weekly planner payload."""
import json
import re
import sys
import urllib.parse

sys.path.insert(0, "/config/scripts")
from todoist_lib import api_get, get_project_id, get_sections  # noqa: E402

PROJECT_NAME = "Meal Prep"
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MEAL_RE = re.compile(r"^(lunch|dinner)\s*[—\-–:]\s*(.+)$", re.IGNORECASE)


def classify(content: str):
    text = (content or "").strip()
    m = MEAL_RE.match(text)
    if not m:
        return None, text
    return m.group(1).lower(), m.group(2).strip()


try:
    pid = get_project_id(PROJECT_NAME)
    if not pid:
        print(json.dumps({
            "count": 0, "days": [], "ideas": None, "project_id": None,
            "error": f"project {PROJECT_NAME} not found",
        }))
        sys.exit(0)

    sections_raw = get_sections(pid)
    tasks_raw = api_get(f"tasks?project_id={urllib.parse.quote(str(pid))}") or []
except Exception as e:
    print(json.dumps({"count": 0, "days": [], "ideas": None, "project_id": None, "error": str(e)}))
    sys.exit(0)

by_name = {(s.get("name") or "").strip(): s for s in sections_raw}
tasks_by_section = {}
for t in tasks_raw:
    if t.get("checked") or t.get("is_completed"):
        continue
    if t.get("parent_id"):
        continue
    sid = t.get("section_id")
    tasks_by_section.setdefault(sid, []).append(t)

days = []
count = 0
for day_name in DAY_ORDER:
    sec = by_name.get(day_name)
    if not sec:
        days.append({
            "id": None, "name": day_name,
            "lunch": [], "dinner": [], "other": [], "count": 0,
        })
        continue
    lunch, dinner, other = [], [], []
    for t in tasks_by_section.get(sec.get("id"), []):
        raw = t.get("content") or ""
        meal, label = classify(raw)
        item = {"id": t.get("id"), "content": label, "raw": raw, "meal": meal}
        if meal == "lunch":
            lunch.append(item)
        elif meal == "dinner":
            dinner.append(item)
        else:
            other.append(item)
    n = len(lunch) + len(dinner) + len(other)
    count += n
    days.append({
        "id": sec.get("id"),
        "name": day_name,
        "lunch": lunch,
        "dinner": dinner,
        "other": other,
        "count": n,
    })

ideas = None
ideas_sec = by_name.get("Ideas")
if ideas_sec:
    items = []
    for t in tasks_by_section.get(ideas_sec.get("id"), []):
        raw = t.get("content") or ""
        items.append({"id": t.get("id"), "content": raw, "raw": raw})
    count += len(items)
    ideas = {
        "id": ideas_sec.get("id"),
        "name": "Ideas",
        "items": items,
        "count": len(items),
    }

print(json.dumps({"count": count, "project_id": pid, "days": days, "ideas": ideas}))
