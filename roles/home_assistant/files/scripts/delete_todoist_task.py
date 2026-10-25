#!/usr/bin/env python3
"""Delete a Todoist task by id. Single API call."""
import json
import sys

sys.path.insert(0, "/config/scripts")
from todoist_lib import api_request  # noqa: E402

if len(sys.argv) != 2:
    print(json.dumps({"ok": False, "error": "usage: delete_todoist_task.py <task_id>"}))
    sys.exit(1)

task_id = sys.argv[1].strip()
if not task_id:
    print(json.dumps({"ok": False, "error": "empty task_id"}))
    sys.exit(1)

try:
    status, _ = api_request(f"tasks/{task_id}", method="DELETE")
    print(json.dumps({"ok": True, "status": status}))
except Exception as e:
    print(json.dumps({"ok": False, "error": str(e)}))
    sys.exit(1)
