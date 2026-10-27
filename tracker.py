
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ACCOUNT_ID = 294194492
API = f"https://api.opendota.com/api/players/{ACCOUNT_ID}"
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


def fetch(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "dota2-daily-tracker/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    endpoints = {
        "player": API,
        "recent_matches": API + "/recentMatches",
        "win_loss": API + "/wl",
        "heroes": API + "/heroes",
        "ratings": API + "/ratings",
    }

    snapshot = {"collected_at_utc": now, "account_id": ACCOUNT_ID}
    errors = {}

    for name, url in endpoints.items():
        try:
            snapshot[name] = fetch(url)
        except Exception as exc:
            errors[name] = str(exc)

    snapshot["errors"] = errors
    date = now[:10]
    path = DATA_DIR / f"{date}.json"

    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        previous = old.get("recent_matches", [])
        current = snapshot.get("recent_matches", [])
        known = {m.get("match_id") for m in previous}
        new_matches = [
            m for m in current if m.get("match_id") not in known
        ]
    else:
        new_matches = []

    snapshot["new_matches_since_previous_run"] = new_matches
    path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = [
        f"# Dota 2 daily report: {date}",
        "",
        f"- Account ID: {ACCOUNT_ID}",
        f"- Collected: {now}",
        f"- New matches since previous run: {len(new_matches)}",
        "",
        "## Recent matches",
        "",
    ]

    for match in snapshot.get("recent_matches", [])[:20]:
        result = "WIN" if match.get("radiant_win") == (
            match.get("player_slot", 0) < 128
        ) else "LOSS"
        report.append(
            f"- Match `{match.get('match_id')}`: {result}; "
            f"K/D/A {match.get('kills', '?')}/"
            f"{match.get('deaths', '?')}/"
            f"{match.get('assists', '?')}; "
            f"duration {match.get('duration', 0) // 60} min"
        )

    if errors:
        report += ["", "## Data access warnings", ""]
        report += [f"- {key}: {value}" for key, value in errors.items()]

    (DATA_DIR / "latest-report.md").write_text(
        "\n".join(report) + "\n", encoding="utf-8"
    )
    print("\n".join(report))


if __name__ == "__main__":
    main()
