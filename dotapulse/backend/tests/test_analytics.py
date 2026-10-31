from app.analytics import coach_review, hero_summaries, is_win, summarize_matches


def sample(slot=0, radiant_win=True, hero_id=1, **extra):
    return {"player_slot": slot, "radiant_win": radiant_win, "hero_id": hero_id,
            "kills": 5, "deaths": 2, "assists": 7, "duration": 1800,
            "gold_per_min": 500, "xp_per_min": 600, **extra}


def test_radiant_and_dire_win_logic():
    assert is_win(sample(slot=0, radiant_win=True)) is True
    assert is_win(sample(slot=128, radiant_win=True)) is False
    assert is_win(sample(slot=128, radiant_win=False)) is True


def test_unknown_result_is_excluded():
    assert is_win({"player_slot": 0, "radiant_win": None}) is None
    stats = summarize_matches([sample(), {"player_slot": 0, "radiant_win": None}])
    assert stats["matches"] == 1
    assert stats["excluded_unknown_results"] == 1


def test_summary_and_hero_stats():
    matches = [sample(), sample(slot=128, radiant_win=True, hero_id=2)]
    stats = summarize_matches(matches)
    assert stats["matches"] == 2
    assert stats["wins"] == 1
    assert stats["losses"] == 1
    assert stats["win_rate"] == 50.0
    assert stats["avg_kda"] == 6.0
    assert len(hero_summaries(matches)) == 2


def test_coach_discloses_small_sample():
    result = coach_review([sample()])
    assert result["observations"][0]["type"] == "sample_size"
    assert result["limitations"]
