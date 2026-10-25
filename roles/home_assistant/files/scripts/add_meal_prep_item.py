#!/usr/bin/env python3
"""Add a meal to the Todoist Meal Prep project.

Usage:
  add_meal_prep_item.py <section_id> <meal_type> <base64(content)> [project_id]
"""
import base64
import json
import sys

sys.path.insert(0, "/config/scripts")
from todoist_lib import api_request, get_project_id  # noqa: E402

PROJECT_NAME = "Meal Prep"

if len(sys.argv) < 4:
    print(json.dumps({"ok": False, "error": "usage: add_meal_prep_item.py <section_id> <meal_type> <b64content> [project_id]"}))
    sys.exit(1)

section_id = sys.argv[1].strip()
meal_type = sys.argv[2].strip().lower()
content = base64.b64decode(sys.argv[3]).decode("utf-8").strip()
project_id = sys.argv[4].strip() if len(sys.argv) >= 5 else None

if not content:
    print(json.dumps({"ok": False, "error": "empty content"}))
    sys.exit(1)

if meal_type == "lunch":
    task_content = f"Lunch — {content}"
elif meal_type == "dinner":
    task_content = f"Dinner — {content}"
else:
    task_content = content

try:
    pid = project_id or get_project_id(PROJECT_NAME)
    if not pid:
        print(json.dumps({"ok": False, "error": f"{PROJECT_NAME} project not found"}))
        sys.exit(1)

    payload = {"content": task_content, "project_id": pid}
    if section_id and section_id.lower() not in ("none", "null", ""):
        payload["section_id"] = section_id

    _, created = api_request("tasks", method="POST", payload=payload)
    print(json.dumps({"ok": True, "id": created.get("id"), "content": created.get("content")}))
except Exception as e:
    print(json.dumps({"ok": False, "error": str(e)}))
    sys.exit(1)
