from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .analytics import coach_review, compare_sessions, hero_summaries, summarize_matches
from .opendota import OpenDotaClient, OpenDotaError

app = FastAPI(
    title="DotaPulse API",
    version="0.1.0",
    description="Статистика Dota 2 и проверяемые подсказки тренера на основе OpenDota.",
)
# Local development only. Replace with the deployed frontend origin before public launch.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)
opendota = OpenDotaClient()


def account_path(account_id: int, suffix: str) -> str:
    if account_id <= 0:
        raise HTTPException(status_code=422, detail="Account ID должен быть положительным числом.")
    return f"/players/{account_id}{suffix}"


async def api_get(path: str):
    try:
        return await opendota.get(path)
    except OpenDotaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/health")
async def health():
    return {"status": "ok", "service": "dotapulse-api"}


@app.get("/api/v1/players/{account_id}/matches")
async def player_matches(account_id: int, limit: int = Query(default=50, ge=1, le=100)):
    path = account_path(account_id, f"/recentMatches")
    matches = await api_get(path)
    return {"account_id": account_id, "matches": matches[:limit], "count": min(len(matches), limit)}


@app.get("/api/v1/players/{account_id}/overview")
async def player_overview(account_id: int, limit: int = Query(default=50, ge=1, le=100)):
    profile, matches = await __import__("asyncio").gather(
        api_get(account_path(account_id, "")),
        api_get(account_path(account_id, "/recentMatches")),
    )
    selected = matches[:limit]
    return {
        "account_id": account_id,
        "profile": profile,
        "stats": summarize_matches(selected),
        "heroes": hero_summaries(selected),
        "matches": selected,
    }


@app.get("/api/v1/players/{account_id}/coach")
async def player_coach(account_id: int, limit: int = Query(default=50, ge=1, le=100)):
    matches = await api_get(account_path(account_id, "/recentMatches"))
    return {"account_id": account_id, **coach_review(matches[:limit])}


@app.get("/api/v1/players/{account_id}/progress")
async def player_progress(account_id: int, session_size: int = Query(default=10, ge=3, le=30)):
    matches = await api_get(account_path(account_id, "/recentMatches"))
    return {
        "account_id": account_id,
        **compare_sessions(matches, session_size=session_size),
    }
