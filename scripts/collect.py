#!/usr/bin/env python3
"""DotaPulse: collect verified OpenDota snapshots using only Python stdlib."""
import datetime as dt
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

ACCOUNT_ID = 294194492
ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
API = f"https://api.opendota.com/api/players/{ACCOUNT_ID}"
HEADERS = {"User-Agent": "DotaPulse-Coach/3.3 (+https://github.com/aruhaa222/dota2-daily-tracker)", "Accept": "application/json"}
KEY = os.environ.get("OPENDOTA_API_KEY", "").strip()


def fetch(path, retries=3):
    url = API + path + (("&" if "?" in path else "?") + "api_key=" + KEY if KEY else "")
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=25) as resp:
                payload = json.load(resp)
            return payload
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"OpenDota request failed for {path}: {last_error}")


def read_previous():
    path = DATA / "latest.json"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, value):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def main():
    previous = read_previous()
    # These endpoints are mandatory: on error, do not overwrite last known-good data.
    player = fetch("")
    recent = fetch("/recentMatches")
    wl = fetch("/wl")
    if not isinstance(player, dict) or not isinstance(recent, list) or not isinstance(wl, dict):
        raise RuntimeError("OpenDota returned an unexpected payload type")
    if not isinstance(player.get("profile"), dict) or player["profile"].get("account_id") != ACCOUNT_ID:
        raise RuntimeError("OpenDota account mismatch; refusing to publish")
    if not isinstance(wl.get("win"), int) or not isinstance(wl.get("lose"), int):
        raise RuntimeError("OpenDota win/loss fields invalid")
    if not all(isinstance(m, dict) and isinstance(m.get("match_id"), int) for m in recent):
        raise RuntimeError("OpenDota recent match records invalid")
    old_ids = {int(m["match_id"]) for m in previous.get("recent_matches", []) if isinstance(m, dict) and m.get("match_id") is not None}
    new_ids = [m["match_id"] for m in recent if m["match_id"] not in old_ids]
    if not old_ids and previous:
        raise RuntimeError("Previous snapshot has no match IDs; refusing to label matches as new")
    errors = {}
    optional = {}
    for field, path in (("heroes", "/heroes"), ("ratings", "/ratings")):
        try:
            optional[field] = fetch(path)
        except RuntimeError as exc:
            errors[field] = str(exc)
            optional[field] = previous.get(field, [])
    now = dt.datetime.now(dt.timezone.utc)
    stamp = now.isoformat(timespec="seconds").replace("+00:00", "Z")
    snapshot = {
        "collected_at_utc": stamp,
        "account_id": ACCOUNT_ID,
        "player": player,
        "recent_matches": recent,
        "win_loss": wl,
        "heroes": optional["heroes"],
        "ratings": optional["ratings"],
        "errors": errors,
        "new_matches_since_previous_run": new_ids,
        "comparison_snapshot": previous.get("collected_at_utc"),
        "comparison_note": "Only IDs absent from the previous recent_matches list are marked new; older matches beyond the API window cannot be detected."
    }
    DATA.mkdir(exist_ok=True)
    archive_path = DATA / "match-history.json"
    archive = []
    if archive_path.exists():
        with archive_path.open(encoding="utf-8") as fh:
            stored = json.load(fh)
        if not isinstance(stored, list):
            raise RuntimeError("Existing match archive is not a list; refusing to overwrite")
        archive = stored
    by_id = {}
    for item in archive + recent:
        if isinstance(item, dict) and isinstance(item.get("match_id"), int):
            by_id[item["match_id"]] = item
    archive = sorted(by_id.values(), key=lambda m: m.get("start_time") or 0, reverse=True)
    # Keep a bounded history to limit repository growth.
    archive = archive[:1000]
    dated = DATA / (now.date().isoformat() + ".json")
    write_json(dated, snapshot)
    write_json(DATA / "latest.json", snapshot)
    write_json(archive_path, archive)
    print(f"Snapshot {stamp}: {len(recent)} recent matches, {len(new_ids)} newly seen IDs, {len(archive)} archived matches, {len(errors)} optional API errors")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"COLLECTION FAILED; previous data preserved: {exc}", file=sys.stderr)
        sys.exit(1)
