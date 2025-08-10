from __future__ import annotations

from typing import Optional


STATUS_ORDER = {"sent": 1, "delivered": 2, "read": 3}


def promote_status(current: Optional[str], new: Optional[str]) -> Optional[str]:
    if new is None:
        return current
    if current is None:
        return new
    if STATUS_ORDER.get(new, 0) > STATUS_ORDER.get(current, 0):
        return new
    return current
