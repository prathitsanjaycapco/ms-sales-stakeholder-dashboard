from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    and_,
    bindparam,
    delete,
    func,
    insert,
    inspect,
    select,
    text,
    update,
)
from sqlalchemy.engine import Engine

from .repository import NotFoundError, POD_STRUCTURE, slug
from .models import MeetingUpdate
from .account_team import ACCOUNT_TEAM, demo_employee_id


pod_metadata = MetaData()

pod_events = Table(
    "pod_events",
    pod_metadata,
    Column("id", String(120), primary_key=True),
    Column("pod_id", String(80), nullable=False),
    Column("event_type", String(30), nullable=False),
    Column("title", String(240), nullable=False),
    Column("start_at", DateTime(timezone=True), nullable=False),
    Column("end_at", DateTime(timezone=True), nullable=False),
    Column("all_day", Boolean, nullable=False, default=False),
    Column("stakeholder_id", String(180)),
    Column("opportunity_id", String(180)),
    Column("source_meeting_id", String(180)),
    Column("importance", String(20), nullable=False, default="Medium"),
    Column("status", String(30), nullable=False, default="Scheduled"),
    Column("business_unit", String(160), nullable=False, default="Account"),
    Column("is_client", Boolean, nullable=False, default=True),
    Column("prep_required", Boolean, nullable=False, default=False),
    Column("previous_engagement", Text, nullable=False, default=""),
    Column("open_actions", JSON, nullable=False, default=list),
    Column("discussion_topics", JSON, nullable=False, default=list),
    Column("tags", JSON, nullable=False, default=list),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
Index("idx_pod_events_period", pod_events.c.pod_id, pod_events.c.start_at)

pod_event_attendees = Table(
    "pod_event_attendees",
    pod_metadata,
    Column("id", String(160), primary_key=True),
    Column("event_id", String(120), nullable=False),
    Column("employee_id", String(120)),
    Column("attendee_name", String(160), nullable=False),
    Column("attendee_role", String(120), nullable=False, default="Account team"),
    Column("is_lead", Boolean, nullable=False, default=False),
)
Index("idx_pod_event_attendees_event", pod_event_attendees.c.event_id)

pod_tasks = Table(
    "pod_tasks",
    pod_metadata,
    Column("id", String(120), primary_key=True),
    Column("pod_id", String(80), nullable=False),
    Column("title", String(240), nullable=False),
    Column("description", Text, nullable=False, default=""),
    Column("owner_id", String(160)),
    Column("owner_employee_id", String(120)),
    Column("priority", String(20), nullable=False, default="Medium"),
    Column("status", String(30), nullable=False, default="Open"),
    Column("due_date", Date),
    Column("completed_at", DateTime(timezone=True)),
    Column("stakeholder_id", String(180)),
    Column("meeting_id", String(180)),
    Column("opportunity_id", String(180)),
    Column("critical_item_id", String(180)),
    Column("tags", JSON, nullable=False, default=list),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
Index("idx_pod_tasks_period", pod_tasks.c.pod_id, pod_tasks.c.due_date, pod_tasks.c.status)

pod_critical_items = Table(
    "pod_critical_items",
    pod_metadata,
    Column("id", String(120), primary_key=True),
    Column("pod_id", String(80), nullable=False),
    Column("item_type", String(100), nullable=False),
    Column("severity", String(20), nullable=False),
    Column("title", String(240), nullable=False),
    Column("description", Text, nullable=False, default=""),
    Column("owner_id", String(160)),
    Column("owner_employee_id", String(120)),
    Column("status", String(30), nullable=False, default="Open"),
    Column("due_date", Date),
    Column("stakeholder_id", String(180)),
    Column("opportunity_id", String(180)),
    Column("engagement_id", String(180)),
    Column("tags", JSON, nullable=False, default=list),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("resolved_at", DateTime(timezone=True)),
)
Index("idx_pod_critical_active", pod_critical_items.c.pod_id, pod_critical_items.c.status, pod_critical_items.c.severity)

pod_milestones = Table(
    "pod_milestones",
    pod_metadata,
    Column("id", String(120), primary_key=True),
    Column("pod_id", String(80), nullable=False),
    Column("milestone_type", String(100), nullable=False),
    Column("title", String(240), nullable=False),
    Column("milestone_date", Date, nullable=False),
    Column("description", Text, nullable=False, default=""),
    Column("owner_id", String(160)),
    Column("owner_employee_id", String(120)),
    Column("stakeholder_id", String(180)),
    Column("opportunity_id", String(180)),
    Column("engagement_id", String(180)),
    Column("tags", JSON, nullable=False, default=list),
)
Index("idx_pod_milestones_date", pod_milestones.c.pod_id, pod_milestones.c.milestone_date)

pod_focus = Table(
    "pod_focus",
    pod_metadata,
    Column("id", String(120), primary_key=True),
    Column("pod_id", String(80), nullable=False),
    Column("period_type", String(20), nullable=False),
    Column("period_start", Date, nullable=False),
    Column("content", JSON, nullable=False, default=list),
    Column("created_by", String(160)),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("pod_id", "period_type", "period_start", name="uq_pod_focus_period"),
)

pod_relationship_signals = Table(
    "pod_relationship_signals",
    pod_metadata,
    Column("id", String(120), primary_key=True),
    Column("pod_id", String(80), nullable=False),
    Column("stakeholder_id", String(180), nullable=False),
    Column("signal_type", String(80), nullable=False),
    Column("days_since_contact", Integer, nullable=False),
    Column("importance", String(20), nullable=False),
    Column("signal", Text, nullable=False),
    Column("status", String(30), nullable=False, default="Open"),
    Column("observed_at", DateTime(timezone=True), nullable=False),
)
Index("idx_pod_relationship_status", pod_relationship_signals.c.pod_id, pod_relationship_signals.c.status)

pod_change_events = Table(
    "pod_change_events",
    pod_metadata,
    Column("id", String(120), primary_key=True),
    Column("pod_id", String(80), nullable=False),
    Column("event_date", Date, nullable=False),
    Column("kind", String(30), nullable=False),
    Column("headline", Text, nullable=False),
    Column("detail", Text, nullable=False),
    Column("stakeholder_id", String(180)),
    Column("opportunity_id", String(180)),
)
Index("idx_pod_changes_period", pod_change_events.c.pod_id, pod_change_events.c.event_date)

pod_health_metrics = Table(
    "pod_health_metrics",
    pod_metadata,
    Column("id", String(120), primary_key=True),
    Column("pod_id", String(80), nullable=False),
    Column("label", String(120), nullable=False),
    Column("metric_value", Integer, nullable=False),
    Column("status", String(30), nullable=False),
    Column("detail", Text, nullable=False),
    Column("sort_order", Integer, nullable=False, default=0),
    Column("as_of_date", Date, nullable=False),
)

pod_opportunity_contexts = Table(
    "pod_opportunity_contexts",
    pod_metadata,
    Column("opportunity_id", String(180), primary_key=True),
    Column("pod_id", String(80), nullable=False),
    Column("latest_movement", Text, nullable=False),
    Column("commercial_context", Text, nullable=False),
    Column("recommended_next_step", Text, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
Index("idx_pod_opportunity_context", pod_opportunity_contexts.c.pod_id)

pod_seed_registry = Table(
    "pod_seed_registry",
    pod_metadata,
    Column("id", String(80), primary_key=True),
    Column("seeded_at", DateTime(timezone=True), nullable=False),
    Column("row_counts", JSON, nullable=False),
)


CAPCO_TEAM = [(name, role) for _, name, role in ACCOUNT_TEAM]

EVENT_THEMES = [
    ("Executive transformation checkpoint", "client"),
    ("AI-enabled workflow discovery", "workshop"),
    ("Platform modernization roadmap", "client"),
    ("Risk analytics solution review", "workshop"),
    ("Commercial proposal working session", "client"),
    ("Delivery recovery checkpoint", "critical"),
    ("Data governance operating model", "workshop"),
    ("Architecture decision forum", "client"),
    ("Account team pursuit review", "internal"),
    ("RFP response checkpoint", "deadline"),
    ("Operating model design session", "workshop"),
    ("Executive sponsor alignment", "client"),
]

TASK_TITLES = [
    "Send revised transformation proposal",
    "Confirm steering committee recovery plan",
    "Arrange executive sponsor introduction",
    "Validate workshop attendee list",
    "Prepare fixed income value case",
    "Resolve data architect coverage gap",
    "Share operations discovery notes",
    "Complete RFP pricing review",
    "Draft decision-path stakeholder map",
    "Confirm procurement approval sequence",
    "Publish delivery dependency log",
    "Schedule architecture deep dive",
    "Update weighted pipeline forecast",
    "Prepare QBR account narrative",
    "Close outstanding security questions",
    "Align resourcing plan with demand",
    "Document client success measures",
    "Confirm next executive commitment",
    "Review commercial assumptions",
    "Share capability case studies",
    "Reconcile open meeting actions",
    "Prepare negotiation position",
    "Confirm solution ownership model",
    "Escalate unresolved milestone risk",
]

CRITICAL_TEMPLATES = [
    ("CLIENT ESCALATION", "RED", "Delivery milestone at risk", "A client commitment is trending late and needs an agreed recovery path."),
    ("COMMERCIAL DEADLINE", "RED", "Proposal approval window closing", "Pricing, scope and approval owners must align before the client deadline."),
    ("STAFFING RISK", "AMBER", "Specialist coverage gap", "A priority workstream is missing confirmed senior specialist capacity."),
    ("RELATIONSHIP RISK", "AMBER", "Executive sponsor coverage is thin", "The decision maker has no confirmed Capco touchpoint in the next two weeks."),
    ("DELIVERY DEPENDENCY", "AMBER", "Architecture decision remains open", "The unresolved platform decision blocks downstream estimation and mobilization."),
    ("PROCUREMENT", "AMBER", "Procurement path is not confirmed", "Commercial owners and approval gates require validation before negotiation."),
    ("DATA QUALITY", "GREEN", "Discovery evidence needs validation", "Source-system volumes and control requirements need client confirmation."),
    ("GOVERNANCE", "GREEN", "Working-group cadence not agreed", "Owners need to establish a weekly decision and escalation rhythm."),
]

CHANGE_TEMPLATES = [
    ("PIPELINE", "Probability increased after sponsor confirmed funding"),
    ("RELATIONSHIP", "New executive stakeholder added to the decision group"),
    ("DELIVERY", "Recovery plan accepted with a revised milestone sequence"),
    ("MEETING", "Client requested a deeper architecture working session"),
    ("PIPELINE", "Proposal value updated after scope validation"),
    ("RELATIONSHIP", "Coverage owner changed following account review"),
    ("RISK", "A staffing dependency moved into the critical path"),
    ("COMMERCIAL", "Procurement requested a revised pricing structure"),
]


def _eastern_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("America/New_York"))
    return value.isoformat()


class PodOperatingStore:
    """Normalized SQL source for the Pod View operating cockpit."""

    seed_id = "pod-operating-cockpit-v2"

    def __init__(self, engine: Engine, repository, *, seed_demo_data: bool = True, auto_create_schema: bool = True) -> None:
        self.engine = engine
        self.repository = repository
        if auto_create_schema:
            pod_metadata.create_all(self.engine)
        elif not inspect(self.engine).has_table("pod_events"):
            raise RuntimeError("Pod schema is missing; run Alembic migrations before startup")
        self._validate_schema()
        if seed_demo_data:
            self._seed_if_needed()
        self._normalize_attendee_names()
        self._reconcile_employee_identities()

    def _validate_pod(self, pod: str) -> None:
        if pod not in POD_STRUCTURE and pod != "All":
            raise NotFoundError("Pod not found")

    def _employee_names(self, employee_ids: list[str]) -> dict[str, str]:
        unique_ids = list(dict.fromkeys(value for value in employee_ids if value))
        if not unique_ids or not inspect(self.engine).has_table("capco_employees"):
            return {}
        statement = text("SELECT id, name FROM capco_employees WHERE id IN :employee_ids").bindparams(
            bindparam("employee_ids", expanding=True)
        )
        with self.engine.connect() as connection:
            return dict(connection.execute(statement, {"employee_ids": unique_ids}).all())

    @staticmethod
    def _tags(*groups) -> list[str]:
        values: dict[str, str] = {}
        for group in groups:
            for value in group or []:
                clean = str(value).strip()
                if clean:
                    values.setdefault(clean.casefold(), clean)
        return sorted(values.values(), key=str.casefold)

    @staticmethod
    def _semantic_tags(*text_values) -> list[str]:
        text = " ".join(str(value or "") for value in text_values).casefold()
        rules = {
            "AI": (" ai ", "ai-", "artificial intelligence", "machine learning"),
            "Data": ("data", "analytics"),
            "Risk": ("risk", "security", "control", "governance"),
            "Technology": ("technology", "platform", "cloud", "architecture"),
            "Delivery": ("delivery", "staff", "resource", "recovery", "milestone"),
            "Commercial": ("commercial", "proposal", "pricing", "procurement", "rfp", "negotiat"),
        }
        matches = [tag for tag, needles in rules.items() if any(needle in f" {text} " for needle in needles)]
        return matches or ["Account"]

    def _validate_schema(self) -> None:
        required_columns = {
            pod_events: {"tags"},
            pod_event_attendees: {"employee_id"},
            pod_tasks: {"tags", "owner_employee_id"},
            pod_critical_items: {"tags", "owner_employee_id"},
            pod_milestones: {"tags", "owner_employee_id"},
        }
        schema = inspect(self.engine)
        for table, expected in required_columns.items():
            columns = {column["name"] for column in schema.get_columns(table.name)}
            missing = expected - columns
            if missing:
                raise RuntimeError(
                    f"{table.name} schema is missing {', '.join(sorted(missing))}; run Alembic migrations before startup"
                )

    def _pod_stakeholders(self, pod: str):
        return self.repository.list_stakeholders(pod=pod)

    def _pod_opportunities(self, pod: str):
        ids = {item.id for item in self._pod_stakeholders(pod)}
        return [item for item in self.repository.list_opportunities() if ids.intersection(item.stakeholder_ids)]

    def _seed_if_needed(self) -> None:
        with self.engine.connect() as connection:
            seeded = connection.execute(
                select(pod_seed_registry.c.id).where(pod_seed_registry.c.id == self.seed_id)
            ).scalar_one_or_none()
        if seeded:
            return

        rows: dict[str, list[dict]] = defaultdict(list)
        now = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)
        stakeholder_by_id = self.repository.stakeholders
        opportunities = list(self.repository.list_opportunities())
        opportunity_by_stakeholder = {}
        for opportunity in opportunities:
            for stakeholder_id in opportunity.stakeholder_ids:
                opportunity_by_stakeholder.setdefault(stakeholder_id, opportunity)

        # Reuse every existing canonical meeting instead of discarding the account history.
        for meeting in self.repository.list_meetings():
            stakeholder = next((stakeholder_by_id.get(value) for value in meeting.stakeholder_ids if value in stakeholder_by_id), None)
            if stakeholder is None:
                continue
            opportunity = opportunity_by_stakeholder.get(stakeholder.id)
            event_id = f"event-{meeting.id}"
            rows["events"].append({
                "id": event_id,
                "pod_id": stakeholder.pod,
                "event_type": "client",
                "title": meeting.subject,
                "start_at": meeting.meeting_date,
                "end_at": meeting.meeting_date + timedelta(hours=1),
                "all_day": False,
                "stakeholder_id": stakeholder.id,
                "opportunity_id": opportunity.id if opportunity else None,
                "source_meeting_id": meeting.id,
                "importance": "High" if stakeholder.is_buyer else "Medium",
                "status": "Completed" if meeting.meeting_date < now else "Scheduled",
                "business_unit": stakeholder.business_unit,
                "is_client": True,
                "prep_required": meeting.meeting_date >= now,
                "previous_engagement": meeting.summary,
                "open_actions": meeting.next_steps or ["Confirm accountable owner and due date"],
                "discussion_topics": [meeting.outcome, "Confirm the next client commitment"],
                "created_at": meeting.created_at,
            })
            organizer = meeting.organizer if meeting.organizer != "Capco Account Team" else (stakeholder.capco_owner or "Alex Morgan")
            attendee_names = [organizer]
            if stakeholder.capco_owner and stakeholder.capco_owner not in attendee_names:
                attendee_names.append(stakeholder.capco_owner)
            for attendee_index, attendee_name in enumerate(attendee_names):
                role = next((value for name, value in CAPCO_TEAM if name == attendee_name), "Account team")
                rows["attendees"].append({
                    "id": f"{event_id}-attendee-{attendee_index}",
                    "event_id": event_id,
                    "employee_id": demo_employee_id(attendee_name),
                    "attendee_name": attendee_name,
                    "attendee_role": role,
                    "is_lead": attendee_index == 0,
                })

        for pod_index, pod in enumerate(POD_STRUCTURE):
            people = sorted(
                self._pod_stakeholders(pod),
                key=lambda item: (not item.is_budget_holder, not item.is_buyer, not item.is_primary_technology, item.name),
            )
            pod_opportunities = self._pod_opportunities(pod)
            if not people:
                continue
            pod_key = slug(pod)

            # Two scheduled client/account moments per weekday through mid-September.
            cursor = date(2026, 8, 13)
            schedule_index = 0
            while cursor <= date(2026, 9, 18):
                if cursor.weekday() < 5:
                    for slot, start_hour in enumerate((10, 14)):
                        person = people[schedule_index % min(len(people), 24)]
                        opportunity = opportunity_by_stakeholder.get(person.id)
                        if opportunity is None and pod_opportunities:
                            opportunity = pod_opportunities[schedule_index % len(pod_opportunities)]
                        title, event_type = EVENT_THEMES[(schedule_index + pod_index) % len(EVENT_THEMES)]
                        event_id = f"{pod_key}-planned-{cursor.isoformat()}-{slot + 1}"
                        start_at = datetime.combine(cursor, time(start_hour, 0), tzinfo=ZoneInfo("America/New_York"))
                        rows["events"].append({
                            "id": event_id,
                            "pod_id": pod,
                            "event_type": event_type,
                            "title": title,
                            "start_at": start_at,
                            "end_at": start_at + timedelta(minutes=60 if slot == 0 else 45),
                            "all_day": False,
                            "stakeholder_id": person.id,
                            "opportunity_id": opportunity.id if opportunity else None,
                            "source_meeting_id": None,
                            "importance": "High" if person.is_buyer or event_type in {"critical", "deadline"} else "Medium",
                            "status": "Scheduled",
                            "business_unit": person.business_unit,
                            "is_client": event_type != "internal",
                            "prep_required": event_type in {"client", "workshop", "critical", "deadline"},
                            "previous_engagement": f"The last conversation with {person.name} aligned on {', '.join(person.tags[:2]) or 'transformation priorities'} and left a decision path to confirm.",
                            "open_actions": [
                                "Confirm outstanding decisions and accountable owners",
                                "Send the latest evidence pack before the meeting",
                                "Agree the next client commitment and target date",
                            ],
                            "discussion_topics": [
                                f"Progress against {person.business_unit} priorities",
                                "Commercial and delivery dependencies",
                                "Executive sponsorship and next decision point",
                            ],
                            "created_at": now,
                        })
                        attendee_count = 3 if event_type in {"critical", "deadline"} else 2
                        for attendee_index in range(attendee_count):
                            attendee_name, attendee_role = CAPCO_TEAM[(schedule_index + attendee_index + pod_index) % len(CAPCO_TEAM)]
                            rows["attendees"].append({
                                "id": f"{event_id}-attendee-{attendee_index}",
                                "event_id": event_id,
                                "employee_id": demo_employee_id(attendee_name),
                                "attendee_name": attendee_name,
                                "attendee_role": attendee_role,
                                "is_lead": attendee_index == 0,
                            })
                        schedule_index += 1
                cursor += timedelta(days=1)

            for index, title in enumerate(TASK_TITLES):
                person = people[index % min(len(people), 24)]
                opportunity = opportunity_by_stakeholder.get(person.id)
                if opportunity is None and pod_opportunities:
                    opportunity = pod_opportunities[index % len(pod_opportunities)]
                task_id = f"{pod_key}-task-{index + 1:02d}"
                status = "Done" if index in {6, 12, 18, 21} else "In Progress" if index in {3, 9, 15} else "Open"
                due_date = date(2026, 8, 21) + timedelta(days=index)
                owner_name = CAPCO_TEAM[(index + pod_index) % len(CAPCO_TEAM)][0]
                rows["tasks"].append({
                    "id": task_id,
                    "pod_id": pod,
                    "title": title,
                    "description": f"Account action supporting {person.name} and the {person.business_unit} decision path.",
                    "owner_id": owner_name,
                    "owner_employee_id": demo_employee_id(owner_name),
                    "priority": "High" if index % 4 in {0, 1} else "Medium" if index % 4 == 2 else "Low",
                    "status": status,
                    "due_date": due_date,
                    "completed_at": now - timedelta(days=1) if status == "Done" else None,
                    "stakeholder_id": person.id,
                    "meeting_id": None,
                    "opportunity_id": opportunity.id if opportunity else None,
                    "critical_item_id": f"{pod_key}-critical-{(index % len(CRITICAL_TEMPLATES)) + 1:02d}" if index < 8 else None,
                    "created_at": now - timedelta(days=12 - min(index, 12)),
                    "updated_at": now,
                })

            for index, (item_type, severity, title, description) in enumerate(CRITICAL_TEMPLATES):
                person = people[index % min(len(people), 16)]
                opportunity = opportunity_by_stakeholder.get(person.id)
                if opportunity is None and pod_opportunities:
                    opportunity = pod_opportunities[index % len(pod_opportunities)]
                resolved = index >= 6
                rows["critical"].append({
                    "id": f"{pod_key}-critical-{index + 1:02d}",
                    "pod_id": pod,
                    "item_type": item_type,
                    "severity": severity,
                    "title": f"{person.business_unit}: {title}",
                    "description": description,
                    "owner_id": CAPCO_TEAM[(index + 3 + pod_index) % len(CAPCO_TEAM)][0],
                    "owner_employee_id": demo_employee_id(CAPCO_TEAM[(index + 3 + pod_index) % len(CAPCO_TEAM)][0]),
                    "status": "Resolved" if resolved else "Open",
                    "due_date": date(2026, 8, 27) + timedelta(days=index * 2),
                    "stakeholder_id": person.id,
                    "opportunity_id": opportunity.id if opportunity else None,
                    "engagement_id": None,
                    "created_at": now - timedelta(days=10 - index),
                    "resolved_at": now - timedelta(days=1) if resolved else None,
                })

            milestone_types = ["RFP", "COMMERCIAL", "DELIVERY", "RELATIONSHIP", "WORKSHOP", "GOVERNANCE"]
            milestone_titles = [
                "RFP response checkpoint", "Pricing approval deadline", "Mobilization readiness review",
                "Executive sponsor meeting", "Solution validation workshop", "Steering committee",
                "Contract decision date", "Architecture sign-off", "Benefits case approval",
                "Delivery health review", "Procurement submission", "Quarterly business review",
            ]
            for index, title in enumerate(milestone_titles):
                person = people[index % min(len(people), 20)]
                opportunity = opportunity_by_stakeholder.get(person.id)
                if opportunity is None and pod_opportunities:
                    opportunity = pod_opportunities[index % len(pod_opportunities)]
                rows["milestones"].append({
                    "id": f"{pod_key}-milestone-{index + 1:02d}",
                    "pod_id": pod,
                    "milestone_type": milestone_types[index % len(milestone_types)],
                    "title": f"{person.business_unit}: {title}",
                    "milestone_date": date(2026, 8, 27) + timedelta(days=index * 3),
                    "description": f"Decision milestone linked to {person.name} and current account commitments.",
                    "owner_id": CAPCO_TEAM[(index + pod_index) % len(CAPCO_TEAM)][0],
                    "owner_employee_id": demo_employee_id(CAPCO_TEAM[(index + pod_index) % len(CAPCO_TEAM)][0]),
                    "stakeholder_id": person.id,
                    "opportunity_id": opportunity.id if opportunity else None,
                    "engagement_id": None,
                })

            focus_items = [
                f"Convert the highest-value {pod} opportunities",
                "Stabilize delivery against executive commitments",
                "Expand coverage across priority buyers and influencers",
                "Close commercial and staffing dependencies early",
            ]
            for period_type, period_start in (("month", date(2026, 8, 1)), ("week", date(2026, 8, 24))):
                rows["focus"].append({
                    "id": f"{pod_key}-focus-{period_type}-2026-08",
                    "pod_id": pod,
                    "period_type": period_type,
                    "period_start": period_start,
                    "content": focus_items,
                    "created_by": "Morgan Stanley Account Leadership",
                    "updated_at": now,
                })

            relationship_signals = [
                "No executive touchpoint is scheduled; confirm a sponsor meeting",
                "Decision influence increased after the last working session",
                "Relationship is concentrated with one Capco owner",
                "Budget authority is likely but has not been explicitly confirmed",
                "New stakeholder entered the evaluation group",
                "Client requested evidence from a comparable transformation",
                "Contact cadence slipped behind the pursuit plan",
                "Technical support is strong; commercial sponsorship needs work",
                "Stakeholder sentiment improved after delivery recovery actions",
                "Cross-division introduction could unlock adjacent demand",
            ]
            for index, signal in enumerate(relationship_signals):
                person = people[index % min(len(people), 20)]
                rows["relationships"].append({
                    "id": f"{pod_key}-relationship-{index + 1:02d}",
                    "pod_id": pod,
                    "stakeholder_id": person.id,
                    "signal_type": "Coverage gap" if index % 3 == 0 else "Influence change" if index % 3 == 1 else "Engagement cadence",
                    "days_since_contact": 12 + index * 4,
                    "importance": "High" if index < 4 else "Medium",
                    "signal": signal,
                    "status": "Open",
                    "observed_at": now - timedelta(days=index),
                })

            for index in range(16):
                kind, headline = CHANGE_TEMPLATES[index % len(CHANGE_TEMPLATES)]
                person = people[index % min(len(people), 24)]
                opportunity = opportunity_by_stakeholder.get(person.id)
                if opportunity is None and pod_opportunities:
                    opportunity = pod_opportunities[index % len(pod_opportunities)]
                rows["changes"].append({
                    "id": f"{pod_key}-change-{index + 1:02d}",
                    "pod_id": pod,
                    "event_date": date(2026, 8, 26) - timedelta(days=index),
                    "kind": kind,
                    "headline": headline,
                    "detail": f"{person.name} · {person.business_unit}" + (f" · {opportunity.name}" if opportunity else ""),
                    "stakeholder_id": person.id,
                    "opportunity_id": opportunity.id if opportunity else None,
                })

            health_rows = [
                ("Delivery confidence", 72 - pod_index * 2, "AMBER", "Two milestone dependencies require active executive management."),
                ("Client sentiment", 84 - pod_index, "GREEN", "Recent sponsor and working-team feedback is constructive."),
                ("Staffing readiness", 68 + pod_index * 3, "AMBER", "Specialist capacity is not fully locked for priority demand."),
                ("Coverage strength", 76 - pod_index * 2, "GREEN", "Buyer coverage is broad, with a small number of executive gaps."),
            ]
            for index, (label, value, status, detail) in enumerate(health_rows):
                rows["health"].append({
                    "id": f"{pod_key}-health-{index + 1:02d}",
                    "pod_id": pod,
                    "label": label,
                    "metric_value": value,
                    "status": status,
                    "detail": detail,
                    "sort_order": index,
                    "as_of_date": date(2026, 8, 26),
                })

            for index, opportunity in enumerate(pod_opportunities):
                rows["opportunity_contexts"].append({
                    "opportunity_id": opportunity.id,
                    "pod_id": pod,
                    "latest_movement": [
                        "Sponsor confirmed the next decision checkpoint",
                        "Scope expanded after discovery",
                        "Commercial review moved forward",
                        "Technical validation completed",
                    ][index % 4],
                    "commercial_context": f"{opportunity.name} is tied to a priority transformation theme and an active client decision path.",
                    "recommended_next_step": "Confirm the economic buyer, approval sequence and next dated client commitment.",
                    "updated_at": now - timedelta(days=index % 10),
                })

        table_rows = [
            (pod_events, rows["events"]),
            (pod_event_attendees, rows["attendees"]),
            (pod_tasks, rows["tasks"]),
            (pod_critical_items, rows["critical"]),
            (pod_milestones, rows["milestones"]),
            (pod_focus, rows["focus"]),
            (pod_relationship_signals, rows["relationships"]),
            (pod_change_events, rows["changes"]),
            (pod_health_metrics, rows["health"]),
            (pod_opportunity_contexts, rows["opportunity_contexts"]),
        ]
        with self.engine.begin() as connection:
            for table, values in table_rows:
                if values:
                    connection.execute(insert(table), values)
            connection.execute(insert(pod_seed_registry).values(
                id=self.seed_id,
                seeded_at=now,
                row_counts={table.name: len(values) for table, values in table_rows},
            ))

    def _normalize_attendee_names(self) -> None:
        """Upgrade generic legacy attendee labels to an accountable full name."""
        with self.engine.begin() as connection:
            connection.execute(
                update(pod_event_attendees)
                .where(pod_event_attendees.c.attendee_name == "Capco Account Team")
                .values(attendee_name="Alex Morgan", attendee_role="Managing Principal")
            )

    def _reconcile_employee_identities(self) -> None:
        """Backfill canonical IDs on operating rows created before identity governance."""
        if not inspect(self.engine).has_table("capco_employees"):
            return
        with self.engine.begin() as connection:
            employee_rows = connection.execute(text("SELECT id, name FROM capco_employees WHERE active = true")).all()
            for employee_id, employee_name in employee_rows:
                connection.execute(
                    update(pod_event_attendees)
                    .where(pod_event_attendees.c.employee_id.is_(None), pod_event_attendees.c.attendee_name == employee_name)
                    .values(employee_id=employee_id)
                )
                for table in (pod_tasks, pod_critical_items, pod_milestones):
                    connection.execute(
                        update(table)
                        .where(table.c.owner_employee_id.is_(None), table.c.owner_id == employee_name)
                        .values(owner_employee_id=employee_id)
                    )

    def counts(self) -> dict[str, int]:
        tables = [pod_events, pod_event_attendees, pod_tasks, pod_critical_items, pod_milestones, pod_focus,
                  pod_relationship_signals, pod_change_events, pod_health_metrics, pod_opportunity_contexts]
        with self.engine.connect() as connection:
            return {table.name: connection.execute(select(func.count()).select_from(table)).scalar_one() for table in tables}

    def _period_bounds(self, period: str, period_start: date | None) -> tuple[date, date]:
        today = date.today()
        start = period_start or (
            today - timedelta(days=today.weekday())
            if period == "week"
            else today.replace(day=1)
        )
        if period == "week":
            return start, start + timedelta(days=7)
        if start.month == 12:
            return start, date(start.year + 1, 1, 1)
        return start, date(start.year, start.month + 1, 1)

    def _task_view(self, row, stakeholders, opportunities) -> dict:
        stakeholder = stakeholders.get(row["stakeholder_id"])
        opportunity = opportunities.get(row["opportunity_id"])
        tags = self._tags(
            row.get("tags"),
            stakeholder.tags if stakeholder else None,
            opportunity.tags if opportunity else None,
            self._semantic_tags(row["title"], row["description"]),
        )
        return {
            "id": row["id"],
            "pod": row["pod_id"],
            "title": row["title"],
            "description": row["description"],
            "owner": row["owner_id"] or "Account team",
            "ownerEmployeeId": row["owner_employee_id"],
            "priority": row["priority"],
            "status": row["status"],
            "due": row["due_date"].isoformat() if row["due_date"] else None,
            "stakeholder": stakeholder.name if stakeholder else None,
            "stakeholderId": stakeholder.id if stakeholder else None,
            "opportunity": opportunity.name if opportunity else None,
            "opportunityId": opportunity.id if opportunity else None,
            "criticalItemId": row["critical_item_id"],
            "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
            "tags": tags,
        }

    def list_tasks(self, pod: str) -> list[dict]:
        self._validate_pod(pod)
        stakeholders = {item.id: item for item in self._pod_stakeholders(pod)}
        opportunities = {item.id: item for item in self._pod_opportunities(pod)}
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(pod_tasks).where(pod_tasks.c.pod_id == pod).order_by(pod_tasks.c.due_date, pod_tasks.c.id)
            ).mappings().all()
        return [self._task_view(row, stakeholders, opportunities) for row in rows]

    def update_task(self, pod: str, task_id: str, changes: dict) -> dict:
        self._validate_pod(pod)
        if changes.get("owner_employee_id"):
            owner_names = self._employee_names([changes["owner_employee_id"]])
            if changes["owner_employee_id"] not in owner_names:
                raise NotFoundError("Task owner does not exist")
            changes["owner"] = owner_names[changes["owner_employee_id"]]
        values = {}
        field_map = {"title": "title", "owner": "owner_id", "owner_employee_id": "owner_employee_id", "priority": "priority", "status": "status", "due": "due_date", "tags": "tags"}
        for field, column in field_map.items():
            if field in changes and changes[field] is not None:
                values[column] = changes[field]
        if "status" in values:
            values["completed_at"] = datetime.now(timezone.utc) if values["status"] == "Done" else None
        values["updated_at"] = datetime.now(timezone.utc)
        with self.engine.begin() as connection:
            exists = connection.execute(select(pod_tasks.c.id).where(and_(pod_tasks.c.pod_id == pod, pod_tasks.c.id == task_id))).scalar_one_or_none()
            if not exists:
                raise NotFoundError("Task not found")
            connection.execute(update(pod_tasks).where(and_(pod_tasks.c.pod_id == pod, pod_tasks.c.id == task_id)).values(**values))
        return next(item for item in self.list_tasks(pod) if item["id"] == task_id)

    def create_task(self, pod: str, payload: dict, task_id: str) -> dict:
        self._validate_pod(pod)
        stakeholders = self._pod_stakeholders(pod)
        opportunities = self._pod_opportunities(pod)
        stakeholder_id = payload.get("stakeholder_id")
        opportunity_id = payload.get("opportunity_id")
        stakeholder = next((item for item in stakeholders if item.id == stakeholder_id), None)
        opportunity = next((item for item in opportunities if item.id == opportunity_id), None)
        if stakeholder_id and not stakeholder:
            raise NotFoundError("Linked stakeholder is not in this pod")
        if opportunity_id and not opportunity:
            raise NotFoundError("Linked opportunity is not in this pod")
        owner_employee_id = payload.get("owner_employee_id")
        owner_names = self._employee_names([owner_employee_id]) if owner_employee_id else {}
        if owner_employee_id and owner_employee_id not in owner_names:
            raise NotFoundError("Task owner does not exist")
        owner_name = owner_names.get(owner_employee_id) or payload.get("owner") or "Account team"
        now = datetime.now(timezone.utc)
        with self.engine.begin() as connection:
            connection.execute(insert(pod_tasks).values(
                id=task_id,
                pod_id=pod,
                title=payload["title"],
                description="User-created account action",
                owner_id=owner_name,
                owner_employee_id=owner_employee_id or demo_employee_id(owner_name),
                priority=payload.get("priority") or "Medium",
                status="Open",
                due_date=payload["due"],
                completed_at=None,
                stakeholder_id=stakeholder.id if stakeholder else None,
                meeting_id=None,
                opportunity_id=opportunity.id if opportunity else None,
                critical_item_id=None,
                tags=payload.get("tags") or [],
                created_at=now,
                updated_at=now,
            ))
        return next(item for item in self.list_tasks(pod) if item["id"] == task_id)

    def event_exists(self, meeting_id: str) -> bool:
        with self.engine.connect() as connection:
            return connection.execute(select(pod_events.c.id).where(
                (pod_events.c.id == meeting_id) | (pod_events.c.source_meeting_id == meeting_id)
            )).first() is not None

    def generate_meeting_brief(self, meeting_id: str) -> dict:
        """Build a grounded brief from the canonical account records linked to a meeting."""
        with self.engine.connect() as connection:
            event = connection.execute(select(pod_events).where(
                (pod_events.c.id == meeting_id) | (pod_events.c.source_meeting_id == meeting_id)
            )).mappings().first()
            if event is None:
                raise NotFoundError("Meeting not found")
            attendee_rows = connection.execute(select(pod_event_attendees).where(
                pod_event_attendees.c.event_id == event["id"]
            ).order_by(pod_event_attendees.c.is_lead.desc(), pod_event_attendees.c.id)).mappings().all()
            task_rows = connection.execute(select(pod_tasks).where(and_(
                pod_tasks.c.pod_id == event["pod_id"],
                pod_tasks.c.stakeholder_id == event["stakeholder_id"],
                pod_tasks.c.status != "Done",
            )).order_by(pod_tasks.c.due_date).limit(6)).mappings().all()
            risk_rows = connection.execute(select(pod_critical_items).where(and_(
                pod_critical_items.c.pod_id == event["pod_id"],
                pod_critical_items.c.stakeholder_id == event["stakeholder_id"],
                pod_critical_items.c.status != "Resolved",
            )).order_by(pod_critical_items.c.due_date).limit(5)).mappings().all()
            opportunity_context = connection.execute(select(pod_opportunity_contexts).where(
                pod_opportunity_contexts.c.opportunity_id == event["opportunity_id"]
            )).mappings().first() if event["opportunity_id"] else None

        person = self.repository.get_stakeholder(event["stakeholder_id"]) if event["stakeholder_id"] else None
        opportunity = self.repository.opportunities.get(event["opportunity_id"])
        canonical_id = event["source_meeting_id"] or event["id"]
        canonical = self.repository.meetings.get(canonical_id)
        notes = self.repository.list_notes(person.id)[:5] if person else []
        stakeholder_documents = self.repository.list_documents(person.id)[:8] if person else []
        meeting_documents = []
        seen_documents = set()
        for target in (canonical_id, event["id"]):
            for document in self.repository.list_meeting_documents(target):
                if document.id not in seen_documents:
                    seen_documents.add(document.id)
                    meeting_documents.append(document)
        event_start = event["start_at"]
        if event_start.tzinfo is None:
            event_start = event_start.replace(tzinfo=ZoneInfo("America/New_York"))
        prior_meetings = [
            item for item in self.repository.list_meetings(person.id) if item.id != canonical_id and item.meeting_date < event_start
        ][:4] if person else []

        objectives = self._tags(
            list(event["discussion_topics"] or []),
            [canonical.outcome] if canonical and canonical.outcome else None,
            [opportunity_context["recommended_next_step"]] if opportunity_context else None,
        )
        open_actions = list(dict.fromkeys([
            *(event["open_actions"] or []),
            *(canonical.next_steps if canonical else []),
            *(row["title"] for row in task_rows),
        ]))[:8]
        risks = [{
            "severity": row["severity"],
            "title": row["title"],
            "description": row["description"],
            "due": row["due_date"].isoformat() if row["due_date"] else None,
            "owner": row["owner_id"],
        } for row in risk_rows]
        intelligence = []
        if event["previous_engagement"]:
            intelligence.append({"type": "Meeting context", "text": event["previous_engagement"]})
        intelligence.extend({"type": f"Stakeholder note · {note.category}", "text": note.body} for note in notes)
        intelligence.extend({
            "type": f"Prior meeting · {meeting.meeting_date.date().isoformat()}",
            "text": meeting.summary or meeting.outcome,
        } for meeting in prior_meetings if meeting.summary or meeting.outcome)
        intelligence = intelligence[:7]

        documents = []
        for document, scope in [
            *((value, "Meeting") for value in meeting_documents),
            *((value, "Stakeholder") for value in stakeholder_documents),
        ]:
            documents.append({
                "id": document.id,
                "scope": scope,
                "title": document.title,
                "type": document.document_type,
                "description": document.description,
                "fileName": document.file_name,
                "sharePointUrl": document.sharepoint_url or document.url,
                "tags": document.tags,
                "updatedAt": document.updated_at.isoformat(),
            })

        relationship = person.relationship_strength if person else "Unknown"
        executive_summary = (
            f"Prepare for {event['title']} with {person.name if person else 'the account team'}. "
            f"The relationship is {relationship.lower()}"
            f"{f' and the linked {opportunity.name} opportunity is at {opportunity.probability}% probability' if opportunity else ''}. "
            f"Use the discussion to resolve {len(open_actions)} open action{'s' if len(open_actions) != 1 else ''}"
            f"{f' and {len(risks)} active risk items' if risks else ''}."
        )
        recommended_questions = [
            f"What decision or commitment is required to close: {value}?" for value in open_actions[:3]
        ]
        recommended_questions.extend(
            f"What recovery action and accountable owner will address {risk['title']} by {risk['due'] or 'the next checkpoint'}?"
            for risk in risks[:2]
        )
        if opportunity:
            recommended_questions.append(f"What evidence is still required to advance {opportunity.name} from {opportunity.stage}?")

        return {
            "meetingId": canonical_id,
            "eventId": event["id"],
            "pod": event["pod_id"],
            "status": "Ready",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "generationMethod": "Grounded account brief v1",
            "meeting": {
                "title": event["title"],
                "start": _eastern_iso(event["start_at"]),
                "stakeholderId": person.id if person else None,
                "stakeholder": person.name if person else "Account team",
                "stakeholderTitle": person.title if person else None,
                "relationship": relationship,
                "capcoAttendees": [row["attendee_name"] for row in attendee_rows],
                "capcoAttendeeIds": [row["employee_id"] for row in attendee_rows if row["employee_id"]],
            },
            "executiveSummary": executive_summary,
            "stakeholderContext": {
                "role": person.organizational_role if person else None,
                "businessUnit": person.business_unit if person else event["business_unit"],
                "capcoOwner": person.capco_owner if person else None,
                "tags": person.tags if person else [],
                "biography": person.biography if person else "",
            },
            "objectives": objectives or ["Confirm the desired outcome and accountable next step"],
            "openActions": open_actions,
            "activeRisks": risks,
            "latestIntelligence": intelligence,
            "documentContext": documents,
            "recommendedQuestions": recommended_questions or ["What decision, owner, and timing should be confirmed in this meeting?"],
            "sourceSummary": {
                "meetingDocuments": len(meeting_documents),
                "stakeholderDocuments": len(stakeholder_documents),
                "stakeholderNotes": len(notes),
                "priorMeetings": len(prior_meetings),
                "openActions": len(open_actions),
                "activeRisks": len(risks),
            },
        }

    def list_meeting_options(self, pod: str) -> list[dict]:
        self._validate_pod(pod)
        with self.engine.connect() as connection:
            rows = connection.execute(select(pod_events).where(
                pod_events.c.pod_id == pod
            ).order_by(pod_events.c.start_at.desc())).mappings().all()
            event_ids = [row["id"] for row in rows]
            attendee_rows = connection.execute(select(pod_event_attendees).where(
                pod_event_attendees.c.event_id.in_(event_ids)
            ).order_by(pod_event_attendees.c.event_id, pod_event_attendees.c.is_lead.desc())).mappings().all() if event_ids else []
        attendees_by_event: dict[str, list[str]] = defaultdict(list)
        attendee_ids_by_event: dict[str, list[str]] = defaultdict(list)
        for attendee in attendee_rows:
            attendees_by_event[attendee["event_id"]].append(attendee["attendee_name"])
            if attendee["employee_id"]:
                attendee_ids_by_event[attendee["event_id"]].append(attendee["employee_id"])
        meeting_models = self.repository.meetings
        stakeholders = self.repository.stakeholders
        opportunities = self.repository.opportunities
        return [{
            "id": row["source_meeting_id"] or row["id"],
            "event_id": row["id"],
            "title": row["title"],
            "meeting_date": _eastern_iso(row["start_at"]),
            "duration_minutes": max(15, int((row["end_at"] - row["start_at"]).total_seconds() / 60)),
            "stakeholder_id": row["stakeholder_id"],
            "stakeholder_ids": list(meeting_models[row["source_meeting_id"]].stakeholder_ids) if row["source_meeting_id"] in meeting_models else ([row["stakeholder_id"]] if row["stakeholder_id"] else []),
            "business_unit": row["business_unit"],
            "summary": meeting_models[row["source_meeting_id"]].summary if row["source_meeting_id"] in meeting_models else row["previous_engagement"],
            "organizer": meeting_models[row["source_meeting_id"]].organizer if row["source_meeting_id"] in meeting_models else (attendees_by_event[row["id"]][0] if attendees_by_event[row["id"]] else "Capco Account Team"),
            "organizer_employee_id": meeting_models[row["source_meeting_id"]].organizer_employee_id if row["source_meeting_id"] in meeting_models else (attendee_ids_by_event[row["id"]][0] if attendee_ids_by_event[row["id"]] else None),
            "capco_attendees": attendees_by_event[row["id"]],
            "capco_attendee_ids": attendee_ids_by_event[row["id"]],
            "outcome": meeting_models[row["source_meeting_id"]].outcome if row["source_meeting_id"] in meeting_models else ((row["discussion_topics"] or ["Follow-up required"])[0]),
            "next_steps": list(meeting_models[row["source_meeting_id"]].next_steps) if row["source_meeting_id"] in meeting_models else list(row["open_actions"] or []),
            "event_type": row["event_type"],
            "opportunity_id": row["opportunity_id"],
            "prep_required": bool(row["prep_required"]),
            "tags": self._tags(
                row.get("tags"),
                meeting_models[row["source_meeting_id"]].tags if row["source_meeting_id"] in meeting_models else None,
                stakeholders[row["stakeholder_id"]].tags if row["stakeholder_id"] in stakeholders else None,
                opportunities[row["opportunity_id"]].tags if row["opportunity_id"] in opportunities else None,
            ),
        } for row in rows]

    def update_meeting_event(self, pod: str, meeting_id: str, changes: dict, connection=None, update_canonical: bool = True) -> dict:
        self._validate_pod(pod)
        if connection is None:
            with self.engine.connect() as read_connection:
                row = read_connection.execute(select(pod_events).where(and_(
                    pod_events.c.pod_id == pod,
                    (pod_events.c.id == meeting_id) | (pod_events.c.source_meeting_id == meeting_id),
                ))).mappings().first()
        else:
            row = connection.execute(select(pod_events).where(and_(
                pod_events.c.pod_id == pod,
                (pod_events.c.id == meeting_id) | (pod_events.c.source_meeting_id == meeting_id),
            ))).mappings().first()
        if row is None:
            raise NotFoundError("Meeting not found")
        stakeholders = {item.id: item for item in self._pod_stakeholders(pod)}
        stakeholder_ids = changes.get("stakeholder_ids")
        stakeholder_id = stakeholder_ids[0] if stakeholder_ids else row["stakeholder_id"]
        if stakeholder_id not in stakeholders:
            raise NotFoundError("Meeting stakeholder is not available in this pod")
        if "opportunity_id" in changes and changes["opportunity_id"]:
            opportunity_ids = {item.id for item in self._pod_opportunities(pod)}
            if changes["opportunity_id"] not in opportunity_ids:
                raise NotFoundError("Meeting opportunity is not available in this pod")

        source_meeting_id = row["source_meeting_id"]
        meeting_fields = {key: value for key, value in changes.items() if key in {
            "subject", "meeting_date", "summary", "stakeholder_ids", "organizer", "organizer_employee_id",
            "capco_attendee_ids", "outcome", "next_steps", "tags",
        }}
        if "opportunity_id" in changes:
            meeting_fields["opportunity_ids"] = [changes["opportunity_id"]] if changes["opportunity_id"] else []
        if update_canonical and source_meeting_id in self.repository.meetings and meeting_fields:
            self.repository.update_meeting(source_meeting_id, MeetingUpdate(**meeting_fields))

        current_duration = max(15, int((row["end_at"] - row["start_at"]).total_seconds() / 60))
        start_at = changes.get("meeting_date", row["start_at"])
        duration = changes.get("duration_minutes", current_duration)
        values = {
            "stakeholder_id": stakeholder_id,
            "business_unit": stakeholders[stakeholder_id].business_unit,
        }
        field_map = {
            "subject": "title", "event_type": "event_type", "opportunity_id": "opportunity_id",
            "prep_required": "prep_required", "summary": "previous_engagement", "next_steps": "open_actions", "tags": "tags",
        }
        for field, column in field_map.items():
            if field in changes:
                values[column] = changes[field]
        if "outcome" in changes:
            existing_topics = list(row["discussion_topics"] or [])
            values["discussion_topics"] = [changes["outcome"], *existing_topics[1:]]
        if "meeting_date" in changes or "duration_minutes" in changes:
            values["start_at"] = start_at
            values["end_at"] = start_at + timedelta(minutes=duration)
        if "event_type" in changes:
            values["is_client"] = changes["event_type"] != "internal"

        attendee_ids = changes.get("capco_attendee_ids")
        attendees = changes.get("capco_attendees")
        if attendee_ids is not None:
            names_by_id = self._employee_names(attendee_ids)
            missing = set(attendee_ids) - set(names_by_id)
            if missing:
                raise NotFoundError("One or more Capco meeting attendees do not exist")
            attendees = [names_by_id[value] for value in attendee_ids]
        elif attendees is None and "organizer" in changes:
            attendees = [changes["organizer"]]
        def write_projection(write_connection):
            write_connection.execute(update(pod_events).where(pod_events.c.id == row["id"]).values(**values))
            if attendees is not None:
                names = list(dict.fromkeys(value.strip() for value in attendees if value and value.strip()))
                write_connection.execute(delete(pod_event_attendees).where(pod_event_attendees.c.event_id == row["id"]))
                for index, name in enumerate(names):
                    employee_id = attendee_ids[index] if attendee_ids is not None else demo_employee_id(name)
                    write_connection.execute(insert(pod_event_attendees).values(
                        id=f"{row['id']}-attendee-{index}", event_id=row["id"], employee_id=employee_id, attendee_name=name,
                        attendee_role="Meeting owner" if index == 0 else "Account team", is_lead=index == 0,
                    ))
        if connection is None:
            with self.engine.begin() as write_connection:
                write_projection(write_connection)
        else:
            write_projection(connection)
        return next(item for item in self.list_meeting_options(pod) if item["event_id"] == row["id"])

    def create_meeting_event(self, pod: str, meeting, payload: dict, connection=None) -> dict:
        self._validate_pod(pod)
        stakeholders = {item.id: item for item in self._pod_stakeholders(pod)}
        invalid = [value for value in meeting.stakeholder_ids if value not in stakeholders]
        if invalid:
            raise NotFoundError("Meeting stakeholder is not available in this pod")
        person = stakeholders[meeting.stakeholder_ids[0]]
        opportunities = {item.id: item for item in self._pod_opportunities(pod)}
        opportunity_id = payload.get("opportunity_id")
        if opportunity_id and opportunity_id not in opportunities:
            raise NotFoundError("Meeting opportunity is not available in this pod")
        event_id = f"event-{meeting.id}"
        attendee_ids = list(dict.fromkeys(payload.get("capco_attendee_ids") or meeting.capco_attendee_ids or []))
        names_by_id = self._employee_names(attendee_ids)
        if set(attendee_ids) - set(names_by_id):
            raise NotFoundError("One or more Capco meeting attendees do not exist")
        attendees = [names_by_id[value] for value in attendee_ids] if attendee_ids else list(dict.fromkeys(
            value.strip() for value in (payload.get("capco_attendees") or [meeting.organizer]) if value and value.strip()
        )) or [meeting.organizer]
        start_at = meeting.meeting_date
        now = datetime.now(timezone.utc)
        status_value = "Completed" if start_at < now else "Scheduled"
        def write_rows(active_connection):
            active_connection.execute(insert(pod_events).values(
                id=event_id,
                pod_id=pod,
                event_type=payload.get("event_type") or "client",
                title=meeting.subject,
                start_at=start_at,
                end_at=start_at + timedelta(minutes=payload.get("duration_minutes") or 60),
                all_day=False,
                stakeholder_id=person.id,
                opportunity_id=opportunity_id,
                source_meeting_id=meeting.id,
                importance="High" if person.is_buyer else "Medium",
                status=status_value,
                business_unit=person.business_unit,
                is_client=(payload.get("event_type") or "client") != "internal",
                prep_required=bool(payload.get("prep_required", True)),
                previous_engagement=meeting.summary,
                open_actions=meeting.next_steps,
                discussion_topics=[meeting.outcome] if meeting.outcome else [],
                tags=meeting.tags,
                created_at=meeting.created_at,
            ))
            for index, attendee_name in enumerate(attendees):
                employee_id = attendee_ids[index] if attendee_ids else demo_employee_id(attendee_name)
                active_connection.execute(insert(pod_event_attendees).values(
                    id=f"{event_id}-attendee-{index}",
                    event_id=event_id,
                    employee_id=employee_id,
                    attendee_name=attendee_name,
                    attendee_role="Meeting owner" if index == 0 else "Account team",
                    is_lead=index == 0,
                ))
        if connection is None:
            with self.engine.begin() as active_connection:
                write_rows(active_connection)
        else:
            write_rows(connection)
        return {
            "id": event_id,
            "meeting_id": meeting.id,
            "pod": pod,
            "title": meeting.subject,
            "start": _eastern_iso(start_at),
            "stakeholder_id": person.id,
            "capco_attendees": attendees,
            "capco_attendee_ids": attendee_ids or [value for value in (demo_employee_id(name) for name in attendees) if value],
        }

    def create_critical_item(self, pod: str, payload: dict, item_id: str) -> dict:
        self._validate_pod(pod)
        stakeholders = {item.id: item for item in self._pod_stakeholders(pod)}
        stakeholder = stakeholders.get(payload["stakeholder_id"])
        if stakeholder is None:
            raise NotFoundError("Critical item stakeholder is not available in this pod")
        opportunities = {item.id: item for item in self._pod_opportunities(pod)}
        opportunity_id = payload.get("opportunity_id")
        if opportunity_id and opportunity_id not in opportunities:
            raise NotFoundError("Critical item opportunity is not available in this pod")
        owner_employee_id = payload.get("capco_owner_employee_id")
        owner_names = self._employee_names([owner_employee_id]) if owner_employee_id else {}
        if owner_employee_id and owner_employee_id not in owner_names:
            raise NotFoundError("Critical item owner does not exist")
        owner_name = owner_names.get(owner_employee_id) or payload["capco_owner"]
        now = datetime.now(timezone.utc)
        with self.engine.begin() as connection:
            connection.execute(insert(pod_critical_items).values(
                id=item_id,
                pod_id=pod,
                item_type=payload["item_type"],
                severity=payload["severity"],
                title=payload["title"],
                description=payload.get("description") or "",
                owner_id=owner_name,
                owner_employee_id=owner_employee_id or demo_employee_id(owner_name),
                status="Open",
                due_date=payload["due_date"],
                stakeholder_id=stakeholder.id,
                opportunity_id=opportunity_id,
                engagement_id=None,
                tags=payload.get("tags") or [],
                created_at=now,
                resolved_at=None,
            ))
        return {
            "id": item_id,
            "pod": pod,
            "status": "Open",
            "stakeholder_id": stakeholder.id,
            "ms_owner": stakeholder.name,
            "capco_owner": owner_name,
            "capco_owner_employee_id": owner_employee_id or demo_employee_id(owner_name),
        }

    def update_focus(self, pod: str, content: list[str], period_type: str = "month", period_start: date | None = None) -> list[str]:
        self._validate_pod(pod)
        start = period_start or date(2026, 8, 1)
        record_id = f"{slug(pod)}-focus-{period_type}-{start.isoformat()}"
        now = datetime.now(timezone.utc)
        with self.engine.begin() as connection:
            existing = connection.execute(select(pod_focus.c.id).where(and_(
                pod_focus.c.pod_id == pod,
                pod_focus.c.period_type == period_type,
                pod_focus.c.period_start == start,
            ))).scalar_one_or_none()
            if existing:
                connection.execute(update(pod_focus).where(pod_focus.c.id == existing).values(content=content, updated_at=now))
            else:
                connection.execute(insert(pod_focus).values(
                    id=record_id, pod_id=pod, period_type=period_type, period_start=start,
                    content=content, created_by="Pod View user", updated_at=now,
                ))
        return content

    def update_critical_status(self, pod: str, item_id: str, status: str) -> dict:
        self._validate_pod(pod)
        now = datetime.now(timezone.utc)
        with self.engine.begin() as connection:
            exists = connection.execute(select(pod_critical_items.c.id).where(and_(
                pod_critical_items.c.pod_id == pod, pod_critical_items.c.id == item_id,
            ))).scalar_one_or_none()
            if not exists:
                raise NotFoundError("Critical item not found")
            connection.execute(update(pod_critical_items).where(and_(
                pod_critical_items.c.pod_id == pod, pod_critical_items.c.id == item_id,
            )).values(status=status, resolved_at=now if status == "Resolved" else None))
        return {"id": item_id, "pod": pod, "status": status, "resolved_at": now if status == "Resolved" else None}

    def update_critical_item(self, pod: str, item_id: str, changes: dict) -> dict:
        self._validate_pod(pod)
        stakeholders = {item.id: item for item in self._pod_stakeholders(pod)}
        if changes.get("stakeholder_id") and changes["stakeholder_id"] not in stakeholders:
            raise NotFoundError("Critical item stakeholder is not available in this pod")
        if "opportunity_id" in changes and changes["opportunity_id"]:
            opportunity_ids = {item.id for item in self._pod_opportunities(pod)}
            if changes["opportunity_id"] not in opportunity_ids:
                raise NotFoundError("Critical item opportunity is not available in this pod")
        if changes.get("capco_owner_employee_id"):
            owner_names = self._employee_names([changes["capco_owner_employee_id"]])
            if changes["capco_owner_employee_id"] not in owner_names:
                raise NotFoundError("Critical item owner does not exist")
            changes["capco_owner"] = owner_names[changes["capco_owner_employee_id"]]
        field_map = {
            "title": "title", "description": "description", "item_type": "item_type", "severity": "severity",
            "capco_owner": "owner_id", "due_date": "due_date", "stakeholder_id": "stakeholder_id",
            "capco_owner_employee_id": "owner_employee_id",
            "opportunity_id": "opportunity_id", "status": "status",
            "tags": "tags",
        }
        values = {column: changes[field] for field, column in field_map.items() if field in changes}
        if changes.get("status") == "Resolved":
            values["resolved_at"] = datetime.now(timezone.utc)
        elif changes.get("status") == "Open":
            values["resolved_at"] = None
        with self.engine.begin() as connection:
            exists = connection.execute(select(pod_critical_items.c.id).where(and_(
                pod_critical_items.c.pod_id == pod, pod_critical_items.c.id == item_id,
            ))).scalar_one_or_none()
            if not exists:
                raise NotFoundError("Critical item not found")
            connection.execute(update(pod_critical_items).where(and_(
                pod_critical_items.c.pod_id == pod, pod_critical_items.c.id == item_id,
            )).values(**values))
        return {"id": item_id, "pod": pod, **changes}

    def _single_dashboard(self, pod: str, period: str, period_start: date | None = None) -> dict:
        self._validate_pod(pod)
        start, end = self._period_bounds(period, period_start)
        start_at = datetime.combine(start, time.min, tzinfo=ZoneInfo("America/New_York"))
        end_at = datetime.combine(end, time.min, tzinfo=ZoneInfo("America/New_York"))
        stakeholders = {item.id: item for item in self._pod_stakeholders(pod)}
        opportunity_models = self._pod_opportunities(pod)
        opportunities_by_id = {item.id: item for item in opportunity_models}

        with self.engine.connect() as connection:
            event_rows = connection.execute(select(pod_events).where(and_(
                pod_events.c.pod_id == pod,
                pod_events.c.start_at >= start_at,
                pod_events.c.start_at < end_at,
            )).order_by(pod_events.c.start_at)).mappings().all()
            prep_event_rows = connection.execute(select(pod_events).where(and_(
                pod_events.c.pod_id == pod,
                pod_events.c.start_at >= start_at,
                pod_events.c.start_at < start_at + timedelta(days=45),
            )).order_by(pod_events.c.start_at)).mappings().all()
            display_event_rows = {row["id"]: row for row in [*event_rows, *prep_event_rows]}
            event_ids = list(display_event_rows)
            attendee_rows = connection.execute(select(pod_event_attendees).where(
                pod_event_attendees.c.event_id.in_(event_ids)
            ).order_by(pod_event_attendees.c.event_id, pod_event_attendees.c.is_lead.desc(), pod_event_attendees.c.id)).mappings().all() if event_ids else []
            task_rows = connection.execute(select(pod_tasks).where(pod_tasks.c.pod_id == pod).order_by(
                pod_tasks.c.due_date, pod_tasks.c.id
            )).mappings().all()
            critical_rows = connection.execute(select(pod_critical_items).where(and_(
                pod_critical_items.c.pod_id == pod,
                pod_critical_items.c.status != "Resolved",
            )).order_by(pod_critical_items.c.severity.desc(), pod_critical_items.c.due_date)).mappings().all()
            milestone_end = end if period == "month" else start + timedelta(days=45)
            milestone_rows = connection.execute(select(pod_milestones).where(and_(
                pod_milestones.c.pod_id == pod,
                pod_milestones.c.milestone_date >= start,
                pod_milestones.c.milestone_date < milestone_end,
            )).order_by(pod_milestones.c.milestone_date)).mappings().all()
            focus_row = connection.execute(select(pod_focus).where(and_(
                pod_focus.c.pod_id == pod,
                pod_focus.c.period_type == period,
                pod_focus.c.period_start == start,
            )).order_by(pod_focus.c.updated_at.desc())).mappings().first()
            if focus_row is None:
                focus_row = connection.execute(select(pod_focus).where(and_(
                    pod_focus.c.pod_id == pod, pod_focus.c.period_type == period,
                )).order_by(pod_focus.c.period_start.desc())).mappings().first()
            relationship_rows = connection.execute(select(pod_relationship_signals).where(and_(
                pod_relationship_signals.c.pod_id == pod,
                pod_relationship_signals.c.status == "Open",
            ))).mappings().all()
            # Recency is calculated from persisted meetings. The signal table's
            # legacy days_since_contact value is intentionally not a cockpit input.
            relationship_as_of = datetime.now(timezone.utc)
            relationship_meeting_rows = connection.execute(select(
                pod_events.c.id,
                pod_events.c.stakeholder_id,
                pod_events.c.title,
                pod_events.c.start_at,
                pod_events.c.source_meeting_id,
            ).where(and_(
                pod_events.c.pod_id == pod,
                pod_events.c.is_client.is_(True),
                pod_events.c.stakeholder_id.is_not(None),
                pod_events.c.start_at < relationship_as_of,
                pod_events.c.status.not_in(("Cancelled", "Canceled")),
            )).order_by(pod_events.c.start_at.desc())).mappings().all()
            context_rows = connection.execute(select(pod_opportunity_contexts).where(
                pod_opportunity_contexts.c.pod_id == pod
            )).mappings().all()

        attendees_by_event: dict[str, list[str]] = defaultdict(list)
        attendee_ids_by_event: dict[str, list[str]] = defaultdict(list)
        for attendee in attendee_rows:
            attendees_by_event[attendee["event_id"]].append(attendee["attendee_name"])
            if attendee["employee_id"]:
                attendee_ids_by_event[attendee["event_id"]].append(attendee["employee_id"])

        all_events = {}
        for row in display_event_rows.values():
            person = stakeholders.get(row["stakeholder_id"])
            opportunity = opportunities_by_id.get(row["opportunity_id"])
            canonical = self.repository.meetings.get(row["source_meeting_id"])
            all_events[row["id"]] = {
                "id": row["id"],
                "pod": pod,
                "meetingId": row["source_meeting_id"] or row["id"],
                "type": row["event_type"],
                "title": row["title"],
                "start": _eastern_iso(row["start_at"]),
                "end": _eastern_iso(row["end_at"]),
                "person": person.name if person else "Account team",
                "stakeholderId": person.id if person else None,
                "stakeholderIds": [person.id] if person else [],
                "division": person.division if person else pod,
                "unit": row["business_unit"],
                "opportunity": opportunity.name if opportunity else None,
                "opportunityId": opportunity.id if opportunity else None,
                "importance": row["importance"],
                "status": row["status"],
                "prep": bool(row["prep_required"]),
                "capcoAttendees": attendees_by_event[row["id"]],
                "capcoAttendeeIds": attendee_ids_by_event[row["id"]],
                "previousEngagement": row["previous_engagement"],
                "openActions": row["open_actions"] or [],
                "discussionTopics": row["discussion_topics"] or [],
                "tags": self._tags(
                    row.get("tags"),
                    canonical.tags if canonical else None,
                    person.tags if person else None,
                    opportunity.tags if opportunity else None,
                    self._semantic_tags(row["title"], row["previous_engagement"], row["discussion_topics"]),
                ),
            }
        events = [all_events[row["id"]] for row in event_rows]
        upcoming_prep = [all_events[row["id"]] for row in prep_event_rows]

        latest_meetings: dict[str, dict] = {}

        def remember_meeting(stakeholder_id, meeting_date, meeting_id, title):
            if stakeholder_id not in stakeholders or not meeting_date:
                return
            if isinstance(meeting_date, datetime):
                meeting_day = (
                    meeting_date.astimezone(ZoneInfo("America/New_York")).date()
                    if meeting_date.tzinfo
                    else meeting_date.date()
                )
            else:
                meeting_day = meeting_date
            current = latest_meetings.get(stakeholder_id)
            if current is None or meeting_day > current["date"]:
                latest_meetings[stakeholder_id] = {
                    "date": meeting_day,
                    "id": meeting_id,
                    "title": title,
                }

        for row in relationship_meeting_rows:
            remember_meeting(
                row["stakeholder_id"], row["start_at"],
                row["source_meeting_id"] or row["id"], row["title"],
            )

        # Canonical meetings can link several stakeholders even though a calendar
        # event has one display owner, so include every canonical meeting link.
        today = date.today()
        relationship_now = datetime.now(timezone.utc)
        for meeting in self.repository.list_meetings():
            meeting_point = meeting.meeting_date
            if meeting_point.tzinfo is None:
                meeting_point = meeting_point.replace(tzinfo=timezone.utc)
            if meeting_point > relationship_now:
                continue
            for stakeholder_id in meeting.stakeholder_ids:
                remember_meeting(stakeholder_id, meeting.meeting_date, meeting.id, meeting.subject)

        people = []
        for person in sorted(stakeholders.values(), key=lambda item: item.name):
            latest = latest_meetings.get(person.id)
            people.append({
                "id": person.id,
                "pod": pod,
                "name": person.name,
                "title": person.title,
                "division": person.division,
                "unit": person.business_unit,
                "role": "Buyer · Budget Holder" if person.is_budget_holder else "Buyer" if person.is_buyer else "Influencer",
                "relationship": person.relationship_strength,
                "capcoOwner": person.capco_owner,
                "capcoOwnerEmployeeId": person.capco_owner_employee_id,
                "interests": person.tags,
                "tags": self._tags(person.tags, self._semantic_tags(person.title, person.business_unit)),
                "lastMeeting": latest["date"].isoformat() if latest else None,
                "nextMeeting": person.next_meeting.isoformat() if person.next_meeting else None,
            })

        context_by_opportunity = {row["opportunity_id"]: row for row in context_rows}
        opportunity_views = []
        for opportunity in opportunity_models:
            linked_person = next((stakeholders.get(value) for value in opportunity.stakeholder_ids if value in stakeholders), None)
            context = context_by_opportunity.get(opportunity.id)
            opportunity_views.append({
                "id": opportunity.id,
                "pod": pod,
                "name": opportunity.name,
                "description": context["commercial_context"] if context else opportunity.description,
                "value": opportunity.estimated_value,
                "probability": opportunity.probability,
                "stage": opportunity.stage,
                "buyer": linked_person.name if linked_person else "Account sponsor",
                "stakeholderId": linked_person.id if linked_person else None,
                "owner": opportunity.owner,
                "ownerEmployeeId": opportunity.owner_employee_id,
                "movement": context["latest_movement"] if context else "Account record updated",
                "nextStep": context["recommended_next_step"] if context else "Confirm next client commitment",
                "close": opportunity.target_close_date.strftime("%b %d") if opportunity.target_close_date else "TBD",
                "tags": self._tags(opportunity.tags, linked_person.tags if linked_person else None, self._semantic_tags(opportunity.name, opportunity.description)),
            })
        opportunity_views.sort(key=lambda item: item["value"] * item["probability"], reverse=True)

        task_views = [self._task_view(row, stakeholders, opportunities_by_id) for row in task_rows]
        critical_views = []
        for row in critical_rows:
            person = stakeholders.get(row["stakeholder_id"])
            opportunity = opportunities_by_id.get(row["opportunity_id"])
            critical_views.append({
                "id": row["id"], "pod": pod, "severity": row["severity"], "type": row["item_type"],
                "title": row["title"], "description": row["description"], "owner": row["owner_id"],
                "capcoOwner": row["owner_id"],
                "capcoOwnerEmployeeId": row["owner_employee_id"],
                "msOwner": person.name if person else None,
                "msOwnerTitle": person.title if person else None,
                "due": row["due_date"].isoformat() if row["due_date"] else None, "status": row["status"],
                "stakeholder": person.name if person else None, "stakeholderId": person.id if person else None,
                "opportunity": opportunity.name if opportunity else None, "opportunityId": opportunity.id if opportunity else None,
                "tags": self._tags(row.get("tags"), person.tags if person else None, opportunity.tags if opportunity else None, self._semantic_tags(row["title"], row["description"], row["item_type"])),
            })

        signal_by_stakeholder = {row["stakeholder_id"]: row for row in relationship_rows}
        relationships = []
        for person in stakeholders.values():
            latest = latest_meetings.get(person.id)
            last_meeting = latest["date"] if latest else None
            days = max(0, (today - last_meeting).days) if last_meeting else None
            needs_attention = days is None or days >= 30
            importance = "High" if days is None or days >= 60 else "Medium" if days >= 30 else "Low"
            trend = "No meeting" if days is None else "Weakening" if days >= 60 else "Watch" if days >= 30 else "Current"
            source_signal = signal_by_stakeholder.get(person.id)
            signal = (
                "No linked client meeting is recorded."
                if last_meeting is None
                else f"Latest linked client meeting: {last_meeting.strftime('%b')} {last_meeting.day}, {last_meeting.year}."
            )
            relationships.append({
                "id": source_signal["id"] if source_signal else f"{person.id}-meeting-recency",
                "pod": pod,
                "stakeholder": person.name,
                "stakeholderId": person.id,
                "title": f"{person.title} · {person.business_unit}",
                "days": days,
                "lastMeeting": last_meeting.isoformat() if last_meeting else None,
                "latestMeetingId": latest["id"] if latest else None,
                "latestMeetingTitle": latest["title"] if latest else None,
                "importance": importance,
                "signal": signal,
                "contextSignal": source_signal["signal"] if source_signal else None,
                "relationship": person.relationship_strength,
                "riskScore": days if days is not None else 10000,
                "trend": trend,
                "needsAttention": needs_attention,
                "recencySource": "Latest persisted client meeting",
                "tags": self._tags(
                    person.tags,
                    self._semantic_tags(source_signal["signal"] if source_signal else None, person.business_unit),
                ),
            })
        relationships.sort(key=lambda item: item["riskScore"], reverse=True)

        milestones = []
        for row in milestone_rows:
            person = stakeholders.get(row["stakeholder_id"])
            milestones.append({
                "id": row["id"], "pod": pod, "type": row["milestone_type"], "title": row["title"],
                "date": row["milestone_date"].strftime("%b %d") if hasattr(row["milestone_date"], "strftime") else str(row["milestone_date"]),
                "dateIso": row["milestone_date"].isoformat(), "description": row["description"], "owner": row["owner_id"],
                "stakeholder": person.name if person else None, "stakeholderId": person.id if person else None,
                "opportunityId": row["opportunity_id"],
                "tags": self._tags(
                    row.get("tags"),
                    person.tags if person else None,
                    opportunities_by_id[row["opportunity_id"]].tags if row["opportunity_id"] in opportunities_by_id else None,
                    self._semantic_tags(row["title"], row["description"], row["milestone_type"]),
                ),
            })
        # Windows does not support the %-d strftime modifier.
        for milestone in milestones:
            parsed = date.fromisoformat(milestone["dateIso"])
            milestone["date"] = f"{parsed.strftime('%b')} {parsed.day}"

        return {
            "people": people,
            "meetings": events,
            "upcomingPrep": upcoming_prep,
            "opportunities": opportunity_views,
            "criticalItems": critical_views,
            "tasks": task_views,
            "relationships": relationships,
            "milestones": milestones,
            "focus": list(focus_row["content"]) if focus_row else [],
            "health": [],
        }

    @staticmethod
    def _score_status(value: int) -> str:
        return "Strong" if value >= 80 else "Watch" if value >= 60 else "Action"

    def _computed_health(self, view: dict, as_of: date) -> list[dict]:
        pod_count = max(1, len({item.get("pod") for key in ("people", "tasks", "criticalItems") for item in view.get(key, []) if item.get("pod")}))
        critical = view.get("criticalItems", [])
        tasks = view.get("tasks", [])
        relationships = view.get("relationships", [])
        people = view.get("people", [])

        red = sum(item.get("severity") == "RED" for item in critical)
        amber = sum(item.get("severity") == "AMBER" for item in critical)
        open_tasks = [item for item in tasks if item.get("status") != "Done"]
        overdue = sum(bool(item.get("due")) and item["due"] < as_of.isoformat() for item in open_tasks)
        delivery_penalty = min(36, round((red * 8 + amber * 3) / pod_count)) + round(25 * overdue / max(1, len(open_tasks)))
        delivery = max(0, min(100, 100 - delivery_penalty))

        strength_values = {"Strong": 95, "Medium": 75, "Developing": 52, "Unknown": 40}
        relationship_average = round(sum(strength_values.get(item.get("relationship"), 50) for item in relationships) / max(1, len(relationships))) if relationships else 50
        stale = sum(item.get("days") is None or item["days"] >= 45 for item in relationships)
        sentiment = max(0, min(100, relationship_average - round(15 * stale / max(1, len(relationships)))))

        staffing_risks = sum(any(term in f"{item.get('type', '')} {item.get('title', '')}".casefold() for term in ("staff", "coverage", "resource")) for item in critical)
        unassigned = sum(not item.get("capcoOwner") for item in people)
        staffing = max(0, min(100, 100 - min(36, round(12 * staffing_risks / pod_count)) - round(20 * unassigned / max(1, len(people)))))

        owner_coverage = sum(bool(item.get("capcoOwner")) for item in people) / max(1, len(people))
        known_relationships = sum(item.get("relationship") not in (None, "Unknown") for item in relationships) / max(1, len(relationships))
        recent_relationships = sum(item.get("days") is not None and item["days"] <= 60 for item in relationships) / max(1, len(relationships))
        coverage = max(0, min(100, round(55 * owner_coverage + 25 * known_relationships + 20 * recent_relationships)))

        metrics = [
            ("delivery-confidence", "Delivery confidence", delivery,
             f"{red} red and {amber} amber open risks; {overdue} of {len(open_tasks)} open actions overdue.",
             "100 − severity penalty − overdue/open action penalty"),
            ("client-sentiment", "Client sentiment", sentiment,
             f"{len(relationships)} stakeholder relationships; {stale} have no meeting or were last met 45+ days ago.",
             "average relationship strength − stale-meeting penalty"),
            ("staffing-readiness", "Staffing readiness", staffing,
             f"{staffing_risks} staffing or coverage risks; {unassigned} of {len(people)} stakeholders lack a Capco owner.",
             "100 − staffing-risk density − unassigned-owner rate"),
            ("coverage-strength", "Coverage strength", coverage,
             f"{round(owner_coverage * 100)}% owner coverage; {round(recent_relationships * 100)}% of stakeholders were met within 60 days.",
             "55% owner coverage + 25% known relationships + 20% meeting recency"),
        ]
        return [{
            "id": metric_id,
            "label": label,
            "value": value,
            "status": self._score_status(value),
            "detail": detail,
            "formula": formula,
            "asOf": as_of.isoformat(),
            "dataSource": "Live SQL operating records",
        } for metric_id, label, value, detail, formula in metrics]

    @staticmethod
    def _commitments(view: dict) -> list[dict]:
        priority_by_severity = {
            "RED": "Critical",
            "AMBER": "High",
            "YELLOW": "Medium",
        }
        commitments = [{
            "id": item["id"],
            "pod": item["pod"],
            "deadline": item["due"],
            "title": item["title"],
            "category": (item.get("type") or "Critical").replace("_", " ").title(),
            "priority": priority_by_severity.get(item.get("severity"), "Standard"),
            "owner": item.get("capcoOwner") or item.get("owner") or "Account team",
            "stakeholder": item.get("msOwner") or item.get("stakeholder"),
            "stakeholderId": item.get("stakeholderId"),
            "opportunityId": item.get("opportunityId"),
            "status": item.get("status") or "Open",
            "sourceType": "critical",
            "tags": list(item.get("tags") or []),
        } for item in view.get("criticalItems", []) if item.get("due")]
        commitments.extend({
            "id": item["id"],
            "pod": item["pod"],
            "deadline": item["dateIso"],
            "title": item["title"],
            "category": (item.get("type") or "Milestone").replace("_", " ").title(),
            "priority": "Standard",
            "owner": item.get("owner") or "Account team",
            "stakeholder": item.get("stakeholder"),
            "stakeholderId": item.get("stakeholderId"),
            "opportunityId": item.get("opportunityId"),
            "status": "Upcoming",
            "sourceType": "milestone",
            "tags": list(item.get("tags") or []),
        } for item in view.get("milestones", []) if item.get("dateIso"))
        priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Standard": 3}
        return sorted(commitments, key=lambda item: (
            item["deadline"],
            priority_order.get(item["priority"], 4),
            item.get("title") or "",
        ))

    @staticmethod
    def _summary(view: dict, as_of: date) -> dict:
        people_by_id = {item["id"]: item for item in view.get("people", [])}
        meeting_people = {
            item.get("stakeholderId") for item in view.get("meetings", []) if item.get("stakeholderId")
        }
        buyers = sum("Buyer" in people_by_id[item]["role"] for item in meeting_people if item in people_by_id)
        actions = [item for item in view.get("tasks", []) if item.get("status") != "Done"]
        overdue = sum(bool(item.get("due")) and item["due"] < as_of.isoformat() for item in actions)
        opportunities = view.get("opportunities", [])
        attention = view.get("relationshipAttention", [])
        commitments = view.get("commitments", [])
        return {
            "meetingCount": len(view.get("meetings", [])),
            "buyerCount": buyers,
            "influencerCount": max(0, len(meeting_people) - buyers),
            "deadlineCount": len(commitments),
            "urgentDeadlineCount": sum(item["priority"] in ("Critical", "High") for item in commitments),
            "openActionCount": len(actions),
            "overdueActionCount": overdue,
            "pipelineValue": sum(item.get("value", 0) for item in opportunities),
            "weightedPipelineValue": round(sum(
                item.get("value", 0) * item.get("probability", 0) / 100 for item in opportunities
            )),
            "relationshipAttentionCount": len(attention),
            "highRelationshipAttentionCount": sum(item.get("importance") == "High" for item in attention),
        }

    def _finalize_dashboard(self, view: dict, tag: str | None) -> dict:
        filterable = ("people", "meetings", "upcomingPrep", "opportunities", "criticalItems", "tasks", "relationships", "milestones")
        related_tags: dict[str, list[str]] = defaultdict(list)
        for key in filterable:
            for item in view.get(key, []):
                if item.get("stakeholderId"):
                    related_tags[item["stakeholderId"]].extend(item.get("tags", []))
        for opportunity in view.get("opportunities", []):
            if opportunity.get("stakeholderId"):
                related_tags[opportunity["stakeholderId"]].extend(opportunity.get("tags", []))
        for person in view.get("people", []):
            person["tags"] = self._tags(person.get("tags"), related_tags.get(person["id"]))
            person["interests"] = list(person["tags"])
        people_by_id = {item["id"]: item for item in view.get("people", [])}
        opportunities_by_id = {item["id"]: item for item in view.get("opportunities", [])}
        for key in filterable:
            for item in view.get(key, []):
                person = people_by_id.get(item.get("stakeholderId"))
                opportunity = opportunities_by_id.get(item.get("opportunityId"))
                item["tags"] = self._tags(
                    item.get("tags"),
                    person.get("tags") if person else None,
                    opportunity.get("tags") if opportunity else None,
                )
        tag_options = self._tags(*(item.get("tags") for key in filterable for item in view.get(key, [])))
        active_tag = tag.strip() if tag and tag.strip() and tag.casefold() != "all" else None
        if active_tag:
            needle = active_tag.casefold()
            for key in filterable:
                view[key] = [item for item in view.get(key, []) if needle in {value.casefold() for value in item.get("tags", [])}]
        view["tagOptions"] = tag_options
        view["activeTag"] = active_tag or "All"
        view["commitments"] = self._commitments(view)
        view["relationshipAttention"] = [
            item for item in view.get("relationships", []) if item.get("needsAttention")
        ]
        as_of = date.today()
        view["health"] = self._computed_health(view, as_of)
        view["summary"] = self._summary(view, as_of)
        return view

    def dashboard(self, pod: str, period: str, period_start: date | None = None, tag: str | None = None) -> dict:
        self._validate_pod(pod)
        if pod != "All":
            return self._finalize_dashboard(self._single_dashboard(pod, period, period_start), tag)

        dashboards = [self._single_dashboard(value, period, period_start) for value in POD_STRUCTURE]
        collection_keys = ("people", "meetings", "upcomingPrep", "opportunities", "criticalItems", "tasks", "relationships", "milestones")
        combined = {key: [item for dashboard in dashboards for item in dashboard.get(key, [])] for key in collection_keys}
        combined["focus"] = [f"{pod_name}: {priority}" for pod_name, dashboard in zip(POD_STRUCTURE, dashboards) for priority in dashboard.get("focus", [])]
        combined["meetings"].sort(key=lambda item: item["start"])
        combined["upcomingPrep"].sort(key=lambda item: item["start"])
        combined["relationships"].sort(key=lambda item: (item.get("riskScore", 0), item.get("days", 0)), reverse=True)
        combined["opportunities"].sort(key=lambda item: item["value"] * item["probability"], reverse=True)
        return self._finalize_dashboard(combined, tag)
