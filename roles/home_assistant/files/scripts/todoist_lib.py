#!/usr/bin/env python3
"""Shared Todoist helpers with on-disk caching to reduce API calls.

Cache file: /config/.todoist_cache.json
- project ids by name (long TTL)
- project name map by id (for today view)
- sections by project id (medium TTL)
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CACHE_PATH = Path("/config/.todoist_cache.json")
SECRETS_PATH = Path("/config/secrets.yaml")

PROJECT_TTL_SEC = 7 * 24 * 3600
SECTIONS_TTL_SEC = 24 * 3600
PROJECT_NAMES_TTL_SEC = 24 * 3600


def token() -> str:
    with SECRETS_PATH.open() as f:
        for line in f:
            if line.startswith("todoist_token:"):
                return line.split(":", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("todoist_token missing from secrets.yaml")


def _load_cache() -> dict:
    try:
        return json.loads(CACHE_PATH.read_text())
    except Exception:
        return {}


def _save_cache(data: dict) -> None:
    tmp = CACHE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.replace(CACHE_PATH)


def api_request(path: str, *, method: str = "GET", payload: dict | None = None, timeout: int = 15):
    headers = {"Authorization": f"Bearer {token()}"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"https://api.todoist.com/api/v1/{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {err_body}") from e

    if not body:
        return status, None
    raw = json.loads(body)
    if isinstance(raw, dict) and "results" in raw:
        return status, raw["results"]
    return status, raw


def api_get(path: str, timeout: int = 15):
    _, data = api_request(path, timeout=timeout)
    return data


def invalidate_sections(project_id: str | None = None) -> None:
    cache = _load_cache()
    sections = cache.get("sections") or {}
    if project_id is None:
        cache["sections"] = {}
    else:
        sections.pop(str(project_id), None)
        cache["sections"] = sections
    _save_cache(cache)


def get_project_id(name: str, *, force_refresh: bool = False) -> str | None:
    cache = _load_cache()
    projects = cache.get("projects") or {}
    entry = projects.get(name)
    now = time.time()
    if (
        not force_refresh
        and isinstance(entry, dict)
        and entry.get("id")
        and now - float(entry.get("cached_at") or 0) < PROJECT_TTL_SEC
    ):
        return str(entry["id"])

    all_projects = api_get("projects") or []
    # Refresh whole name->id map while we're here.
    projects = {}
    names = {}
    found = None
    for p in all_projects:
        pname = p.get("name") or ""
        pid = str(p.get("id"))
        projects[pname] = {"id": pid, "cached_at": now}
        names[pid] = pname
        if pname == name:
            found = pid
    cache["projects"] = projects
    cache["project_names"] = {"cached_at": now, "map": names}
    _save_cache(cache)
    return found


def get_project_names(*, force_refresh: bool = False) -> dict:
    cache = _load_cache()
    entry = cache.get("project_names") or {}
    now = time.time()
    mapping = entry.get("map") or {}
    if (
        not force_refresh
        and mapping
        and now - float(entry.get("cached_at") or 0) < PROJECT_NAMES_TTL_SEC
    ):
        return {str(k): v for k, v in mapping.items()}

    all_projects = api_get("projects") or []
    names = {str(p.get("id")): (p.get("name") or "Todoist") for p in all_projects}
    projects = cache.get("projects") or {}
    for p in all_projects:
        pname = p.get("name") or ""
        projects[pname] = {"id": str(p.get("id")), "cached_at": now}
    cache["projects"] = projects
    cache["project_names"] = {"cached_at": now, "map": names}
    _save_cache(cache)
    return names


def get_sections(project_id: str, *, force_refresh: bool = False) -> list:
    pid = str(project_id)
    cache = _load_cache()
    sections_cache = cache.get("sections") or {}
    entry = sections_cache.get(pid) or {}
    now = time.time()
    cached_sections = entry.get("sections")
    if (
        not force_refresh
        and isinstance(cached_sections, list)
        and now - float(entry.get("cached_at") or 0) < SECTIONS_TTL_SEC
    ):
        return cached_sections

    sections = api_get(f"sections?project_id={urllib.parse.quote(pid)}") or []
    slim = [{"id": s.get("id"), "name": s.get("name") or "Section"} for s in sections]
    sections_cache[pid] = {"cached_at": now, "sections": slim}
    cache["sections"] = sections_cache
    _save_cache(cache)
    return slim
