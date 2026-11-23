"""DotaPulse 6.1: evidence-first review of OpenDota match player data.
Does not parse .dem. No invented positions, spells or death timestamps.
"""
import json
import sys

def explain(player):
    if not isinstance(player, dict):
        raise ValueError("Expected one player record")
    notes = []
    deaths = player.get("deaths")
    duration = player.get("duration")
    if isinstance(deaths, (int, float)) and isinstance(duration, (int, float)) and duration > 0:
        rate = deaths * 600 / duration
        if rate > 2.5:
            notes.append({"level":"observed","metric":"deaths_per_10","value":round(rate,2),
              "finding":"Повышенная частота смертей в этом матче.",
              "possible_causes":["позиционирование","опасные перемещения","неудачные драки"],
              "verification":"Проверь каждую смерть по реплею: позицию союзников, обзор и способности врагов.",
              "exercise":"После каждой смерти отмечай минуту и более безопасное решение."})
    times = player.get("death_times")
    if isinstance(times, list) and all(isinstance(x,(int,float)) and x>=0 for x in times):
        notes.append({"level":"observed","metric":"death_times","value":times,
                      "finding":"Доступны временные отметки смертей из источника.",
                      "verification":"Сопоставь отметки с реплеем; источник может использовать секунды игрового времени."})
    if not notes:
        notes.append({"level":"insufficient_data","finding":"Недостаточно подтверждённых событий для объяснения ошибок.",
                      "verification":"Нужен подробный матч OpenDota или разобранный реплей."})
    return {"schema":"dotapulse-error-review-v1","source":"provided_player_data",
            "limitations":"Причины смертей не установлены автоматически. Возможные причины являются гипотезами.",
            "notes":notes}

if __name__ == "__main__":
    try:
        payload=json.load(sys.stdin)
        json.dump(explain(payload),sys.stdout,ensure_ascii=False,indent=2)
        print()
    except (ValueError,TypeError) as exc:
        print(str(exc),file=sys.stderr)
        sys.exit(1)
