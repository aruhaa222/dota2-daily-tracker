import json
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


def load_previous_snapshot(current_path):
    """Return the newest valid snapshot other than today's file."""
    candidates = sorted(
        (p for p in DATA_DIR.glob("????-??-??.json") if p != current_path),
        reverse=True,
    )
    for candidate in candidates:
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
            if isinstance(data.get("recent_matches"), list):
                return data
        except (OSError, json.JSONDecodeError):
            continue
    return None


def match_result(match):
    radiant_win = match.get("radiant_win")
    player_slot = match.get("player_slot")
    if radiant_win is None or player_slot is None:
        return "UNKNOWN"
    return "WIN" if bool(radiant_win) == (player_slot < 128) else "LOSS"


def main():
    now_dt = datetime.now(timezone.utc)
    now = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    date = now_dt.strftime("%Y-%m-%d")
    path = DATA_DIR / f"{date}.json"

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
            errors[name] = f"{type(exc).__name__}: {exc}"

    snapshot["errors"] = errors
    previous = load_previous_snapshot(path)

    current_matches = snapshot.get("recent_matches")
    previous_matches = previous.get("recent_matches", []) if previous else []
    if isinstance(current_matches, list):
        known_ids = {
            m.get("match_id") for m in previous_matches
            if isinstance(m, dict) and m.get("match_id") is not None
        }
        new_matches = [
            m for m in current_matches
            if isinstance(m, dict)
            and m.get("match_id") is not None
            and m.get("match_id") not in known_ids
        ] if previous else []
        snapshot["new_matches_since_previous_run"] = new_matches
    else:
        new_matches = []
        snapshot["new_matches_since_previous_run"] = []
    snapshot["comparison_snapshot"] = (
        previous.get("collected_at_utc") if previous else None
    )

    path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = [
        f"# Dota 2 daily report: {date}",
        "",
        f"- Account ID: {ACCOUNT_ID}",
        f"- Collected (UTC): {now}",
        f"- Compared with snapshot: {snapshot['comparison_snapshot'] or 'no previous snapshot available'}",
        f"- New matches since previous snapshot: {len(new_matches)}",
        "",
    ]

    if "win_loss" in snapshot and isinstance(snapshot["win_loss"], dict):
        wl = snapshot["win_loss"]
        wins, losses = wl.get("win"), wl.get("lose")
        if isinstance(wins, int) and isinstance(losses, int) and wins + losses:
            report += [
                "## Overall record (OpenDota)",
                "",
                f"- Wins / losses: {wins} / {losses}",
                f"- Win rate: {wins / (wins + losses) * 100:.1f}%",
                "",
            ]

    if isinstance(current_matches, list):
        report += ["## Recent matches", ""]
        for match in current_matches[:20]:
            result = match_result(match)
            duration = match.get("duration")
            duration_text = f"{duration // 60} min" if isinstance(duration, int) else "unknown"
            report.append(
                f"- Match `{match.get('match_id', '?')}`: {result}; "
                f"K/D/A {match.get('kills', '?')}/"
                f"{match.get('deaths', '?')}/"
                f"{match.get('assists', '?')}; duration {duration_text}"
            )
    else:
        report += [
            "## Recent matches",
            "",
            "Recent-match data was unavailable in this run; no new-match count was inferred.",
        ]

    if new_matches:
        report += ["", "## Newly detected matches", ""]
        for match in new_matches:
            report.append(
                f"- `{match.get('match_id')}`: {match_result(match)}; "
                f"K/D/A {match.get('kills', '?')}/"
                f"{match.get('deaths', '?')}/"
                f"{match.get('assists', '?')}"
            )

    if errors:
        report += ["", "## Data access warnings", ""]
        report += [f"- {key}: {value}" for key, value in errors.items()]

    report_text = "\n".join(report) + "\n"
    (DATA_DIR / "latest-report.md").write_text(report_text, encoding="utf-8")
    print(report_text)


if __name__ == "__main__":
    main()
