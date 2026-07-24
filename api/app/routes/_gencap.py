"""Shared token-efficiency helpers for generation routes (Feature B)."""
from datetime import datetime, timezone

from app.errors import ApiError

GEN_CAP_CODE = "GEN_CAP_REACHED"


def today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def cap_reached(uid: int, repo, cfg) -> bool:
    if cfg.DAILY_GEN_CAP <= 0:
        return False
    return repo.gen_count_today(uid, today_utc()) >= cfg.DAILY_GEN_CAP


def note_generation(uid: int, repo) -> None:
    repo.gen_incr_today(uid, today_utc())


def serve_or_generate(skill: str, default_band: str, uid: int, repo, cfg, gateway, body) -> dict:
    """
    Pool-freeze + daily-cap policy shared by reading & listening.

    - Pool full (count_sets >= POOL_TARGET) → serve a random stored set, no LLM.
    - Under target but daily cap reached → serve from pool if any, else 429.
    - Otherwise → generate, grow the pool, count the generation, return it.
    A new band starts with an empty pool, so generation resumes on level-up.
    """
    band = (body or {}).get("band", default_band)

    if repo.count_sets(skill, band) >= cfg.POOL_TARGET:
        return repo.serve_set(skill, band)

    if cap_reached(uid, repo, cfg):
        served = repo.serve_set(skill, band) or repo.serve_any_set(skill)
        if served is not None:
            return served
        raise ApiError(GEN_CAP_CODE, "Daily generation limit reached", 429)

    out = gateway.generate("generate", skill=skill, band=band)
    repo.add_set(skill, band, out)
    note_generation(uid, repo)
    return out
