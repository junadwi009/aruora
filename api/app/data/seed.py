"""
Offline fixture loader and database seeder.

Public API
----------
load_fixture(name: str) -> dict | list
    Read and parse ``fixtures/<name>.json`` from the repository root.
    The repo root is resolved as three parents up from this file:
        api/app/data/seed.py  →  api/app/data  →  api/app  →  api  →  repo root

seed_all(session_factory) -> None
    Idempotent seeder.  If the ``placement_combos`` table is empty:
      - Insert the 2 placement combos (with their listening/reading items).
      - Insert 20 GeneratedSet rows (5 per skill) with source="seed".
    If combos already exist, do nothing (idempotent).

Do NOT call seed_all from create_app here — a later task wires that up.
"""

import json
from pathlib import Path

from app.data.models import GeneratedSet, PlacementCombo, PlacementItem

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

# This file lives at:  api/app/data/seed.py
# parents[0] = api/app/data
# parents[1] = api/app
# parents[2] = api
# parents[3] = repo root   (C:/.../ielts)
_REPO_ROOT = Path(__file__).resolve().parents[3]
_FIXTURES_DIR = _REPO_ROOT / "fixtures"


def load_fixture(name: str) -> "dict | list":
    """Return the parsed contents of ``fixtures/<name>.json``."""
    path = _FIXTURES_DIR / f"{name}.json"
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------

def seed_all(session_factory) -> None:
    """
    Populate the database with offline fixture data.

    Idempotent: if placement_combos already has rows, returns immediately
    without touching any table.
    """
    from sqlalchemy.exc import IntegrityError

    with session_factory() as session:
        if session.query(PlacementCombo).count() > 0:
            return  # already seeded — nothing to do

        try:
            _seed_placement_combos(session)
            _seed_generated_sets(session)
            session.commit()
        except IntegrityError:
            # Another worker/process seeded concurrently (fresh DB + multiple
            # gunicorn workers race past the count check). That's fine.
            session.rollback()


def _seed_placement_combos(session) -> None:
    combos_data = load_fixture("placement_combos")

    for combo_dict in combos_data:
        combo = PlacementCombo(
            combo_id=combo_dict["comboId"],
            target_minutes=combo_dict["targetMinutes"],
            sections=combo_dict["sections"],
        )
        session.add(combo)

        for item_dict in combo_dict.get("items", []):
            item = PlacementItem(
                combo_id=combo_dict["comboId"],
                skill=item_dict["skill"],
                band_tag=item_dict["bandTag"],
                type=item_dict["type"],
                payload=item_dict["payload"],
                section_seconds=item_dict["sectionSeconds"],
            )
            session.add(item)


def _seed_generated_sets(session) -> None:
    sets_data = load_fixture("seed_sets")

    for skill, skill_sets in sets_data.items():
        for set_dict in skill_sets:
            generated_set = GeneratedSet(
                skill=skill,
                band=set_dict["band"],
                set_index=set_dict["setIndex"],
                payload=set_dict["payload"],
                source="seed",
            )
            session.add(generated_set)
