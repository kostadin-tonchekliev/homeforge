#!/usr/bin/env python3
import json, urllib.request, sys
from datetime import date

with open("/config/secrets.yaml") as f:
    for line in f:
        if line.startswith("todoist_token:"):
            token = line.split(":", 1)[1].strip().strip(chr(34)).strip(chr(39))
            break

req = urllib.request.Request(
    "https://api.todoist.com/api/v1/tasks",
    headers={"Authorization": f"Bearer {token}"}
)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = json.loads(resp.read())
except Exception as e:
    print(json.dumps({"count": 0, "tasks": [], "error": str(e)}))
    sys.exit(0)

tasks = raw.get("results", raw) if isinstance(raw, dict) else raw
today = date.today().isoformat()

overdue = [
    {"content": t["content"], "due": t["due"]["date"]}
    for t in tasks
    if t.get("due") and t["due"].get("date", "") < today
]
overdue.sort(key=lambda x: x["due"])

print(json.dumps({"count": len(overdue), "tasks": overdue}))
