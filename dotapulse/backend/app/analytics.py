"""Deterministic analytics based only on fields returned by OpenDota."""
from collections import defaultdict
from statistics import mean


def is_win(match: dict) -> bool | None:
    """Return the player's result, or None when the slot/result is unavailable."""
    slot = match.get("player_slot")
    radiant_win = match.get("radiant_win")
    if not isinstance(slot, int) or not isinstance(radiant_win, bool):
        return None
    player_is_radiant = slot < 128
    return radiant_win if player_is_radiant else not radiant_win


def summarize_matches(matches: list[dict]) -> dict:
    played = [m for m in matches if is_win(m) is not None]
    wins = sum(1 for m in played if is_win(m))
    losses = len(played) - wins
    kills = sum(int(m.get("kills") or 0) for m in played)
    deaths = sum(int(m.get("deaths") or 0) for m in played)
    assists = sum(int(m.get("assists") or 0) for m in played)
    duration_values = [m["duration"] for m in played if isinstance(m.get("duration"), (int, float)) and m["duration"] > 0]
    gpm_values = [m["gold_per_min"] for m in played if isinstance(m.get("gold_per_min"), (int, float)) and m["gold_per_min"] > 0]
    xpm_values = [m["xp_per_min"] for m in played if isinstance(m.get("xp_per_min"), (int, float)) and m["xp_per_min"] > 0]
    return {
        "matches": len(played),
        "excluded_unknown_results": len(matches) - len(played),
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / len(played) * 100, 1) if played else None,
        "avg_kills": round(kills / len(played), 2) if played else None,
        "avg_deaths": round(deaths / len(played), 2) if played else None,
        "avg_assists": round(assists / len(played), 2) if played else None,
        "avg_kda": round((kills + assists) / max(deaths, 1), 2) if played else None,
        "avg_duration_min": round(mean(duration_values) / 60, 1) if duration_values else None,
        "avg_gpm": round(mean(gpm_values), 1) if gpm_values else None,
        "avg_xpm": round(mean(xpm_values), 1) if xpm_values else None,
    }


def hero_summaries(matches: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for match in matches:
        result = is_win(match)
        hero_id = match.get("hero_id")
        if result is not None and isinstance(hero_id, int):
            grouped[hero_id].append(result)
    rows = []
    for hero_id, results in grouped.items():
        wins = sum(results)
        rows.append({
            "hero_id": hero_id,
            "matches": len(results),
            "wins": wins,
            "losses": len(results) - wins,
            "win_rate": round(wins / len(results) * 100, 1),
        })
    return sorted(rows, key=lambda row: (-row["matches"], row["hero_id"]))


def coach_review(matches: list[dict]) -> dict:
    stats = summarize_matches(matches)
    observations = []
    n = stats["matches"]
    if n < 5:
        observations.append({
            "type": "sample_size",
            "message": "Пока мало матчей для устойчивых выводов. Собери хотя бы 5 игр, лучше 10–20.",
            "evidence": {"matches": n},
            "confidence": "low",
        })
    if n >= 5 and stats["avg_deaths"] is not None and stats["avg_deaths"] >= 8:
        observations.append({
            "type": "deaths",
            "message": "Среднее число смертей повышено. После игры проверь 2–3 смерти до 15-й минуты и оцени, можно ли было отойти раньше.",
            "evidence": {"avg_deaths": stats["avg_deaths"], "matches": n},
            "confidence": "medium",
        })
    if n >= 10 and stats["win_rate"] is not None and stats["win_rate"] < 45:
        observations.append({
            "type": "win_rate",
            "message": "На этой выборке винрейт ниже 45%. Не делай вывод по одной серии: сравни результаты по героям и повторяющимся метрикам.",
            "evidence": {"win_rate": stats["win_rate"], "matches": n},
            "confidence": "medium",
        })
    if n >= 5 and stats["avg_kda"] is not None and stats["avg_kda"] < 2:
        observations.append({
            "type": "kda",
            "message": "Средний KDA ниже 2. Проверь, не продолжаешь ли драку после потери ключевых способностей или преимущества по позициям.",
            "evidence": {"avg_kda": stats["avg_kda"], "matches": n},
            "confidence": "low",
        })
    if not observations:
        observations.append({
            "type": "baseline",
            "message": "Явного сигнала по базовым метрикам пока нет. Для более полезного разбора нужна большая выборка и данные отдельных матчей.",
            "evidence": {"matches": n},
            "confidence": "low",
        })
    return {
        "summary": stats,
        "observations": observations,
        "next_session_plan": [
            "Выбери 1–2 комфортных героя и не меняй пул без причины.",
            "После каждой игры отметь одну повторяющуюся ошибку, а не пытайся исправить всё сразу.",
            "Сравни следующую серию из 5–10 матчей с этой выборкой.",
        ],
        "limitations": [
            "Это статистические подсказки по доступным матчевым полям, а не анализ реплея.",
            "Метрики сами по себе не доказывают причину победы или поражения.",
            "Результаты зависят от размера и состава выборки.",
        ],
    }
