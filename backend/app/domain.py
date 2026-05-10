from __future__ import annotations

# Volunteer roles; extend CHECK constraints in schema.sql if this list grows.
VOLUNTEER_ROLES = frozenset({"support", "oncall", "admin"})

# Product rule (current): swap offers are only between support volunteers.
SWAP_ELIGIBLE_ROLES = frozenset({"support"})

GENDERS = frozenset({"M", "F"})

# Scheduling / pairing: IL vs NA groups do not intermingle.
REGIONS = frozenset({"IL", "NA"})


def is_swap_eligible(role: str) -> bool:
    return role in SWAP_ELIGIBLE_ROLES


def same_region(a: str, b: str) -> bool:
    return a == b and a in REGIONS
