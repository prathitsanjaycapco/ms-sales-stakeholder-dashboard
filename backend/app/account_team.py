"""Stable demo identities for the Capco account team.

Production deployments load employees from an authoritative workforce source.
Demo data uses these IDs everywhere so relationships never depend on names.
"""
from __future__ import annotations


ACCOUNT_TEAM = (
    ("capco-001", "Priya Shah", "Account Executive"),
    ("capco-002", "James Miller", "Engagement Lead"),
    ("capco-003", "Rachel Kim", "Relationship Lead"),
    ("capco-004", "Rachel Chen", "Delivery Executive"),
    ("capco-005", "Jordan Brooks", "Technology Partner"),
    ("capco-006", "Alex Morgan", "Managing Principal"),
    ("capco-007", "Chris Walker", "Commercial Lead"),
    ("capco-008", "Priya Desai", "Client Partner"),
    ("capco-009", "Amrit Rai", "Relationship Lead"),
)

ACCOUNT_TEAM_BY_ID = {employee_id: {"id": employee_id, "name": name, "role": role} for employee_id, name, role in ACCOUNT_TEAM}
ACCOUNT_TEAM_ID_BY_NAME = {name.casefold(): employee_id for employee_id, name, _ in ACCOUNT_TEAM}


def demo_employee_id(name: str | None) -> str | None:
    return ACCOUNT_TEAM_ID_BY_NAME.get(name.strip().casefold()) if name else None
