#!/usr/bin/env python3
"""Mark a Todoist task as completed (close).

Usage: close_todoist_task.py <task_id>
"""
import json
import sys

sys.path.insert(0, "/config/scripts")
from todoist_lib import api_request  # noqa: E402

if len(sys.argv) != 2:
    print(json.dumps({"ok": False, "error": "usage: close_todoist_task.py <task_id>"}))
    sys.exit(1)

task_id = sys.argv[1].strip()
if not task_id:
    print(json.dumps({"ok": False, "error": "empty task_id"}))
    sys.exit(1)

try:
    status, _ = api_request(f"tasks/{task_id}/close", method="POST")
    print(json.dumps({"ok": True, "status": status, "id": task_id}))
except Exception as e:
    print(json.dumps({"ok": False, "error": str(e)}))
    sys.exit(1)
