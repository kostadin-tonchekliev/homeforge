#!/usr/bin/env python3
"""Delete all Meal Prep tasks in day sections; keep Ideas intact."""
import json
import sys
import urllib.parse

sys.path.insert(0, "/config/scripts")
from todoist_lib import api_get, api_request, get_project_id, get_sections  # noqa: E402

PROJECT_NAME = "Meal Prep"
KEEP_SECTIONS = {"Ideas"}

try:
    pid = get_project_id(PROJECT_NAME)
    if not pid:
        print(json.dumps({"ok": False, "error": f"{PROJECT_NAME} not found"}))
        sys.exit(1)

    sections = get_sections(pid)
    delete_section_ids = {
        s["id"] for s in sections if (s.get("name") or "").strip() not in KEEP_SECTIONS
    }

    tasks = api_get(f"tasks?project_id={urllib.parse.quote(str(pid))}") or []
    to_delete = [
        t for t in tasks
        if not (t.get("checked") or t.get("is_completed"))
        and t.get("section_id") in delete_section_ids
        and not t.get("parent_id")
    ]

    deleted = []
    errors = []
    for t in to_delete:
        tid = t.get("id")
        try:
            api_request(f"tasks/{tid}", method="DELETE")
            deleted.append(tid)
        except Exception as e:
            errors.append({"id": tid, "error": str(e)})

    print(json.dumps({
        "ok": len(errors) == 0,
        "deleted": len(deleted),
        "ids": deleted,
        "errors": errors,
    }))
    if errors:
        sys.exit(1)
except Exception as e:
    print(json.dumps({"ok": False, "error": str(e)}))
    sys.exit(1)
