from __future__ import annotations

import json
import re
from copy import deepcopy
from hashlib import sha256
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import create_engine, delete, event, inspect, insert, select, text, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError

from .canonical_schema import (
    accounts, application_state, assignment_history, business_units, divisions,
    documents, enterprise_functions, meeting_employees, meeting_opportunities,
    meeting_stakeholders, meetings, metadata, notes, opportunities,
    opportunity_employees, opportunity_stakeholders, pods,
    stakeholder_assignments, stakeholder_employee_relationships, stakeholders,
)
from .config import settings
from .models import (
    AssignmentHistory, DocumentLink, DocumentLinkCreate, DocumentLinkUpdate,
    Meeting, MeetingCreate, MeetingUpdate, Note, NoteCreate, NoteUpdate,
    Opportunity, OpportunityCreate, OpportunityUpdate, Stakeholder,
    StakeholderCreate, StakeholderUpdate,
)
from .repository import StakeholderRepository, slug
from .account_team import demo_employee_id


ACCOUNT_ID = "morgan-stanley"


def _as_float(value):
    return None if value is None else float(value)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class PersistentStakeholderRepository(StakeholderRepository):
    """Normalized SQL authority with a one-time importer for prototype snapshots."""

    backend_name = "normalized-sql"

    def __init__(
        self,
        database_url: str,
        engine: Optional[Engine] = None,
        *,
        seed_demo_data: Optional[bool] = None,
        auto_create_schema: Optional[bool] = None,
    ) -> None:
        super().__init__(seed_data=False)
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine = engine or create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
        if self.engine.dialect.name == "sqlite":
            event.listen(self.engine, "connect", _enable_sqlite_foreign_keys)
        self._mutation_depth = 0
        self._generation = 0
        should_create = settings.auto_create_schema if auto_create_schema is None else auto_create_schema
        should_seed = settings.seed_demo_data if seed_demo_data is None else seed_demo_data
        if should_create:
            metadata.create_all(self.engine)
        elif not inspect(self.engine).has_table("stakeholders"):
            raise RuntimeError("Canonical schema is missing; run Alembic migrations before startup")
        if not self._load_normalized():
            if self._import_legacy_snapshot():
                self._persist_normalized()
            elif should_seed:
                self._seed()
                self._persist_normalized()
            else:
                raise RuntimeError("Canonical database is empty and SEED_DEMO_DATA is disabled")

    @staticmethod
    def _rows(connection: Connection, table) -> list[dict]:
        return [dict(row) for row in connection.execute(select(table)).mappings()]

    def _load_normalized(self, connection: Connection | None = None) -> bool:
        if connection is None:
            with self.engine.connect() as owned_connection:
                return self._load_normalized(owned_connection)
        if not inspect(connection).has_table("accounts"):
            return False
        stakeholder_rows = self._rows(connection, stakeholders)
        if not stakeholder_rows:
            return False
        pod_rows = self._rows(connection, pods)
        division_rows = self._rows(connection, divisions)
        unit_rows = self._rows(connection, business_units)
        assignment_rows = self._rows(connection, stakeholder_assignments)
        enterprise_rows = self._rows(connection, enterprise_functions)
        meeting_rows = self._rows(connection, meetings)
        meeting_link_rows = self._rows(connection, meeting_stakeholders)
        meeting_employee_rows = self._rows(connection, meeting_employees)
        meeting_opportunity_rows = self._rows(connection, meeting_opportunities)
        note_rows = self._rows(connection, notes)
        opportunity_rows = self._rows(connection, opportunities)
        opportunity_link_rows = self._rows(connection, opportunity_stakeholders)
        opportunity_employee_rows = self._rows(connection, opportunity_employees)
        stakeholder_employee_rows = self._rows(connection, stakeholder_employee_relationships)
        history_rows = self._rows(connection, assignment_history)
        document_rows = self._rows(connection, documents)
        state_rows = self._rows(connection, application_state)

        pod_names = {row["id"]: row["name"] for row in pod_rows}
        division_by_id = {row["id"]: row for row in division_rows}
        unit_by_id = {row["id"]: row for row in unit_rows}
        base_by_id = {row["id"]: row for row in stakeholder_rows}
        current_assignments = [row for row in assignment_rows if row["is_current"]]
        assignment_by_person = {row["stakeholder_id"]: row for row in current_assignments}
        primary_employee_by_stakeholder = {
            row["stakeholder_id"]: row["employee_id"]
            for row in stakeholder_employee_rows
            if row["is_current"] and row["is_primary"]
        }

        self.stakeholders = {}
        for assignment in current_assignments:
            base = base_by_id[assignment["stakeholder_id"]]
            division = division_by_id[assignment["division_id"]]
            unit = unit_by_id.get(assignment["business_unit_id"])
            self.stakeholders[base["id"]] = Stakeholder(
                id=base["id"], assignment_id=assignment["id"], name=base["name"], title=base["title"],
                pod=pod_names[assignment["pod_id"]], division=division["name"],
                business_unit=unit["name"] if unit else "Division Leadership",
                team_type=assignment["team_type"], organizational_role=assignment["organizational_role"],
                level=base["level"], location=base["location"], country_code=base["country_code"],
                manager_id=assignment["manager_stakeholder_id"], is_primary_technology=assignment["is_primary_technology"],
                is_buyer=assignment["is_buyer"], is_influencer=assignment["is_influencer"],
                is_budget_holder=assignment["is_budget_holder"], relationship_strength=assignment["relationship_strength"],
                capco_contingents=assignment["capco_contingents"], capco_owner=assignment["capco_owner"],
                capco_owner_employee_id=primary_employee_by_stakeholder.get(base["id"]),
                budget_amount=_as_float(assignment["budget_amount"]), biography=base["biography"],
                tags=list(assignment["tags"] or []), created_at=_utc(base["created_at"]), updated_at=_utc(base["updated_at"]),
            )

        assignments_by_unit: dict[str, list[Stakeholder]] = defaultdict(list)
        for person in self.stakeholders.values():
            unit_id = assignment_by_person[person.id]["business_unit_id"]
            if unit_id:
                assignments_by_unit[unit_id].append(person)

        self.divisions = {}
        for row in division_rows:
            if row["name"] == "Enterprise Functions":
                continue
            self.divisions[row["id"]] = {
                "id": row["id"], "pod": pod_names[row["pod_id"]], "name": row["name"],
                "color": row["color"], "head_stakeholder_id": row["head_stakeholder_id"], "unit_ids": [],
            }
        self.units = {}
        for row in sorted(unit_rows, key=lambda item: (item["division_id"], item["sort_order"])):
            division = division_by_id[row["division_id"]]
            if division["name"] == "Enterprise Functions":
                continue
            people = assignments_by_unit[row["id"]]
            business = sorted((p for p in people if p.team_type == "Business"), key=lambda p: (p.organizational_role != "Business Unit Head", p.id))
            technology = sorted((p for p in people if p.team_type == "Technology"), key=lambda p: (not p.is_primary_technology, p.id))
            primary = next((p for p in technology if p.is_primary_technology), None)
            self.units[row["id"]] = {
                "id": row["id"], "pod": pod_names[division["pod_id"]], "division": division["name"],
                "name": row["name"], "sort_order": row["sort_order"],
                "business_stakeholder_ids": [p.id for p in business],
                "technology_stakeholder_ids": [p.id for p in technology],
                "primary_technology_id": primary.id if primary else None,
                "reporting_unknown_ids": [p.id for p in business if p.manager_id is None and p.organizational_role != "Business Unit Head"],
            }
            self.divisions[row["division_id"]]["unit_ids"].append(row["id"])

        self.enterprise = defaultdict(list)
        for row in enterprise_rows:
            lead_assignment = assignment_by_person[row["lead_stakeholder_id"]]
            unit_id = lead_assignment["business_unit_id"]
            pod_name = pod_names[lead_assignment["pod_id"]]
            members = sorted(p.id for p in assignments_by_unit[unit_id] if p.id != row["lead_stakeholder_id"])
            self.enterprise[pod_name].append({
                "id": row["id"], "name": row["name"], "lead_stakeholder_id": row["lead_stakeholder_id"], "member_ids": members,
            })

        links_by_meeting: dict[str, list[str]] = defaultdict(list)
        for row in meeting_link_rows:
            links_by_meeting[row["meeting_id"]].append(row["stakeholder_id"])
        employees_by_meeting: dict[str, list[str]] = defaultdict(list)
        organizer_by_meeting: dict[str, str] = {}
        for row in meeting_employee_rows:
            employees_by_meeting[row["meeting_id"]].append(row["employee_id"])
            if row["is_organizer"]:
                organizer_by_meeting[row["meeting_id"]] = row["employee_id"]
        opportunities_by_meeting: dict[str, list[str]] = defaultdict(list)
        for row in meeting_opportunity_rows:
            opportunities_by_meeting[row["meeting_id"]].append(row["opportunity_id"])
        self.meetings = {row["id"]: Meeting(
            id=row["id"], subject=row["subject"], meeting_date=_utc(row["meeting_date"]), summary=row["summary"],
            stakeholder_ids=links_by_meeting[row["id"]], organizer=row["organizer"],
            organizer_employee_id=organizer_by_meeting.get(row["id"]),
            capco_attendee_ids=employees_by_meeting[row["id"]],
            opportunity_ids=opportunities_by_meeting[row["id"]], outcome=row["outcome"],
            next_steps=list(row["next_steps"] or []), tags=list(row["tags"] or []), created_at=_utc(row["created_at"]),
        ) for row in meeting_rows}
        self.notes = {row["id"]: Note(**{**{key: row[key] for key in Note.model_fields}, "created_at": _utc(row["created_at"]), "updated_at": _utc(row["updated_at"])}) for row in note_rows}
        links_by_opportunity: dict[str, list[str]] = defaultdict(list)
        for row in opportunity_link_rows:
            links_by_opportunity[row["opportunity_id"]].append(row["stakeholder_id"])
        primary_employee_by_opportunity = {
            row["opportunity_id"]: row["employee_id"]
            for row in opportunity_employee_rows if row["is_primary"]
        }
        self.opportunities = {row["id"]: Opportunity(
            id=row["id"], name=row["name"], description=row["description"], estimated_value=float(row["estimated_value"]),
            probability=row["probability"], stage=row["stage"], stakeholder_ids=links_by_opportunity[row["id"]],
            owner=row["owner"], owner_employee_id=primary_employee_by_opportunity.get(row["id"]),
            target_close_date=row["target_close_date"], tags=list(row["tags"] or []),
            created_at=_utc(row["created_at"]), updated_at=_utc(row["updated_at"]),
        ) for row in opportunity_rows}
        self.history = [AssignmentHistory(**{**{key: row[key] for key in AssignmentHistory.model_fields}, "effective_at": _utc(row["effective_at"])}) for row in history_rows]
        self.documents = {row["id"]: DocumentLink(**{**{key: row[key] for key in DocumentLink.model_fields}, "created_at": _utc(row["created_at"]), "updated_at": _utc(row["updated_at"])}) for row in document_rows}
        state = {row["key"]: row["value"] for row in state_rows}
        self._generation = int(state.get("repository_generation", 0) or 0)
        self.dashboard_task_statuses = state.get("dashboard_task_statuses", {})
        self.dashboard_task_records = state.get("dashboard_task_records", {})
        self.dashboard_focus = state.get("dashboard_focus", {})
        self.dashboard_critical_statuses = state.get("dashboard_critical_statuses", {})
        self._refresh_derived_fields()
        return True

    def _import_legacy_snapshot(self) -> bool:
        with self.engine.connect() as connection:
            if not inspect(connection).has_table("repository_snapshots"):
                return False
            payload = connection.execute(text("SELECT payload FROM repository_snapshots WHERE id = :id"), {"id": "stakeholder-intelligence-v1"}).scalar_one_or_none()
        if payload is None:
            return False
        if isinstance(payload, str):
            payload = json.loads(payload)
        if payload.get("version") != 1:
            raise ValueError("Unsupported legacy stakeholder snapshot version")
        self.stakeholders = {key: Stakeholder(**value) for key, value in payload["stakeholders"].items()}
        self.units = payload["units"]
        self.divisions = payload["divisions"]
        self.enterprise = defaultdict(list, payload["enterprise"])
        self.meetings = {key: Meeting(**value) for key, value in payload["meetings"].items()}
        self.notes = {key: Note(**value) for key, value in payload["notes"].items()}
        self.documents = {key: DocumentLink(**value) for key, value in payload.get("documents", {}).items()}
        self.opportunities = {key: Opportunity(**value) for key, value in payload["opportunities"].items()}
        self.history = [AssignmentHistory(**value) for value in payload["history"]]
        self.dashboard_task_statuses = payload.get("dashboard_task_statuses", {})
        self.dashboard_task_records = payload.get("dashboard_task_records", {})
        self.dashboard_focus = payload.get("dashboard_focus", {})
        self.dashboard_critical_statuses = payload.get("dashboard_critical_statuses", {})
        self._refresh_derived_fields()
        return True

    @staticmethod
    def _prune_single_key(connection: Connection, table, rows: list[dict]) -> None:
        primary_key = list(table.primary_key.columns)[0]
        keys = [row[primary_key.name] for row in rows]
        connection.execute(delete(table).where(primary_key.not_in(keys))) if keys else connection.execute(delete(table))

    @staticmethod
    def _upsert_single_key(connection: Connection, table, rows: list[dict]) -> None:
        primary_key = list(table.primary_key.columns)[0]
        existing = set(connection.execute(select(primary_key)).scalars())
        for row in rows:
            key = row[primary_key.name]
            values = {name: value for name, value in row.items() if name != primary_key.name}
            if key in existing:
                connection.execute(update(table).where(primary_key == key).values(**values))
            else:
                connection.execute(insert(table).values(**row))

    def _normalized_rows(self, connection: Connection | None = None) -> dict:
        available_employee_ids: set[str] = set()
        if connection is None:
            with self.engine.connect() as owned_connection:
                return self._normalized_rows(owned_connection)
        if inspect(connection).has_table("capco_employees"):
            available_employee_ids = set(connection.execute(text("SELECT id FROM capco_employees")).scalars())
        known_pods = sorted({row["pod"] for row in self.divisions.values()} | set(self.enterprise))
        # Pod IDs are the account's governed codes (ISG, Wealth Management, MSIM).
        # They are shared unchanged by operating and executive fact tables.
        pod_rows = [{"id": name, "account_id": ACCOUNT_ID, "name": name} for name in known_pods]
        division_rows = [{
            "id": row["id"], "pod_id": row["pod"], "name": row["name"], "color": row["color"],
            "head_stakeholder_id": row["head_stakeholder_id"],
        } for row in self.divisions.values()]
        enterprise_division_ids = {}
        division_id_by_scope = {(row["pod"], row["name"]): row["id"] for row in self.divisions.values()}
        unit_rows = [{
            "id": row["id"], "division_id": division_id_by_scope[(row["pod"], row["division"])],
            "name": row["name"], "sort_order": row["sort_order"],
        } for row in self.units.values()]
        enterprise_rows = []
        for pod_name, groups in self.enterprise.items():
            division_id = f"{slug(pod_name)}-enterprise-functions"
            enterprise_division_ids[pod_name] = division_id
            division_id_by_scope[(pod_name, "Enterprise Functions")] = division_id
            division_rows.append({"id": division_id, "pod_id": pod_name, "name": "Enterprise Functions", "color": "#5b6472", "head_stakeholder_id": None})
            for index, group in enumerate(groups):
                unit_rows.append({"id": group["id"], "division_id": division_id, "name": group["name"], "sort_order": index})
                enterprise_rows.append({"id": group["id"], "pod_id": pod_name, "name": group["name"], "lead_stakeholder_id": group["lead_stakeholder_id"]})
        unit_id_by_scope = {(row["pod"], row["division"], row["name"]): row["id"] for row in self.units.values()}
        for pod_name, groups in self.enterprise.items():
            for group in groups:
                unit_id_by_scope[(pod_name, "Enterprise Functions", group["name"])] = group["id"]

        stakeholder_rows, assignment_rows, stakeholder_employee_rows = [], [], []
        demo_prefixes = tuple(f"{slug(name)}-" for name in known_pods)
        for person in self.stakeholders.values():
            stakeholder_rows.append({
                "id": person.id, "name": person.name, "title": person.title, "level": person.level,
                "location": person.location, "country_code": person.country_code, "biography": person.biography,
                "created_at": person.created_at, "updated_at": person.updated_at,
                "source_system": "demo_seed" if person.id.startswith(demo_prefixes) else "manual",
            })
            assignment_rows.append({
                "id": person.assignment_id, "stakeholder_id": person.id, "pod_id": person.pod,
                "division_id": division_id_by_scope[(person.pod, person.division)],
                "business_unit_id": unit_id_by_scope.get((person.pod, person.division, person.business_unit)),
                "team_type": person.team_type, "organizational_role": person.organizational_role,
                "manager_stakeholder_id": person.manager_id, "is_primary_technology": person.is_primary_technology,
                "is_buyer": person.is_buyer, "is_influencer": person.is_influencer,
                "is_budget_holder": person.is_budget_holder, "relationship_strength": person.relationship_strength,
                "capco_contingents": person.capco_contingents, "capco_owner": person.capco_owner,
                "budget_amount": person.budget_amount, "tags": person.tags,
                "effective_from": date.today() if person.assignment_id.startswith("assignment-version-") else person.created_at.date(),
                "effective_to": None, "is_current": True,
            })
            owner_employee_id = person.capco_owner_employee_id or demo_employee_id(person.capco_owner)
            if owner_employee_id in available_employee_ids:
                relationship_key = sha256(f"{person.id}:{owner_employee_id}:primary".encode()).hexdigest()[:32]
                stakeholder_employee_rows.append({
                    "id": f"stakeholder-employee-{relationship_key}",
                    "stakeholder_id": person.id,
                    "employee_id": owner_employee_id,
                    "relationship_role": "Relationship owner",
                    "is_primary": True,
                    "effective_from": person.created_at.date(),
                    "effective_to": None,
                    "is_current": True,
                    "created_at": person.created_at,
                })
        meeting_rows = [{
            "id": item.id, "subject": item.subject, "meeting_date": item.meeting_date, "summary": item.summary,
            "organizer": item.organizer, "outcome": item.outcome, "next_steps": item.next_steps, "tags": item.tags,
            "created_at": item.created_at, "updated_at": item.created_at,
            "source_system": "demo_seed" if re.fullmatch(r"meeting-\d+-\d+", item.id) else "manual",
        } for item in self.meetings.values()]
        meeting_employee_rows = []
        meeting_opportunity_rows = []
        for item in self.meetings.values():
            employee_ids = [value for value in dict.fromkeys([
                *(item.capco_attendee_ids or []),
                *([item.organizer_employee_id] if item.organizer_employee_id else []),
                *([demo_employee_id(item.organizer)] if demo_employee_id(item.organizer) else []),
            ]) if value in available_employee_ids]
            for employee_id in employee_ids:
                meeting_employee_rows.append({
                    "meeting_id": item.id,
                    "employee_id": employee_id,
                    "attendee_role": "Organizer" if employee_id == (item.organizer_employee_id or demo_employee_id(item.organizer)) else "Account team",
                    "is_organizer": employee_id == (item.organizer_employee_id or demo_employee_id(item.organizer)),
                })
            meeting_opportunity_rows.extend({
                "meeting_id": item.id,
                "opportunity_id": opportunity_id,
                "relationship_type": "Discussion",
            } for opportunity_id in item.opportunity_ids)
        opportunity_rows = []
        opportunity_employee_rows = []
        for item in self.opportunities.values():
            person = next((self.stakeholders[value] for value in item.stakeholder_ids if value in self.stakeholders), None)
            if person is None:
                raise ValueError(f"Opportunity {item.id} has no valid stakeholder context")
            opportunity_rows.append({
                "id": item.id, "pod_id": person.pod,
                "business_unit_id": unit_id_by_scope.get((person.pod, person.division, person.business_unit)),
                "name": item.name, "description": item.description, "estimated_value": item.estimated_value,
                "probability": item.probability, "stage": item.stage, "owner": item.owner,
                "target_close_date": item.target_close_date, "tags": item.tags,
                "created_at": item.created_at, "updated_at": item.updated_at,
                "source_system": "demo_seed" if re.fullmatch(r"opportunity-\d+", item.id) else "manual",
            })
            owner_employee_id = item.owner_employee_id or demo_employee_id(item.owner)
            if owner_employee_id in available_employee_ids:
                opportunity_employee_rows.append({
                    "opportunity_id": item.id,
                    "employee_id": owner_employee_id,
                    "owner_role": "Owner",
                    "is_primary": True,
                })
        return {
            "accounts": [{"id": ACCOUNT_ID, "name": "Morgan Stanley"}], "pods": pod_rows,
            "divisions": division_rows, "business_units": unit_rows, "stakeholders": stakeholder_rows,
            "assignments": assignment_rows, "stakeholder_employee_relationships": stakeholder_employee_rows,
            "enterprise": enterprise_rows, "meetings": meeting_rows,
            "meeting_links": [{"meeting_id": item.id, "stakeholder_id": value} for item in self.meetings.values() for value in item.stakeholder_ids],
            "meeting_employees": meeting_employee_rows,
            "meeting_opportunities": meeting_opportunity_rows,
            "notes": [item.model_dump(mode="python") for item in self.notes.values()],
            "opportunities": opportunity_rows,
            "opportunity_links": [{"opportunity_id": item.id, "stakeholder_id": value, "role": None} for item in self.opportunities.values() for value in item.stakeholder_ids],
            "opportunity_employees": opportunity_employee_rows,
            "history": [{**item.model_dump(mode="python"), "changed_by": None} for item in self.history],
            "documents": [item.model_dump(mode="python") for item in self.documents.values()],
            "state": [
                {"key": "dashboard_task_statuses", "value": self.dashboard_task_statuses},
                {"key": "dashboard_task_records", "value": self.dashboard_task_records},
                {"key": "dashboard_focus", "value": self.dashboard_focus},
                {"key": "dashboard_critical_statuses", "value": self.dashboard_critical_statuses},
            ],
        }

    def _write_normalized(self, connection: Connection, rows: dict) -> None:
        connection.execute(delete(meeting_opportunities))
        connection.execute(delete(meeting_employees))
        connection.execute(delete(meeting_stakeholders))
        connection.execute(delete(opportunity_employees))
        connection.execute(delete(opportunity_stakeholders))
            # Remove stale records child-first so restrictive foreign keys remain useful.
        for table, key in (
            (documents, "documents"), (notes, "notes"), (assignment_history, "history"),
            (meetings, "meetings"), (opportunities, "opportunities"),
            (enterprise_functions, "enterprise"),
            (stakeholders, "stakeholders"), (business_units, "business_units"),
            (divisions, "divisions"), (pods, "pods"), (accounts, "accounts"),
            (application_state, "state"),
        ):
            self._prune_single_key(connection, table, rows[key])
            # Insert/update parent-first so a fresh database satisfies every FK.
        for table, key in (
            (accounts, "accounts"), (pods, "pods"), (divisions, "divisions"),
            (business_units, "business_units"), (stakeholders, "stakeholders"),
            (stakeholder_assignments, "assignments"), (enterprise_functions, "enterprise"),
            (meetings, "meetings"), (notes, "notes"), (opportunities, "opportunities"),
            (assignment_history, "history"), (documents, "documents"),
            (application_state, "state"),
        ):
            values = rows[key]
            if table is divisions:
                # Division heads form an intentional cycle (division -> stakeholder ->
                # assignment -> division). Break it inside the transaction, then restore.
                values = [{**row, "head_stakeholder_id": None} for row in values]
            if table is stakeholder_assignments:
                # Close the previous current assignment before inserting a new
                # version so organization changes remain historically queryable.
                for row in values:
                    connection.execute(
                        update(stakeholder_assignments).where(
                            stakeholder_assignments.c.stakeholder_id == row["stakeholder_id"],
                            stakeholder_assignments.c.is_current.is_(True),
                            stakeholder_assignments.c.id != row["id"],
                        ).values(is_current=False, effective_to=date.today())
                    )
            self._upsert_single_key(connection, table, values)
        for row in rows["divisions"]:
            connection.execute(
                update(divisions).where(divisions.c.id == row["id"]).values(head_stakeholder_id=row["head_stakeholder_id"])
            )
        desired_relationships = {row["stakeholder_id"]: row for row in rows["stakeholder_employee_relationships"]}
        current_relationships = connection.execute(
            select(stakeholder_employee_relationships).where(stakeholder_employee_relationships.c.is_current.is_(True))
        ).mappings().all()
        for current in current_relationships:
            desired = desired_relationships.get(current["stakeholder_id"])
            if desired is None or desired["employee_id"] != current["employee_id"]:
                connection.execute(
                    update(stakeholder_employee_relationships)
                    .where(stakeholder_employee_relationships.c.id == current["id"])
                    .values(is_current=False, effective_to=date.today())
                )
        for relationship in rows["stakeholder_employee_relationships"]:
            exists = connection.execute(
                select(stakeholder_employee_relationships.c.id).where(
                    stakeholder_employee_relationships.c.id == relationship["id"]
                )
            ).scalar_one_or_none()
            if exists:
                connection.execute(
                    update(stakeholder_employee_relationships)
                    .where(stakeholder_employee_relationships.c.id == relationship["id"])
                    .values(**{key: value for key, value in relationship.items() if key != "id"})
                )
            else:
                connection.execute(insert(stakeholder_employee_relationships).values(**relationship))
        if rows["meeting_links"]:
            connection.execute(insert(meeting_stakeholders), rows["meeting_links"])
        if rows["meeting_employees"]:
            connection.execute(insert(meeting_employees), rows["meeting_employees"])
        if rows["meeting_opportunities"]:
            connection.execute(insert(meeting_opportunities), rows["meeting_opportunities"])
        if rows["opportunity_links"]:
            connection.execute(insert(opportunity_stakeholders), rows["opportunity_links"])
        if rows["opportunity_employees"]:
            connection.execute(insert(opportunity_employees), rows["opportunity_employees"])

    def _persist_normalized(self) -> None:
        rows = self._normalized_rows()
        with self.engine.begin() as connection:
            self._write_normalized(connection, rows)

    @staticmethod
    def _row_key(row: dict, columns: tuple[str, ...]) -> tuple:
        return tuple(row[column] for column in columns)

    def _write_delta(self, connection: Connection, before: dict, after: dict) -> None:
        """Persist only rows changed by one repository command.

        The compatibility read model remains in memory for now, but request-time
        writes no longer prune or rebuild whole canonical tables.
        """
        specifications = {
            "accounts": (accounts, ("id",)),
            "pods": (pods, ("id",)),
            "divisions": (divisions, ("id",)),
            "business_units": (business_units, ("id",)),
            "stakeholders": (stakeholders, ("id",)),
            "assignments": (stakeholder_assignments, ("id",)),
            "stakeholder_employee_relationships": (stakeholder_employee_relationships, ("id",)),
            "enterprise": (enterprise_functions, ("id",)),
            "meetings": (meetings, ("id",)),
            "meeting_links": (meeting_stakeholders, ("meeting_id", "stakeholder_id")),
            "meeting_employees": (meeting_employees, ("meeting_id", "employee_id")),
            "meeting_opportunities": (meeting_opportunities, ("meeting_id", "opportunity_id")),
            "notes": (notes, ("id",)),
            "opportunities": (opportunities, ("id",)),
            "opportunity_links": (opportunity_stakeholders, ("opportunity_id", "stakeholder_id")),
            "opportunity_employees": (opportunity_employees, ("opportunity_id", "employee_id")),
            "history": (assignment_history, ("id",)),
            "documents": (documents, ("id",)),
            "state": (application_state, ("key",)),
        }
        before_maps = {
            name: {self._row_key(row, keys): row for row in before[name]}
            for name, (_, keys) in specifications.items()
        }
        after_maps = {
            name: {self._row_key(row, keys): row for row in after[name]}
            for name, (_, keys) in specifications.items()
        }

        # Remove changed child/link rows first. Assignment versions and history
        # are append-only; stakeholder deletion relies on their FK cascades.
        delete_order = (
            "meeting_opportunities", "meeting_employees", "meeting_links",
            "opportunity_employees", "opportunity_links", "stakeholder_employee_relationships",
            "documents", "notes", "meetings", "opportunities", "enterprise", "stakeholders", "state",
        )
        for name in delete_order:
            table, key_columns = specifications[name]
            removed = before_maps[name].keys() - after_maps[name].keys()
            for key in removed:
                condition = None
                for column_name, value in zip(key_columns, key):
                    clause = table.c[column_name] == value
                    condition = clause if condition is None else condition & clause
                connection.execute(delete(table).where(condition))

        insert_order = (
            "accounts", "pods", "divisions", "business_units", "stakeholders", "assignments",
            "enterprise", "meetings", "opportunities", "notes", "documents", "history", "state",
            "stakeholder_employee_relationships", "meeting_links", "meeting_employees",
            "opportunity_links", "opportunity_employees", "meeting_opportunities",
        )
        for name in insert_order:
            table, key_columns = specifications[name]
            old_rows, new_rows = before_maps[name], after_maps[name]
            for key, row in new_rows.items():
                if name == "assignments" and key not in old_rows:
                    connection.execute(
                        update(stakeholder_assignments).where(
                            stakeholder_assignments.c.stakeholder_id == row["stakeholder_id"],
                            stakeholder_assignments.c.is_current.is_(True),
                        ).values(is_current=False, effective_to=date.today())
                    )
                if key not in old_rows:
                    values = row
                    if name == "divisions":
                        values = {**row, "head_stakeholder_id": None}
                    connection.execute(insert(table).values(**values))
                elif row != old_rows[key]:
                    condition = None
                    for column_name, value in zip(key_columns, key):
                        clause = table.c[column_name] == value
                        condition = clause if condition is None else condition & clause
                    values = {column: value for column, value in row.items() if column not in key_columns}
                    connection.execute(update(table).where(condition).values(**values))

        # Division heads intentionally form a cycle through stakeholder
        # assignments, so restore them after all parent rows exist.
        for key, row in after_maps["divisions"].items():
            if key not in before_maps["divisions"] or row != before_maps["divisions"][key]:
                connection.execute(
                    update(divisions).where(divisions.c.id == row["id"]).values(head_stakeholder_id=row["head_stakeholder_id"])
                )

    def _lock_generation(self, connection: Connection) -> int:
        values = {"key": "repository_generation", "value": 0}
        if connection.dialect.name == "postgresql":
            connection.execute(postgresql_insert(application_state).values(**values).on_conflict_do_nothing(index_elements=["key"]))
        elif connection.dialect.name == "sqlite":
            connection.execute(sqlite_insert(application_state).values(**values).on_conflict_do_nothing(index_elements=["key"]))
        else:
            existing = connection.execute(select(application_state.c.key).where(application_state.c.key == values["key"])).scalar_one_or_none()
            if existing is None:
                connection.execute(insert(application_state).values(**values))
        statement = select(application_state.c.value).where(application_state.c.key == "repository_generation")
        if connection.dialect.name == "postgresql":
            statement = statement.with_for_update()
        return int(connection.execute(statement).scalar_one() or 0)

    def refresh_if_stale(self) -> None:
        with self.engine.connect() as connection:
            generation = connection.execute(
                select(application_state.c.value).where(application_state.c.key == "repository_generation")
            ).scalar_one_or_none()
            generation = int(generation or 0)
            if generation != self._generation:
                self._load_normalized(connection)

    def reconcile_external_identities(self) -> None:
        """Deprecated: identity repair must run as an explicit migration."""
        self._load_normalized()

    def create_meeting_transactional(self, payload: MeetingCreate, event_writer):
        """Commit the canonical meeting and its operating calendar projection atomically."""
        with self._lock:
            try:
                with self.engine.begin() as connection:
                    generation = self._lock_generation(connection)
                    self._load_normalized(connection)
                    before = deepcopy(self._normalized_rows(connection))
                    meeting = super().create_meeting(payload)
                    self._write_delta(connection, before, self._normalized_rows(connection))
                    event = event_writer(connection, meeting)
                    connection.execute(update(application_state).where(application_state.c.key == "repository_generation").values(value=generation + 1))
                    self._generation = generation + 1
                return meeting, event
            except Exception:
                self._load_normalized()
                raise

    def update_meeting_transactional(self, meeting_id: str, payload: MeetingUpdate, event_writer):
        """Update the canonical meeting and its calendar projection in one transaction."""
        with self._lock:
            try:
                with self.engine.begin() as connection:
                    generation = self._lock_generation(connection)
                    self._load_normalized(connection)
                    before = deepcopy(self._normalized_rows(connection))
                    meeting = super().update_meeting(meeting_id, payload)
                    self._write_delta(connection, before, self._normalized_rows(connection))
                    event = event_writer(connection, meeting)
                    connection.execute(update(application_state).where(application_state.c.key == "repository_generation").values(value=generation + 1))
                    self._generation = generation + 1
                return meeting, event
            except Exception:
                self._load_normalized()
                raise

    def _apply(self, operation):
        with self._lock:
            if self._mutation_depth:
                return operation()
            self._mutation_depth += 1
            try:
                with self.engine.begin() as connection:
                    generation = self._lock_generation(connection)
                    self._load_normalized(connection)
                    before = deepcopy(self._normalized_rows(connection))
                    result = operation()
                    self._write_delta(connection, before, self._normalized_rows(connection))
                    connection.execute(update(application_state).where(application_state.c.key == "repository_generation").values(value=generation + 1))
                    self._generation = generation + 1
                return result
            except Exception:
                self._load_normalized()
                raise
            finally:
                self._mutation_depth -= 1

    def create_stakeholder(self, payload: StakeholderCreate) -> Stakeholder:
        return self._apply(lambda: super(PersistentStakeholderRepository, self).create_stakeholder(payload))
    def update_stakeholder(self, stakeholder_id: str, payload: StakeholderUpdate) -> Stakeholder:
        return self._apply(lambda: super(PersistentStakeholderRepository, self).update_stakeholder(stakeholder_id, payload))
    def delete_stakeholder(self, stakeholder_id: str) -> None:
        return self._apply(lambda: super(PersistentStakeholderRepository, self).delete_stakeholder(stakeholder_id))
    def update_reporting_line(self, report_id: str, manager_id: Optional[str], reason: str) -> dict:
        def operation():
            result = super(PersistentStakeholderRepository, self).update_reporting_line(report_id, manager_id, reason)
            self.stakeholders[report_id].assignment_id = f"assignment-version-{uuid4().hex}"
            return result
        return self._apply(operation)
    def set_primary_technology(self, unit_id: str, stakeholder_id: str, reason: str) -> dict:
        def operation():
            prior = self.units[unit_id]["primary_technology_id"]
            result = super(PersistentStakeholderRepository, self).set_primary_technology(unit_id, stakeholder_id, reason)
            for changed_id in {prior, stakeholder_id}:
                if changed_id in self.stakeholders:
                    self.stakeholders[changed_id].assignment_id = f"assignment-version-{uuid4().hex}"
            return result
        return self._apply(operation)
    def create_meeting(self, payload: MeetingCreate) -> Meeting:
        return self._apply(lambda: super(PersistentStakeholderRepository, self).create_meeting(payload))
    def update_meeting(self, meeting_id: str, payload: MeetingUpdate) -> Meeting:
        return self._apply(lambda: super(PersistentStakeholderRepository, self).update_meeting(meeting_id, payload))
    def create_note(self, stakeholder_id: str, payload: NoteCreate) -> Note:
        return self._apply(lambda: super(PersistentStakeholderRepository, self).create_note(stakeholder_id, payload))
    def update_note(self, note_id: str, payload: NoteUpdate) -> Note:
        return self._apply(lambda: super(PersistentStakeholderRepository, self).update_note(note_id, payload))
    def delete_note(self, note_id: str) -> None:
        return self._apply(lambda: super(PersistentStakeholderRepository, self).delete_note(note_id))
    def create_document(self, stakeholder_id: str, payload: DocumentLinkCreate) -> DocumentLink:
        return self._apply(lambda: super(PersistentStakeholderRepository, self).create_document(stakeholder_id, payload))
    def create_meeting_document(self, meeting_id: str, payload: DocumentLinkCreate) -> DocumentLink:
        return self._apply(lambda: super(PersistentStakeholderRepository, self).create_meeting_document(meeting_id, payload))
    def update_document(self, document_id: str, payload: DocumentLinkUpdate) -> DocumentLink:
        return self._apply(lambda: super(PersistentStakeholderRepository, self).update_document(document_id, payload))
    def delete_document(self, document_id: str) -> None:
        return self._apply(lambda: super(PersistentStakeholderRepository, self).delete_document(document_id))
    def create_opportunity(self, payload: OpportunityCreate) -> Opportunity:
        return self._apply(lambda: super(PersistentStakeholderRepository, self).create_opportunity(payload))
    def update_opportunity(self, opportunity_id: str, payload: OpportunityUpdate) -> Opportunity:
        return self._apply(lambda: super(PersistentStakeholderRepository, self).update_opportunity(opportunity_id, payload))
    def update_dashboard_task_status(self, pod: str, task_id: str, status: str) -> None:
        return self._apply(lambda: super(PersistentStakeholderRepository, self).update_dashboard_task_status(pod, task_id, status))
    def save_dashboard_task(self, pod: str, task: dict) -> dict:
        return self._apply(lambda: super(PersistentStakeholderRepository, self).save_dashboard_task(pod, task))
    def save_dashboard_focus(self, pod: str, focus: list[str]) -> list[str]:
        return self._apply(lambda: super(PersistentStakeholderRepository, self).save_dashboard_focus(pod, focus))
    def update_dashboard_critical_status(self, pod: str, item_id: str, status: str) -> None:
        return self._apply(lambda: super(PersistentStakeholderRepository, self).update_dashboard_critical_status(pod, item_id, status))


def default_database_url() -> str:
    return settings.database_url


def create_repository() -> StakeholderRepository:
    if settings.repository_backend == "memory":
        if settings.environment == "production":
            raise RuntimeError("In-memory repository is not permitted in production")
        repository = StakeholderRepository(seed_data=settings.seed_demo_data)
        repository.backend_name = "memory"
        return repository
    try:
        # Application startup is always read-only. Demo population is available
        # only through `python -m backend.manage seed-demo`.
        return PersistentStakeholderRepository(settings.database_url, seed_demo_data=False)
    except (SQLAlchemyError, OSError, ValueError, RuntimeError) as error:
        if settings.require_database:
            raise RuntimeError("Database-backed stakeholder repository failed to initialize") from error
        repository = StakeholderRepository(seed_data=settings.seed_demo_data)
        repository.backend_name = "memory-fallback"
        repository.storage_warning = str(error)
        return repository
