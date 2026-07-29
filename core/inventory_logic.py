
"""
INVENTORY_LOGIC.PY - Structured inventory processing domain logic.

This module contains pure inventory transformation logic and uses repository
abstractions for persistence.
"""

from typing import Any, Dict

from core.llm_response import LLMResponse
from repositories.inventory_repository import InventoryRepository


InventoryState = Dict[str, Any]
InventoryDelta = Dict[str, int]


def apply_inventory_changes(
    current: InventoryState,
    gold_delta: float,
    item_deltas: InventoryDelta,
    ammo_deltas: InventoryDelta,
) -> InventoryState:
    """
    Applies inventory deltas to the current inventory state.

    Args:
        current: Current persisted inventory state.
        gold_delta: Gold amount to add or subtract.
        item_deltas: Item quantity deltas keyed by item name.
        ammo_deltas: Ammunition quantity deltas keyed by ammo type.

    Returns:
        A new updated inventory dictionary.
    """
    updated: InventoryState = {
        "gold": float(current.get("gold", 0.0)),
        "items": dict(current.get("items", {})),
        "ammo": dict(current.get("ammo", {})),
    }

    updated["gold"] += float(gold_delta)
    updated["items"] = _apply_named_deltas(updated["items"], item_deltas)
    updated["ammo"] = _apply_named_deltas(updated["ammo"], ammo_deltas)

    return updated


def process_structured_inventory_update(
    channel_id: str,
    player_id: str,
    response: LLMResponse,
    inventory_repo: InventoryRepository,
) -> None:
    """
    Applies structured inventory changes emitted by the LLM.

    Args:
        channel_id: Discord channel identifier.
        player_id: Discord player identifier.
        response: Normalized LLM response object.
        inventory_repo: Repository abstraction for inventory persistence.
    """
    update = response.inventory_update

    has_change = (
        float(update.gold) != 0.0
        or bool(update.items)
        or bool(update.ammo)
    )

    if not has_change:
        return

    current = inventory_repo.get_inventory(channel_id, player_id)
    updated = apply_inventory_changes(
        current=current,
        gold_delta=update.gold,
        item_deltas=update.items,
        ammo_deltas=update.ammo,
    )
    inventory_repo.save_inventory(channel_id, player_id, updated)


def _apply_named_deltas(
    current_values: Dict[str, Any],
    deltas: InventoryDelta,
) -> Dict[str, int]:
    """
    Applies named integer deltas to an item/ammo dictionary and removes entries
    whose final value is zero or negative.
    """
    updated: Dict[str, int] = {
        str(name): int(quantity)
        for name, quantity in current_values.items()
        if _safe_int(quantity) > 0
    }

    for name, delta in deltas.items():
        normalized_name = str(name)
        current_value = updated.get(normalized_name, 0)
        new_value = current_value + int(delta)

        if new_value > 0:
            updated[normalized_name] = new_value
        elif normalized_name in updated:
            del updated[normalized_name]

    return updated


def _safe_int(value: Any) -> int:
    """
    Converts arbitrary values to int safely for normalization.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0

