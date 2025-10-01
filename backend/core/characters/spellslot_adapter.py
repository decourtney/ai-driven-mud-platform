from collections import defaultdict
from backend.core.spells.spell_slots import SpellSlots


def db_rows_to_spellslots(rows: list) -> SpellSlots:
    """
    Convert a list of DB SpellSlot rows into a SpellSlots object.
    Each row should have `.level` (int) and `.used` (bool).
    """
    max_slots = defaultdict(int)
    current_slots = defaultdict(int)

    for row in rows:
        max_slots[row.level] += 1
        if not row.used:
            current_slots[row.level] += 1

    return SpellSlots(max_slots=dict(max_slots), current_slots=dict(current_slots))


def spellslots_to_db_rows(spellslots: SpellSlots, player_id: str) -> list:
    """
    Convert SpellSlots object back to DB rows for persistence.
    Creates a row per slot with correct 'used' status.
    """
    rows = []
    for level, max_count in spellslots.max_slots.items():
        current_count = spellslots.current_slots.get(level, 0)
        used_count = max_count - current_count
        # First current slots
        for _ in range(current_count):
            rows.append(SpellSlots(level=level, used=False, player_id=player_id))
        # Then used slots
        for _ in range(used_count):
            rows.append(SpellSlots(level=level, used=True, player_id=player_id))
    return rows
