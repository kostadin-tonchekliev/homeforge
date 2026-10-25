#!/usr/bin/env python3
"""Add a task to the Todoist Shopping project in a given section.

Usage:
  add_shopping_item.py <section_id> <base64(content)> [project_id]
"""
import base64
import json
import sys

sys.path.insert(0, "/config/scripts")
from todoist_lib import api_request, get_project_id  # noqa: E402


def _load_args(argv):
    if len(argv) >= 4 and argv[2] == "--plain":
        return argv[1].strip(), " ".join(argv[3:]).strip(), None
    if len(argv) >= 3:
        section_id = argv[1].strip()
        content = base64.b64decode(argv[2]).decode("utf-8").strip()
        project_id = argv[3].strip() if len(argv) >= 4 else None
        return section_id, content, project_id
    return None, None, None


section_id, content, project_id = _load_args(sys.argv)
if content is None:
    print(json.dumps({"ok": False, "error": "usage: add_shopping_item.py <section_id> <b64content> [project_id]"}))
    sys.exit(1)
if not content:
    print(json.dumps({"ok": False, "error": "empty content"}))
    sys.exit(1)

try:
    pid = project_id or get_project_id("Shopping")
    if not pid:
        print(json.dumps({"ok": False, "error": "Shopping project not found"}))
        sys.exit(1)

    payload = {"content": content, "project_id": pid}
    if section_id and section_id.lower() not in ("none", "null", ""):
        payload["section_id"] = section_id

    _, created = api_request("tasks", method="POST", payload=payload)
    print(json.dumps({"ok": True, "id": created.get("id"), "content": created.get("content")}))
except Exception as e:
    print(json.dumps({"ok": False, "error": str(e)}))
    sys.exit(1)
