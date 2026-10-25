#!/usr/bin/env python3
"""Fetch Todoist Shopping project tasks grouped by section (shop)."""
import json
import sys
import urllib.parse

sys.path.insert(0, "/config/scripts")
from todoist_lib import api_get, get_project_id, get_sections  # noqa: E402

PROJECT_NAME = "Shopping"

try:
    pid = get_project_id(PROJECT_NAME)
    if not pid:
        print(json.dumps({"count": 0, "sections": [], "project_id": None, "error": f"project {PROJECT_NAME} not found"}))
        sys.exit(0)

    section_meta = get_sections(pid)
    tasks_raw = api_get(f"tasks?project_id={urllib.parse.quote(str(pid))}") or []
except Exception as e:
    print(json.dumps({"count": 0, "sections": [], "project_id": None, "error": str(e)}))
    sys.exit(0)

# If tasks reference unknown sections, refresh section cache once.
known = {s["id"] for s in section_meta}
unknown = {
    t.get("section_id")
    for t in tasks_raw
    if t.get("section_id") and t.get("section_id") not in known
    and not (t.get("checked") or t.get("is_completed"))
}
if unknown:
    try:
        section_meta = get_sections(pid, force_refresh=True)
        known = {s["id"] for s in section_meta}
    except Exception:
        pass

tasks_by_section = {s["id"]: [] for s in section_meta}
unsectioned = []

for t in tasks_raw:
    if t.get("checked") or t.get("is_completed"):
        continue
    if t.get("parent_id"):
        continue
    item = {"id": t.get("id"), "content": t.get("content") or ""}
    sid = t.get("section_id")
    if sid in tasks_by_section:
        tasks_by_section[sid].append(item)
    else:
        unsectioned.append(item)

sections = []
for s in section_meta:
    items = tasks_by_section.get(s["id"], [])
    sections.append({"id": s["id"], "name": s["name"], "items": items, "count": len(items)})

if unsectioned:
    sections.append({"id": None, "name": "Other", "items": unsectioned, "count": len(unsectioned)})

count = sum(s["count"] for s in sections)
print(json.dumps({"count": count, "project_id": pid, "sections": sections}))
