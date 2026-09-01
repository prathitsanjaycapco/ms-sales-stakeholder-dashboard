from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from statistics import mean
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import (
    JSON, CheckConstraint, Column, Date, DateTime, Float, ForeignKey, Index, Integer,
    MetaData, Numeric, String, Table, Text, and_, func, insert, inspect, select, update,
)
from sqlalchemy.engine import Engine

from .canonical_schema import stakeholders
from .executive_store import employees, engagement_assignments, engagements
from .repository import ConflictError, NotFoundError


resourcing_metadata = MetaData()

resource_requirements = Table(
    "resource_requirements", resourcing_metadata,
    Column("id", String(140), primary_key=True),
    Column("pod_id", String(80), nullable=False),
    Column("division_id", String(160), nullable=False),
    Column("business_unit_id", String(220), nullable=False),
    Column("engagement_id", String(120), nullable=False),
    Column("title", String(180), nullable=False),
    Column("role", String(120), nullable=False),
    Column("description", Text, nullable=False, default=""),
    Column("requested_headcount", Integer, nullable=False),
    Column("level", String(80), nullable=False),
    Column("location", String(120), nullable=False),
    Column("required_skills", JSON, nullable=False, default=list),
    Column("preferred_skills", JSON, nullable=False, default=list),
    Column("target_start_date", Date, nullable=False),
    Column("priority", String(20), nullable=False),
    Column("status", String(30), nullable=False),
    Column("request_owner_capco_employee_id", String(120), nullable=False),
    Column("client_stakeholder_id", String(180), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("closed_at", DateTime(timezone=True)),
    CheckConstraint("requested_headcount > 0", name="ck_resource_requirement_headcount"),
    CheckConstraint("priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')", name="ck_resource_requirement_priority"),
    CheckConstraint("status IN ('DRAFT', 'OPEN', 'SOURCING', 'PARTIALLY_FILLED', 'ON_HOLD', 'FILLED', 'CANCELLED')", name="ck_resource_requirement_status"),
)
Index("idx_resource_requirements_scope", resource_requirements.c.pod_id, resource_requirements.c.status, resource_requirements.c.target_start_date)
Index("idx_resource_requirements_engagement", resource_requirements.c.engagement_id)

candidates = Table(
    "resourcing_candidates", resourcing_metadata,
    Column("id", String(140), primary_key=True),
    Column("resource_requirement_id", String(140), ForeignKey("resource_requirements.id", name="fk_candidate_requirement", ondelete="CASCADE"), nullable=False),
    Column("capco_employee_id", String(120)),
    Column("candidate_type", String(30), nullable=False),
    Column("first_name", String(90), nullable=False),
    Column("last_name", String(90), nullable=False),
    Column("email", String(240)),
    Column("level", String(80), nullable=False),
    Column("location", String(120), nullable=False),
    Column("skills", JSON, nullable=False, default=list),
    Column("resume_reference", String(500)),
    Column("stage", String(40), nullable=False),
    Column("capco_reviewer_id", String(120), nullable=False),
    Column("ms_reviewer_stakeholder_id", String(180)),
    Column("date_identified", Date, nullable=False),
    Column("date_submitted_to_ms", Date),
    Column("expected_start_date", Date),
    Column("match_score", Integer),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("match_score IS NULL OR (match_score >= 0 AND match_score <= 100)", name="ck_candidate_match_score"),
)
Index("idx_resourcing_candidates_requirement", candidates.c.resource_requirement_id, candidates.c.stage)
Index("uq_resourcing_candidate_employee_requirement", candidates.c.capco_employee_id, candidates.c.resource_requirement_id, unique=True)

candidate_stage_history = Table(
    "candidate_stage_history", resourcing_metadata,
    Column("id", String(160), primary_key=True),
    Column("candidate_id", String(140), ForeignKey("resourcing_candidates.id", name="fk_stage_history_candidate", ondelete="CASCADE"), nullable=False),
    Column("stage", String(40), nullable=False),
    Column("entered_at", DateTime(timezone=True), nullable=False),
    Column("exited_at", DateTime(timezone=True)),
    Column("changed_by_employee_id", String(120)),
    Column("note", Text, nullable=False, default=""),
)
Index("idx_candidate_stage_history_timing", candidate_stage_history.c.candidate_id, candidate_stage_history.c.entered_at)

candidate_interviews = Table(
    "candidate_interviews", resourcing_metadata,
    Column("id", String(150), primary_key=True),
    Column("candidate_id", String(140), ForeignKey("resourcing_candidates.id", name="fk_interview_candidate", ondelete="CASCADE"), nullable=False),
    Column("interview_round", Integer, nullable=False),
    Column("scheduled_at", DateTime(timezone=True), nullable=False),
    Column("interview_type", String(60), nullable=False),
    Column("ms_interviewer_stakeholder_ids", JSON, nullable=False, default=list),
    Column("capco_attendee_ids", JSON, nullable=False, default=list),
    Column("status", String(30), nullable=False),
    Column("feedback", Text, nullable=False, default=""),
    Column("recommendation", String(60)),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
Index("idx_candidate_interviews_candidate", candidate_interviews.c.candidate_id, candidate_interviews.c.scheduled_at)

candidate_offers = Table(
    "candidate_offers", resourcing_metadata,
    Column("id", String(150), primary_key=True),
    Column("candidate_id", String(140), ForeignKey("resourcing_candidates.id", name="fk_offer_candidate", ondelete="CASCADE"), nullable=False, unique=True),
    Column("proposed_rate", Numeric(12, 2)),
    Column("agreed_rate", Numeric(12, 2)),
    Column("rate_currency", String(3), nullable=False),
    Column("offer_status", String(30), nullable=False),
    Column("offer_date", Date),
    Column("accepted_date", Date),
    Column("declined_date", Date),
    Column("notes", Text, nullable=False, default=""),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("proposed_rate IS NULL OR proposed_rate >= 0", name="ck_offer_proposed_rate"),
    CheckConstraint("agreed_rate IS NULL OR agreed_rate >= 0", name="ck_offer_agreed_rate"),
)

onboarding_records = Table(
    "onboarding_records", resourcing_metadata,
    Column("id", String(150), primary_key=True),
    Column("candidate_id", String(140), ForeignKey("resourcing_candidates.id", name="fk_onboarding_candidate", ondelete="CASCADE"), nullable=False, unique=True),
    Column("expected_start_date", Date),
    Column("actual_start_date", Date),
    Column("overall_status", String(30), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
Index("idx_onboarding_expected_start", onboarding_records.c.overall_status, onboarding_records.c.expected_start_date)

onboarding_steps = Table(
    "onboarding_steps", resourcing_metadata,
    Column("id", String(170), primary_key=True),
    Column("onboarding_record_id", String(150), ForeignKey("onboarding_records.id", name="fk_onboarding_step_record", ondelete="CASCADE"), nullable=False),
    Column("step_type", String(80), nullable=False),
    Column("step_label", String(180), nullable=False),
    Column("step_order", Integer, nullable=False),
    Column("responsible_party", String(30), nullable=False),
    Column("owner_id", String(180)),
    Column("status", String(30), nullable=False),
    Column("started_at", DateTime(timezone=True)),
    Column("completed_at", DateTime(timezone=True)),
    Column("target_completion_date", Date),
    Column("blocked_since", DateTime(timezone=True)),
    Column("blocker_reason", Text),
    Column("notes", Text, nullable=False, default=""),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
Index("idx_onboarding_steps_record", onboarding_steps.c.onboarding_record_id, onboarding_steps.c.step_order, unique=True)
Index("idx_onboarding_steps_queue", onboarding_steps.c.status, onboarding_steps.c.responsible_party)

resourcing_events = Table(
    "resourcing_events", resourcing_metadata,
    Column("id", String(180), primary_key=True),
    Column("requirement_id", String(140), ForeignKey("resource_requirements.id", name="fk_resourcing_event_requirement", ondelete="CASCADE")),
    Column("candidate_id", String(140), ForeignKey("resourcing_candidates.id", name="fk_resourcing_event_candidate", ondelete="CASCADE")),
    Column("onboarding_record_id", String(150), ForeignKey("onboarding_records.id", name="fk_resourcing_event_onboarding", ondelete="CASCADE")),
    Column("event_type", String(50), nullable=False),
    Column("headline", String(240), nullable=False),
    Column("detail", Text, nullable=False, default=""),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("actor_employee_id", String(120)),
)
Index("idx_resourcing_events_candidate", resourcing_events.c.candidate_id, resourcing_events.c.occurred_at)

resourcing_seed_registry = Table(
    "resourcing_seed_registry", resourcing_metadata,
    Column("id", String(80), primary_key=True),
    Column("seeded_at", DateTime(timezone=True), nullable=False),
    Column("row_count", Integer, nullable=False),
)

WORKFLOW = [
    ("PT_ID_APPROVED", "PT ID Approved", "MORGAN_STANLEY"),
    ("PROFILE_WORKER_OPENED", "Profile Worker Opened", "CAPCO"),
    ("PROFILE_WORKER_APPROVED", "Profile Worker Approved", "MORGAN_STANLEY"),
    ("REHIRE_ELIGIBILITY", "Rehire Eligibility", "MORGAN_STANLEY"),
    ("FORMS_UPLOADED", "Forms Uploaded", "CAPCO"),
    ("FORMS_APPROVED", "Forms Approved", "MORGAN_STANLEY"),
    ("FINGERPRINT_APPOINTMENT", "Fingerprint Appointment Complete", "CAPCO"),
    ("FINGERPRINTS_CLEARED", "Fingerprints Cleared", "MORGAN_STANLEY"),
    ("MSID_ACTIVATION", "Attestation / MSID Activation", "MORGAN_STANLEY"),
    ("READY_TO_START", "Ready to Start", "CAPCO"),
    ("STARTED", "Started", "CAPCO"),
]
ACTIVE_REQUIREMENTS = {"OPEN", "SOURCING", "PARTIALLY_FILLED"}
ACTIVE_CANDIDATES = {"IDENTIFIED", "CAPCO_REVIEW", "SUBMITTED_TO_MS", "MS_REVIEW", "INTERVIEW_SCHEDULED", "INTERVIEWING", "OFFER", "SELECTED"}
ACCOUNT_TIMEZONE = ZoneInfo("America/New_York")


def utcnow():
    return datetime.now(timezone.utc)


def business_today():
    return utcnow().astimezone(ACCOUNT_TIMEZONE).date()


def elapsed_days(start, end=None):
    if not start:
        return 0
    end = end or utcnow()
    if isinstance(start, date) and not isinstance(start, datetime):
        start = datetime.combine(start, time.min, tzinfo=timezone.utc)
    if isinstance(end, date) and not isinstance(end, datetime):
        end = datetime.combine(end, time.min, tzinfo=timezone.utc)
    if start.tzinfo is None: start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None: end = end.replace(tzinfo=timezone.utc)
    return max(0, (end.astimezone(ACCOUNT_TIMEZONE).date() - start.astimezone(ACCOUNT_TIMEZONE).date()).days)


class ResourcingStore:
    seed_id = "resourcing-lifecycle-v1"

    def __init__(self, engine: Engine, repository, *, seed_demo_data=True, auto_create_schema=True):
        self.engine = engine
        self.repository = repository
        if auto_create_schema:
            resourcing_metadata.create_all(engine)
        elif not inspect(engine).has_table("resource_requirements"):
            raise RuntimeError("Resourcing schema is missing; run Alembic migrations before startup")
        if seed_demo_data:
            self._seed_if_needed()
            self._reconcile_demo_lifecycle()

    def _reconcile_demo_lifecycle(self):
        """Keep long-lived development databases aligned with the current synthetic scenario."""
        if not inspect(self.engine).has_table("resourcing_candidates"):
            return
        now, today = utcnow(), date.today()
        selected_ids = {"candidate-001", "candidate-002", "candidate-006", "candidate-013", "candidate-022"}
        with self.engine.begin() as connection:
            for candidate_id in selected_ids:
                if connection.execute(select(candidates.c.id).where(candidates.c.id == candidate_id)).scalar_one_or_none():
                    connection.execute(update(candidates).where(candidates.c.id == candidate_id).values(stage="SELECTED", updated_at=now))
                    connection.execute(update(candidate_stage_history).where(and_(candidate_stage_history.c.candidate_id == candidate_id, candidate_stage_history.c.exited_at.is_(None))).values(stage="SELECTED"))
                    connection.execute(update(candidate_offers).where(candidate_offers.c.candidate_id == candidate_id).values(offer_status="OFFER_ACCEPTED", accepted_date=today, updated_at=now))
            if connection.execute(select(candidates.c.id).where(candidates.c.id == "candidate-009")).scalar_one_or_none():
                connection.execute(update(candidates).where(candidates.c.id == "candidate-009").values(stage="REJECTED", updated_at=now))
                connection.execute(update(candidate_stage_history).where(and_(candidate_stage_history.c.candidate_id == "candidate-009", candidate_stage_history.c.exited_at.is_(None))).values(stage="REJECTED"))
            if connection.execute(select(candidates.c.id).where(candidates.c.id == "candidate-021")).scalar_one_or_none():
                connection.execute(update(candidates).where(candidates.c.id == "candidate-021").values(stage="OFFER", updated_at=now))
                connection.execute(update(candidate_stage_history).where(and_(candidate_stage_history.c.candidate_id == "candidate-021", candidate_stage_history.c.exited_at.is_(None))).values(stage="OFFER"))
                if connection.execute(select(candidate_offers.c.id).where(candidate_offers.c.candidate_id == "candidate-021")).scalar_one_or_none() is None:
                    connection.execute(insert(candidate_offers).values(id="offer-021", candidate_id="candidate-021", proposed_rate=210.0, agreed_rate=None, rate_currency="USD", offer_status="RATE_NEGOTIATION", offer_date=today - timedelta(days=2), accepted_date=None, declined_date=None, notes="Commercial details restricted.", created_at=now - timedelta(days=2), updated_at=now))
            if connection.execute(select(onboarding_records.c.id).where(onboarding_records.c.id == "onboarding-001")).scalar_one_or_none():
                connection.execute(update(onboarding_records).where(onboarding_records.c.id == "onboarding-001").values(actual_start_date=today - timedelta(days=5), overall_status="COMPLETE", updated_at=now))
                connection.execute(update(onboarding_steps).where(onboarding_steps.c.onboarding_record_id == "onboarding-001").values(status="COMPLETE", completed_at=now - timedelta(days=5), blocked_since=None, blocker_reason=None, updated_at=now))
                candidate = connection.execute(select(candidates).where(candidates.c.id == "candidate-001")).mappings().one_or_none()
                requirement = connection.execute(select(resource_requirements).where(resource_requirements.c.id == "req-001")).mappings().one_or_none()
                if candidate and requirement and candidate["capco_employee_id"] and connection.execute(select(engagement_assignments.c.id).where(engagement_assignments.c.id == "assignment-resourcing-001")).scalar_one_or_none() is None:
                    connection.execute(insert(engagement_assignments).values(id="assignment-resourcing-001", employee_id=candidate["capco_employee_id"], engagement_id=requirement["engagement_id"], allocation_percent=100, assignment_role=requirement["role"], billable=True, status="Active", start_date=today - timedelta(days=5), end_date=today + timedelta(days=175)))

    def _seed_if_needed(self):
        with self.engine.connect() as connection:
            seeded = connection.execute(select(resourcing_seed_registry.c.id).where(resourcing_seed_registry.c.id == self.seed_id)).scalar_one_or_none()
            projects = [dict(row) for row in connection.execute(select(engagements)).mappings()]
            employee_ids = list(connection.execute(select(employees.c.id).order_by(employees.c.id)).scalars())
        if seeded or not projects or not employee_ids:
            return
        today, now = date.today(), utcnow()
        role_specs = [
            ("Senior Data Engineer", "Data Engineer", 3, "Principal Consultant", "New York", ["Python", "Data Engineering", "AWS"], "CRITICAL", 42),
            ("AI Solution Architect", "AI Architect", 2, "Managing Principal", "New York", ["GenAI", "Architecture", "Azure"], "HIGH", 34),
            ("Business Analyst - Controls", "Business Analyst", 3, "Senior Consultant", "Charlotte", ["Business Analysis", "Controls", "Agile"], "HIGH", 23),
            ("Cloud Platform Engineer", "Cloud Engineer", 2, "Senior Consultant", "London", ["AWS", "Kubernetes", "Terraform"], "MEDIUM", 18),
            ("Program Delivery Lead", "Program Manager", 1, "Principal Consultant", "New York", ["Program Management", "Risk", "Leadership"], "CRITICAL", 39),
            ("Data Governance Lead", "Data Governance", 2, "Principal Consultant", "New York", ["Data Governance", "Collibra", "Lineage"], "HIGH", 28),
            ("Digital Product Analyst", "Business Analyst", 2, "Consultant", "Toronto", ["Product", "Analytics", "Agile"], "MEDIUM", 12),
            ("Investment Risk Quant", "Quant Analyst", 1, "Senior Consultant", "New York", ["Python", "Risk", "Statistics"], "HIGH", 31),
            ("Operating Model Consultant", "Operating Model", 2, "Senior Consultant", "London", ["Operating Model", "Change", "Process"], "MEDIUM", 16),
        ]
        requirements = []
        for index, spec in enumerate(role_specs):
            project = projects[index % len(projects)]
            client = next((person for person in self.repository.list_stakeholders(pod=project["pod_id"]) if person.business_unit == project["business_unit"]), None)
            client = client or next(iter(self.repository.list_stakeholders(pod=project["pod_id"])))
            title, role, requested, level, location, skills, priority, age = spec
            requirements.append({
                "id": f"req-{index + 1:03d}", "pod_id": project["pod_id"], "division_id": project["division_id"],
                "business_unit_id": project["business_unit_id"], "engagement_id": project["id"], "title": title, "role": role,
                "description": f"Delivery role supporting {project['name']}.", "requested_headcount": requested, "level": level,
                "location": location, "required_skills": skills, "preferred_skills": skills[-1:],
                "target_start_date": today + timedelta(days=10 + index * 5), "priority": priority,
                "status": "SOURCING", "request_owner_capco_employee_id": employee_ids[index % len(employee_ids)],
                "client_stakeholder_id": client.id, "created_at": now - timedelta(days=age), "updated_at": now,
            })

        people = [("Priya", "Nair"), ("John", "Lee"), ("Sarah", "Patel"), ("Amit", "Rao"), ("Michael", "Chen"), ("Tawfik", "Ahmed"), ("Elena", "Garcia"), ("Daniel", "Kim"), ("Maya", "Singh"), ("Noah", "Williams"), ("Sofia", "Brooks"), ("Liam", "Morgan"), ("Chloe", "Martin"), ("Ethan", "Scott"), ("Olivia", "Turner"), ("Lucas", "Hall"), ("Grace", "Young"), ("Arjun", "Mehta"), ("Nina", "Shah"), ("James", "Park"), ("Rita", "Desai"), ("Omar", "Khan"), ("Anna", "Wilson"), ("Leo", "Davis"), ("Ivy", "Zhang")]
        stages = ["SELECTED", "SELECTED", "INTERVIEWING", "MS_REVIEW", "INTERVIEW_SCHEDULED", "SELECTED", "CAPCO_REVIEW", "SUBMITTED_TO_MS", "REJECTED", "INTERVIEWING", "REJECTED", "CAPCO_REVIEW", "SELECTED", "SUBMITTED_TO_MS", "MS_REVIEW", "IDENTIFIED", "INTERVIEWING", "WITHDRAWN", "CAPCO_REVIEW", "MS_REVIEW", "OFFER", "SELECTED", "CAPCO_REVIEW", "SUBMITTED_TO_MS", "IDENTIFIED"]
        candidate_rows, histories, interviews, offers, events = [], [], [], [], []
        for index, ((first, last), stage) in enumerate(zip(people, stages)):
            req = requirements[index % len(requirements)]
            identified = today - timedelta(days=24 - index % 11)
            candidate_id = f"candidate-{index + 1:03d}"
            candidate_rows.append({
                "id": candidate_id, "resource_requirement_id": req["id"], "capco_employee_id": employee_ids[(index + 20) % len(employee_ids)] if index in {0, 1, 5} else None,
                "candidate_type": "INTERNAL_CAPCO" if index in {0, 1, 5} else "EXTERNAL", "first_name": first, "last_name": last,
                "email": f"{first.lower()}.{last.lower()}@example.test", "level": req["level"], "location": req["location"], "skills": req["required_skills"],
                "stage": stage, "capco_reviewer_id": req["request_owner_capco_employee_id"], "ms_reviewer_stakeholder_id": req["client_stakeholder_id"],
                "date_identified": identified, "date_submitted_to_ms": identified + timedelta(days=3) if stage not in {"IDENTIFIED", "CAPCO_REVIEW"} else None,
                "expected_start_date": today + timedelta(days=8 + index * 2) if stage in {"OFFER", "SELECTED"} else None,
                "match_score": 78 + (index * 7) % 20, "created_at": datetime.combine(identified, time.min, tzinfo=timezone.utc), "updated_at": now,
            })
            sequence = ["IDENTIFIED"]
            if stage != "IDENTIFIED": sequence.append("CAPCO_REVIEW")
            if stage not in {"IDENTIFIED", "CAPCO_REVIEW", "REJECTED", "WITHDRAWN"}: sequence += ["SUBMITTED_TO_MS", "MS_REVIEW"]
            if stage in {"INTERVIEW_SCHEDULED", "INTERVIEWING", "OFFER", "SELECTED"}: sequence.append("INTERVIEWING")
            if stage in {"OFFER", "SELECTED", "REJECTED", "WITHDRAWN"}: sequence.append(stage)
            entered = datetime.combine(identified, time.min, tzinfo=timezone.utc)
            for sequence_index, sequence_stage in enumerate(sequence):
                duration = [2, 3, 6, 4, 3, 2][min(sequence_index, 5)]
                histories.append({"id": f"history-{index + 1:03d}-{sequence_index + 1}", "candidate_id": candidate_id, "stage": sequence_stage,
                                  "entered_at": entered, "exited_at": entered + timedelta(days=duration) if sequence_index < len(sequence) - 1 else None,
                                  "changed_by_employee_id": req["request_owner_capco_employee_id"], "note": ""})
                entered += timedelta(days=duration)
            events.append({"id": f"event-identify-{index + 1:03d}", "requirement_id": req["id"], "candidate_id": candidate_id,
                           "event_type": "CANDIDATE_IDENTIFIED", "headline": "Candidate identified", "detail": f"{first} {last} entered the pipeline.",
                           "occurred_at": datetime.combine(identified, time.min, tzinfo=timezone.utc), "actor_employee_id": req["request_owner_capco_employee_id"]})
            if stage in {"INTERVIEW_SCHEDULED", "INTERVIEWING", "OFFER", "SELECTED"}:
                interviews.append({"id": f"interview-{index + 1:03d}", "candidate_id": candidate_id, "interview_round": 1 + index % 2,
                                   "scheduled_at": now + timedelta(days=(index % 5) - 2), "interview_type": "Video", "ms_interviewer_stakeholder_ids": [req["client_stakeholder_id"]],
                                   "capco_attendee_ids": [req["request_owner_capco_employee_id"]], "status": "COMPLETED" if stage in {"OFFER", "SELECTED"} else "SCHEDULED",
                                   "feedback": "Strong functional and delivery alignment." if stage in {"OFFER", "SELECTED"} else "", "recommendation": "PROCEED" if stage in {"OFFER", "SELECTED"} else None,
                                   "created_at": now - timedelta(days=5), "updated_at": now})
            if stage in {"OFFER", "SELECTED"}:
                offers.append({"id": f"offer-{index + 1:03d}", "candidate_id": candidate_id, "proposed_rate": 190.0 + index,
                               "agreed_rate": 185.0 + index if stage == "SELECTED" else None, "rate_currency": "USD", "offer_status": "OFFER_ACCEPTED" if stage == "SELECTED" else "RATE_NEGOTIATION",
                               "offer_date": today - timedelta(days=4), "accepted_date": today - timedelta(days=2) if stage == "SELECTED" else None,
                               "declined_date": None, "notes": "Commercial details restricted.", "created_at": now - timedelta(days=4), "updated_at": now})

        boards, steps = [], []
        for board_index, candidate_index in enumerate([0, 1, 5, 12, 21]):
            candidate = candidate_rows[candidate_index]
            board_id = f"onboarding-{board_index + 1:03d}"
            expected = today + timedelta(days=[-5, 12, 18, 24, 28][board_index])
            boards.append({"id": board_id, "candidate_id": candidate["id"], "expected_start_date": expected,
                           "actual_start_date": today - timedelta(days=5) if board_index == 0 else None,
                           "overall_status": "COMPLETE" if board_index == 0 else "BLOCKED" if board_index in {2, 4} else "IN_PROGRESS",
                           "created_at": now - timedelta(days=12 + board_index), "updated_at": now})
            completed_count, blocked_index = [11, 8, 6, 7, 4][board_index], [None, None, 6, None, 4][board_index]
            for step_index, (step_type, label, party) in enumerate(WORKFLOW):
                complete, blocked = step_index < completed_count, step_index == blocked_index
                status_value = "COMPLETE" if complete else "BLOCKED" if blocked else "IN_PROGRESS" if step_index == completed_count else "NOT_STARTED"
                blocker = "Supplemental background check requested" if blocked and step_type == "FINGERPRINT_APPOINTMENT" else "Manager approval is pending" if blocked else None
                steps.append({"id": f"step-{board_index + 1:03d}-{step_index + 1:02d}", "onboarding_record_id": board_id, "step_type": step_type,
                              "step_label": label, "step_order": step_index + 1, "responsible_party": party,
                              "owner_id": candidate["capco_reviewer_id"] if party == "CAPCO" else candidate["ms_reviewer_stakeholder_id"], "status": status_value,
                              "started_at": now - timedelta(days=max(1, completed_count - step_index + 2)) if status_value != "NOT_STARTED" else None,
                              "completed_at": now - timedelta(days=max(1, completed_count - step_index)) if complete else None,
                              "target_completion_date": expected - timedelta(days=max(0, len(WORKFLOW) - step_index - 2)),
                              "blocked_since": now - timedelta(days=4 + board_index) if blocked else None, "blocker_reason": blocker,
                              "notes": "Requested documents supplied; awaiting review." if blocked else "", "updated_at": now})

        batches = ((resource_requirements, requirements), (candidates, candidate_rows), (candidate_stage_history, histories),
                   (candidate_interviews, interviews), (candidate_offers, offers), (onboarding_records, boards),
                   (onboarding_steps, steps), (resourcing_events, events))
        with self.engine.begin() as connection:
            for table, rows in batches:
                if rows: connection.execute(insert(table), rows)
            connection.execute(insert(resourcing_seed_registry).values(id=self.seed_id, seeded_at=now, row_count=sum(len(rows) for _, rows in batches)))

    def _validate_external_ids(self, connection, values):
        checks = (
            (engagements, values.get("engagement_id"), "Engagement"),
            (employees, values.get("request_owner_capco_employee_id") or values.get("capco_reviewer_id"), "Capco owner"),
            (stakeholders, values.get("client_stakeholder_id") or values.get("ms_reviewer_stakeholder_id"), "Client stakeholder"),
        )
        for table, value, label in checks:
            if value and connection.execute(select(table.c.id).where(table.c.id == value)).scalar_one_or_none() is None:
                raise NotFoundError(f"{label} not found")

    @staticmethod
    def _assert_fresh(current, changes):
        expected = changes.pop("expected_updated_at", None)
        if expected is None:
            return
        actual = current["updated_at"]
        if expected.tzinfo is not None:
            expected = expected.astimezone(timezone.utc).replace(tzinfo=None)
        if actual.tzinfo is not None:
            actual = actual.astimezone(timezone.utc).replace(tzinfo=None)
        if abs((expected - actual).total_seconds()) > 0.001:
            raise ConflictError("This record changed after it was opened. Refresh it before saving.")

    def options(self, pod=None):
        with self.engine.connect() as connection:
            project_rows = [dict(row) for row in connection.execute(select(engagements).order_by(engagements.c.name)).mappings()]
            employee_rows = [dict(row) for row in connection.execute(
                select(employees.c.id, employees.c.name, employees.c.role, employees.c.level, employees.c.location)
                .where(employees.c.active.is_(True)).order_by(employees.c.name)
            ).mappings()]
        if pod and pod != "All":
            project_rows = [row for row in project_rows if row["pod_id"] == pod]
        stakeholder_rows = self.repository.list_stakeholders(pod=pod if pod and pod != "All" else None)
        requirements = self.list_requirements(pod)
        values = lambda key, rows=requirements: sorted({value for row in rows for value in ([row[key]] if isinstance(row.get(key), str) else row.get(key, [])) if value})
        return {
            "pods": sorted({row["pod_id"] for row in project_rows}),
            "engagements": [{key: row[key] for key in ("id", "name", "pod_id", "division_id", "business_unit_id", "division", "business_unit")} for row in project_rows],
            "employees": employee_rows,
            "stakeholders": [{"id": row.id, "name": row.name, "pod": row.pod, "division": row.division, "business_unit": row.business_unit} for row in stakeholder_rows],
            "roles": values("role"), "levels": values("level"), "locations": values("location"),
            "skills": sorted(set(values("required_skills") + values("preferred_skills"))),
            "priorities": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            "requirement_statuses": ["OPEN", "SOURCING", "PARTIALLY_FILLED", "FILLED", "CANCELLED"],
            "candidate_stages": ["IDENTIFIED", "CAPCO_REVIEW", "SUBMITTED_TO_MS", "MS_REVIEW", "INTERVIEW_SCHEDULED", "INTERVIEWING", "OFFER", "SELECTED", "REJECTED", "WITHDRAWN"],
        }

    def list_requirements(self, pod=None):
        statement = (
            select(resource_requirements, engagements.c.name.label("project_name"), engagements.c.division, engagements.c.business_unit,
                   employees.c.name.label("owner_name"), stakeholders.c.name.label("client_name"))
            .join(engagements, engagements.c.id == resource_requirements.c.engagement_id)
            .join(employees, employees.c.id == resource_requirements.c.request_owner_capco_employee_id)
            .join(stakeholders, stakeholders.c.id == resource_requirements.c.client_stakeholder_id)
        )
        if pod and pod != "All":
            statement = statement.where(resource_requirements.c.pod_id == pod)
        with self.engine.connect() as connection:
            rows = [dict(row) for row in connection.execute(statement.order_by(resource_requirements.c.created_at)).mappings()]
            counts = {key: value for key, value in connection.execute(
                select(candidates.c.resource_requirement_id, func.count()).where(candidates.c.stage.notin_(["REJECTED", "WITHDRAWN"]))
                .group_by(candidates.c.resource_requirement_id)
            ).tuples()}
            fills = {key: value for key, value in connection.execute(
                select(candidates.c.resource_requirement_id, func.count()).where(candidates.c.stage == "SELECTED")
                .group_by(candidates.c.resource_requirement_id)
            ).tuples()}
        for row in rows:
            row["candidate_count"] = counts.get(row["id"], 0)
            row["filled_headcount"] = min(row["requested_headcount"], fills.get(row["id"], 0))
            row["remaining_headcount"] = max(0, row["requested_headcount"] - row["filled_headcount"])
            row["age_days"] = elapsed_days(row["created_at"])
            row["current_pipeline_stage"] = "No candidates" if not row["candidate_count"] else "Active pipeline"
        return rows

    def get_requirement(self, requirement_id):
        result = next((row for row in self.list_requirements() if row["id"] == requirement_id), None)
        if not result:
            raise NotFoundError("Resource requirement not found")
        result["candidates"] = self.list_candidates(requirement_id=requirement_id)
        return result

    def create_requirement(self, payload):
        values, now = payload.copy(), utcnow()
        values.update(id=f"req-{uuid4().hex[:12]}", created_at=now, updated_at=now)
        with self.engine.begin() as connection:
            self._validate_external_ids(connection, values)
            project = connection.execute(select(engagements).where(engagements.c.id == values["engagement_id"])).mappings().one()
            if any(values[key] != project[key] for key in ("pod_id", "division_id", "business_unit_id")):
                raise ConflictError("Pod, division and business unit must match the canonical engagement")
            connection.execute(insert(resource_requirements).values(**values))
        return self.get_requirement(values["id"])

    def update_requirement(self, requirement_id, changes):
        with self.engine.begin() as connection:
            current = connection.execute(select(resource_requirements).where(resource_requirements.c.id == requirement_id)).mappings().one_or_none()
            if not current:
                raise NotFoundError("Resource requirement not found")
            self._assert_fresh(current, changes)
            self._validate_external_ids(connection, changes)
            changes["updated_at"] = utcnow()
            if changes.get("status") in {"FILLED", "CANCELLED"}:
                changes["closed_at"] = utcnow()
            connection.execute(update(resource_requirements).where(resource_requirements.c.id == requirement_id).values(**changes))
        return self.get_requirement(requirement_id)

    def list_candidates(self, pod=None, requirement_id=None):
        statement = (
            select(candidates, resource_requirements.c.title.label("requirement_title"), resource_requirements.c.role,
                   resource_requirements.c.pod_id, engagements.c.division, engagements.c.business_unit, engagements.c.name.label("project_name"),
                   employees.c.name.label("owner_name"), stakeholders.c.name.label("ms_owner_name"))
            .join(resource_requirements, resource_requirements.c.id == candidates.c.resource_requirement_id)
            .join(engagements, engagements.c.id == resource_requirements.c.engagement_id)
            .join(employees, employees.c.id == candidates.c.capco_reviewer_id)
            .outerjoin(stakeholders, stakeholders.c.id == candidates.c.ms_reviewer_stakeholder_id)
        )
        if pod and pod != "All": statement = statement.where(resource_requirements.c.pod_id == pod)
        if requirement_id: statement = statement.where(candidates.c.resource_requirement_id == requirement_id)
        with self.engine.connect() as connection:
            rows = [dict(row) for row in connection.execute(statement.order_by(candidates.c.updated_at.desc())).mappings()]
            current_history = {key: value for key, value in connection.execute(
                select(candidate_stage_history.c.candidate_id, func.max(candidate_stage_history.c.entered_at))
                .where(candidate_stage_history.c.exited_at.is_(None)).group_by(candidate_stage_history.c.candidate_id)
            ).tuples()}
        for row in rows:
            row["name"] = f"{row['first_name']} {row['last_name']}"
            row["stage_age_days"] = elapsed_days(current_history.get(row["id"], row["updated_at"]))
            row["overdue"] = row["stage"] == "MS_REVIEW" and row["stage_age_days"] > 3
        return rows

    def get_candidate(self, candidate_id):
        result = next((row for row in self.list_candidates() if row["id"] == candidate_id), None)
        if not result:
            raise NotFoundError("Candidate not found")
        with self.engine.connect() as connection:
            result["timeline"] = [dict(row) for row in connection.execute(
                select(candidate_stage_history).where(candidate_stage_history.c.candidate_id == candidate_id).order_by(candidate_stage_history.c.entered_at)
            ).mappings()]
            result["interviews"] = [dict(row) for row in connection.execute(
                select(candidate_interviews).where(candidate_interviews.c.candidate_id == candidate_id).order_by(candidate_interviews.c.scheduled_at)
            ).mappings()]
            offer = connection.execute(select(candidate_offers).where(candidate_offers.c.candidate_id == candidate_id)).mappings().one_or_none()
            onboarding = connection.execute(select(onboarding_records.c.id).where(onboarding_records.c.candidate_id == candidate_id)).scalar_one_or_none()
        if offer:
            result["offer"] = {key: value for key, value in dict(offer).items() if key not in {"proposed_rate", "agreed_rate"}}
        else:
            result["offer"] = None
        result["onboarding"] = self.get_onboarding(onboarding) if onboarding else None
        return result

    def create_candidate(self, payload):
        values, now = payload.copy(), utcnow()
        values.update(id=f"candidate-{uuid4().hex[:12]}", date_identified=date.today(), created_at=now, updated_at=now)
        with self.engine.begin() as connection:
            requirement = connection.execute(select(resource_requirements.c.id).where(resource_requirements.c.id == values["resource_requirement_id"])).scalar_one_or_none()
            if not requirement: raise NotFoundError("Resource requirement not found")
            self._validate_external_ids(connection, values)
            connection.execute(insert(candidates).values(**values))
            connection.execute(insert(candidate_stage_history).values(id=f"history-{uuid4().hex[:12]}", candidate_id=values["id"], stage=values["stage"], entered_at=now, note=""))
        return self.get_candidate(values["id"])

    def update_candidate(self, candidate_id, changes, actor=None):
        note = changes.pop("note", "") or ""
        with self.engine.begin() as connection:
            current = connection.execute(select(candidates).where(candidates.c.id == candidate_id)).mappings().one_or_none()
            if not current: raise NotFoundError("Candidate not found")
            self._assert_fresh(current, changes)
            self._validate_external_ids(connection, changes)
            now, new_stage = utcnow(), changes.get("stage")
            if new_stage and new_stage != current["stage"]:
                connection.execute(update(candidate_stage_history).where(and_(candidate_stage_history.c.candidate_id == candidate_id, candidate_stage_history.c.exited_at.is_(None))).values(exited_at=now))
                connection.execute(insert(candidate_stage_history).values(id=f"history-{uuid4().hex[:12]}", candidate_id=candidate_id, stage=new_stage, entered_at=now, changed_by_employee_id=actor, note=note))
                if new_stage == "SUBMITTED_TO_MS" and not current["date_submitted_to_ms"]:
                    changes["date_submitted_to_ms"] = date.today()
            changes["updated_at"] = now
            connection.execute(update(candidates).where(candidates.c.id == candidate_id).values(**changes))
            connection.execute(insert(resourcing_events).values(id=f"event-{uuid4().hex[:12]}", requirement_id=current["resource_requirement_id"], candidate_id=candidate_id, event_type="STAGE_CHANGED", headline=f"Stage changed to {new_stage or current['stage']}", detail=note, occurred_at=now, actor_employee_id=actor))
            if new_stage == "SELECTED":
                self._ensure_onboarding(connection, candidate_id, changes.get("expected_start_date") or current["expected_start_date"])
        return self.get_candidate(candidate_id)

    def _ensure_onboarding(self, connection, candidate_id, expected_start):
        existing = connection.execute(select(onboarding_records.c.id).where(onboarding_records.c.candidate_id == candidate_id)).scalar_one_or_none()
        if existing: return existing
        candidate = connection.execute(select(candidates).where(candidates.c.id == candidate_id)).mappings().one()
        board_id, now = f"onboarding-{uuid4().hex[:12]}", utcnow()
        connection.execute(insert(onboarding_records).values(id=board_id, candidate_id=candidate_id, expected_start_date=expected_start, overall_status="IN_PROGRESS", created_at=now, updated_at=now))
        connection.execute(insert(onboarding_steps), [{
            "id": f"step-{uuid4().hex[:12]}", "onboarding_record_id": board_id, "step_type": step_type, "step_label": label,
            "step_order": index + 1, "responsible_party": party,
            "owner_id": candidate["capco_reviewer_id"] if party == "CAPCO" else candidate["ms_reviewer_stakeholder_id"],
            "status": "IN_PROGRESS" if index == 0 else "NOT_STARTED", "started_at": now if index == 0 else None,
            "updated_at": now, "notes": "",
        } for index, (step_type, label, party) in enumerate(WORKFLOW)])
        return board_id

    def add_interview(self, candidate_id, payload):
        values, now = payload.copy(), utcnow()
        values.update(id=f"interview-{uuid4().hex[:12]}", candidate_id=candidate_id, created_at=now, updated_at=now)
        with self.engine.begin() as connection:
            if connection.execute(select(candidates.c.id).where(candidates.c.id == candidate_id)).scalar_one_or_none() is None:
                raise NotFoundError("Candidate not found")
            connection.execute(insert(candidate_interviews).values(**values))
        return values

    def update_interview(self, interview_id, changes):
        with self.engine.begin() as connection:
            current = connection.execute(select(candidate_interviews).where(candidate_interviews.c.id == interview_id)).mappings().one_or_none()
            if current is None:
                raise NotFoundError("Interview not found")
            self._assert_fresh(current, changes)
            changes["updated_at"] = utcnow()
            connection.execute(update(candidate_interviews).where(candidate_interviews.c.id == interview_id).values(**changes))
            return dict(connection.execute(select(candidate_interviews).where(candidate_interviews.c.id == interview_id)).mappings().one())

    def upsert_offer(self, candidate_id, payload):
        now = utcnow()
        with self.engine.begin() as connection:
            candidate = connection.execute(select(candidates).where(candidates.c.id == candidate_id)).mappings().one_or_none()
            if not candidate: raise NotFoundError("Candidate not found")
            current = connection.execute(select(candidate_offers).where(candidate_offers.c.candidate_id == candidate_id)).mappings().one_or_none()
            values = payload.copy()
            if current:
                self._assert_fresh(current, values)
            else:
                values.pop("expected_updated_at", None)
            status_value = values.get("offer_status", current["offer_status"] if current else "OFFER_PENDING")
            if status_value == "OFFER_ACCEPTED": values["accepted_date"] = date.today()
            if status_value == "OFFER_DECLINED": values["declined_date"] = date.today()
            values["updated_at"] = now
            if current:
                connection.execute(update(candidate_offers).where(candidate_offers.c.candidate_id == candidate_id).values(**values))
                offer_id = current["id"]
            else:
                offer_id = f"offer-{uuid4().hex[:12]}"
                values.update(id=offer_id, candidate_id=candidate_id, offer_date=date.today(), created_at=now)
                connection.execute(insert(candidate_offers).values(**values))
            if status_value == "OFFER_ACCEPTED":
                connection.execute(update(candidate_stage_history).where(and_(candidate_stage_history.c.candidate_id == candidate_id, candidate_stage_history.c.exited_at.is_(None))).values(exited_at=now))
                connection.execute(insert(candidate_stage_history).values(id=f"history-{uuid4().hex[:12]}", candidate_id=candidate_id, stage="SELECTED", entered_at=now, note="Offer accepted"))
                connection.execute(update(candidates).where(candidates.c.id == candidate_id).values(stage="SELECTED", updated_at=now))
                self._ensure_onboarding(connection, candidate_id, candidate["expected_start_date"])
            return dict(connection.execute(select(candidate_offers).where(candidate_offers.c.id == offer_id)).mappings().one())

    def get_offer(self, candidate_id):
        with self.engine.connect() as connection:
            row = connection.execute(select(candidate_offers).where(candidate_offers.c.candidate_id == candidate_id)).mappings().one_or_none()
        if row is None:
            raise NotFoundError("Offer not found")
        return dict(row)

    def list_onboarding(self, pod=None):
        statement = (
            select(onboarding_records, candidates.c.first_name, candidates.c.last_name, candidates.c.level,
                   resource_requirements.c.role, resource_requirements.c.pod_id, engagements.c.division,
                   engagements.c.business_unit, engagements.c.name.label("project_name"),
                   employees.c.name.label("capco_owner_name"))
            .join(candidates, candidates.c.id == onboarding_records.c.candidate_id)
            .join(resource_requirements, resource_requirements.c.id == candidates.c.resource_requirement_id)
            .join(engagements, engagements.c.id == resource_requirements.c.engagement_id)
            .join(employees, employees.c.id == candidates.c.capco_reviewer_id)
        )
        if pod and pod != "All": statement = statement.where(resource_requirements.c.pod_id == pod)
        with self.engine.connect() as connection:
            rows = [dict(row) for row in connection.execute(statement.order_by(onboarding_records.c.expected_start_date)).mappings()]
            step_rows = [dict(row) for row in connection.execute(select(onboarding_steps).order_by(onboarding_steps.c.step_order)).mappings()]
            employee_names = {key: value for key, value in connection.execute(select(employees.c.id, employees.c.name)).tuples()}
            stakeholder_names = {key: value for key, value in connection.execute(select(stakeholders.c.id, stakeholders.c.name)).tuples()}
        grouped = defaultdict(list)
        for step in step_rows:
            step["owner_name"] = employee_names.get(step["owner_id"]) or stakeholder_names.get(step["owner_id"])
            step["days_blocked"] = elapsed_days(step["blocked_since"]) if step["blocked_since"] else 0
            grouped[step["onboarding_record_id"]].append(step)
        historical_step_days = defaultdict(list)
        for step in step_rows:
            if step["status"] == "COMPLETE" and step["started_at"] and step["completed_at"]:
                historical_step_days[step["step_order"]].append(max(0.5, (step["completed_at"] - step["started_at"]).total_seconds() / 86400))
        historical_averages = {order: mean(values) for order, values in historical_step_days.items()}
        for row in rows:
            row["name"] = f"{row['first_name']} {row['last_name']}"
            row["steps"] = grouped[row["id"]]
            row["completed_steps"] = sum(step["status"] == "COMPLETE" for step in row["steps"])
            row["total_steps"] = len(row["steps"])
            row["blocked_steps"] = sum(step["status"] == "BLOCKED" for step in row["steps"])
            row["next_step"] = next((step for step in row["steps"] if step["status"] not in {"COMPLETE", "NOT_APPLICABLE"}), None)
            row["responsible_party"] = row["next_step"]["responsible_party"] if row["next_step"] else None
            row["owner_name"] = row["next_step"]["owner_name"] if row["next_step"] else row["capco_owner_name"]
            row["blocker"] = next((step["blocker_reason"] for step in row["steps"] if step["status"] == "BLOCKED"), None)
            required_before_start = [step for step in row["steps"] if step["step_type"] != "STARTED"]
            row["ready_to_start"] = bool(required_before_start) and all(step["status"] in {"COMPLETE", "NOT_APPLICABLE"} for step in required_before_start) and not row["actual_start_date"]
            remaining_average = sum(historical_averages.get(step["step_order"], 1.0) for step in row["steps"] if step["status"] not in {"COMPLETE", "NOT_APPLICABLE"})
            days_until = (row["expected_start_date"] - date.today()).days if row["expected_start_date"] else None
            row["risk"] = "START_AT_RISK" if row["blocked_steps"] or (days_until is not None and remaining_average > days_until) else "ON_TRACK"
            row["risk_explanation"] = {"remaining_steps": row["total_steps"] - row["completed_steps"], "historical_average_remaining_days": round(remaining_average, 1), "days_until_expected_start": days_until, "duration_basis": "historical completed onboarding steps"}
        return rows

    def get_onboarding(self, onboarding_id):
        result = next((row for row in self.list_onboarding() if row["id"] == onboarding_id), None)
        if not result: raise NotFoundError("Onboarding record not found")
        with self.engine.connect() as connection:
            result["blocker_history"] = [dict(row) for row in connection.execute(
                select(resourcing_events).where(and_(
                    resourcing_events.c.onboarding_record_id == onboarding_id,
                    resourcing_events.c.event_type.in_(["BLOCKER_CREATED", "BLOCKER_RESOLVED"]),
                )).order_by(resourcing_events.c.occurred_at.desc())
            ).mappings()]
        return result

    def update_onboarding(self, onboarding_id, changes):
        with self.engine.begin() as connection:
            current = connection.execute(select(onboarding_records).where(onboarding_records.c.id == onboarding_id)).mappings().one_or_none()
            if current is None:
                raise NotFoundError("Onboarding record not found")
            self._assert_fresh(current, changes)
            changes["updated_at"] = utcnow()
            connection.execute(update(onboarding_records).where(onboarding_records.c.id == onboarding_id).values(**changes))
        return self.get_onboarding(onboarding_id)

    def update_step(self, onboarding_id, step_id, changes):
        now = utcnow()
        with self.engine.begin() as connection:
            current = connection.execute(select(onboarding_steps).where(and_(onboarding_steps.c.id == step_id, onboarding_steps.c.onboarding_record_id == onboarding_id))).mappings().one_or_none()
            if not current: raise NotFoundError("Onboarding step not found")
            self._assert_fresh(current, changes)
            responsible_party = changes.get("responsible_party", current["responsible_party"])
            if responsible_party not in {"CAPCO", "MORGAN_STANLEY"}:
                raise ValueError("Responsible party must be CAPCO or MORGAN_STANLEY")
            if changes.get("owner_id"):
                owner_table = employees if responsible_party == "CAPCO" else stakeholders
                if connection.execute(select(owner_table.c.id).where(owner_table.c.id == changes["owner_id"])).scalar_one_or_none() is None:
                    raise NotFoundError("Step owner does not belong to the responsible organization")
            status_value = changes.get("status")
            if status_value == "COMPLETE": changes.update(completed_at=now, blocked_since=None, blocker_reason=None)
            elif status_value == "BLOCKED" and not current["blocked_since"]: changes["blocked_since"] = now
            elif status_value in {"IN_PROGRESS", "NOT_STARTED", "NOT_APPLICABLE"}:
                if status_value == "IN_PROGRESS" and not current["started_at"]:
                    changes["started_at"] = now
                if current["status"] == "BLOCKED":
                    changes.update(blocked_since=None, blocker_reason=None)
            changes["updated_at"] = now
            connection.execute(update(onboarding_steps).where(onboarding_steps.c.id == step_id).values(**changes))
            if status_value == "BLOCKED" and current["status"] != "BLOCKED":
                connection.execute(insert(resourcing_events).values(
                    id=f"event-{uuid4().hex[:12]}", onboarding_record_id=onboarding_id,
                    event_type="BLOCKER_CREATED", headline=f"Blocked: {current['step_label']}",
                    detail=changes.get("blocker_reason") or "Operational blocker", occurred_at=now,
                ))
            elif current["status"] == "BLOCKED" and status_value and status_value != "BLOCKED":
                connection.execute(insert(resourcing_events).values(
                    id=f"event-{uuid4().hex[:12]}", onboarding_record_id=onboarding_id,
                    event_type="BLOCKER_RESOLVED", headline=f"Resolved: {current['step_label']}",
                    detail=current["blocker_reason"] or "Blocker resolved", occurred_at=now,
                ))
            statuses = list(connection.execute(select(onboarding_steps.c.status).where(onboarding_steps.c.onboarding_record_id == onboarding_id)).scalars())
            overall = "BLOCKED" if "BLOCKED" in statuses else "COMPLETE" if all(value in {"COMPLETE", "NOT_APPLICABLE"} for value in statuses) else "IN_PROGRESS"
            connection.execute(update(onboarding_records).where(onboarding_records.c.id == onboarding_id).values(overall_status=overall, updated_at=now))
        return self.get_onboarding(onboarding_id)

    def stakeholder_context(self, stakeholder_id):
        candidates_for_person = [row for row in self.list_candidates() if row["ms_reviewer_stakeholder_id"] == stakeholder_id]
        candidate_ids = {row["id"] for row in candidates_for_person}
        onboarding = [row for row in self.list_onboarding() if row["candidate_id"] in candidate_ids]
        return {"candidates": candidates_for_person, "onboarding": onboarding}

    def executive_demand_records(self, pod=None, horizon=None):
        mappings = {
            "AI / GenAI": ("genai", "ai ", "artificial intelligence"),
            "Data Engineering": ("data engineer", "data governance", "collibra", "lineage"),
            "Business Analysis": ("business analyst", "business analysis", "product analyst"),
            "Cloud": ("cloud", "aws", "azure", "kubernetes", "terraform"),
            "Program Management": ("program manager", "program management", "delivery lead"),
        }
        result = []
        for row in self.list_requirements(pod):
            if row["status"] not in ACTIVE_REQUIREMENTS or not row["remaining_headcount"]:
                continue
            if horizon and row["target_start_date"] > horizon:
                continue
            text = " ".join([row["role"], row["title"], *row["required_skills"]]).casefold()
            capability = next((name for name, needles in mappings.items() if any(needle in text for needle in needles)), "Program Management")
            result.append({"id": row["id"], "capability": capability, "required_fte": float(row["remaining_headcount"]),
                           "pod_id": row["pod_id"], "start_date": row["target_start_date"], "end_date": row["target_start_date"] + timedelta(days=180), "status": "Open"})
        return result

    def analytics(self, pod=None):
        candidates_in_scope = {row["id"] for row in self.list_candidates(pod)}
        boards = self.list_onboarding(pod)
        with self.engine.connect() as connection:
            histories = [dict(row) for row in connection.execute(select(candidate_stage_history)).mappings() if row.candidate_id in candidates_in_scope]
        durations, waiting = defaultdict(list), defaultdict(int)
        stage_labels = {"CAPCO_REVIEW": "Candidate Review", "MS_REVIEW": "MS Review", "INTERVIEWING": "Interview", "OFFER": "Offer"}
        for row in histories:
            label = stage_labels.get(row["stage"])
            if not label: continue
            if row["exited_at"]: durations[label].append(elapsed_days(row["entered_at"], row["exited_at"]))
            else: waiting[label] += 1
        durations["Onboarding"] = [elapsed_days(board["created_at"], board["actual_start_date"] or board["updated_at"]) for board in boards if board["overall_status"] == "COMPLETE"]
        targets = {"Candidate Review": 2, "MS Review": 3, "Interview": 4, "Offer": 3, "Onboarding": 14}
        return [{
            "stage": stage, "average_days": round(mean(durations.get(stage, [])), 1) if durations.get(stage) else None,
            "sample_size": len(durations.get(stage, [])),
            "target_days": target, "waiting": sum(board["overall_status"] != "COMPLETE" for board in boards) if stage == "Onboarding" else waiting[stage],
            "status": "OVER_TARGET" if durations.get(stage) and mean(durations[stage]) > target else "ON_TRACK",
        } for stage, target in targets.items()]

    def overview(self, pod=None):
        requirements, candidate_rows, boards = self.list_requirements(pod), self.list_candidates(pod), self.list_onboarding(pod)
        active_roles = [row for row in requirements if row["status"] in ACTIVE_REQUIREMENTS]
        active_candidates = [row for row in candidate_rows if row["stage"] in ACTIVE_CANDIDATES]
        offers = [row for row in candidate_rows if row["stage"] in {"OFFER", "SELECTED"}]
        active_boards = [row for row in boards if row["overall_status"] != "COMPLETE" and not row["actual_start_date"]]
        starting = [row for row in active_boards if row["expected_start_date"] and 0 <= (row["expected_start_date"] - date.today()).days < 30]
        analytics = self.analytics(pod)
        with self.engine.connect() as connection:
            selected_at = {candidate_id: entered_at for candidate_id, entered_at in connection.execute(
                select(candidate_stage_history.c.candidate_id, func.min(candidate_stage_history.c.entered_at))
                .where(candidate_stage_history.c.stage == "SELECTED").group_by(candidate_stage_history.c.candidate_id)
            ).tuples()}
        time_to_fill = []
        for candidate in [row for row in candidate_rows if row["stage"] == "SELECTED"]:
            requirement = next(row for row in requirements if row["id"] == candidate["resource_requirement_id"])
            if selected_at.get(candidate["id"]):
                time_to_fill.append(elapsed_days(requirement["created_at"], selected_at[candidate["id"]]))
        critical = ([{
            "type": "ROLE", "id": row["id"], "headline": row["title"],
            "detail": "No viable candidates" if not row["candidate_count"] else f"Open {row['age_days']} days", "age_days": row["age_days"],
        } for row in active_roles if row["age_days"] > 30 or not row["candidate_count"]] + [{
            "type": "ONBOARDING", "id": row["id"], "headline": row["name"], "detail": row["blocker"],
            "age_days": max((step["days_blocked"] for step in row["steps"]), default=0),
        } for row in active_boards if row["blocked_steps"]])[:6]
        role_summary = defaultdict(int)
        for row in active_roles: role_summary[row["role"]] += row["remaining_headcount"]
        funnel = [
            ("Demand", sum(row["remaining_headcount"] for row in active_roles)),
            ("Sourcing", sum(row["stage"] in {"IDENTIFIED", "CAPCO_REVIEW"} for row in active_candidates)),
            ("MS Review", sum(row["stage"] in {"SUBMITTED_TO_MS", "MS_REVIEW"} for row in active_candidates)),
            ("Interview", sum(row["stage"] in {"INTERVIEW_SCHEDULED", "INTERVIEWING"} for row in active_candidates)),
            ("Offer", len(offers)), ("Onboarding", len(active_boards)), ("Started", sum(bool(row["actual_start_date"]) for row in boards)),
        ]
        onboarding_average = next((row["average_days"] for row in analytics if row["stage"] == "Onboarding"), None)
        return {
            "generated_at": utcnow(), "pod": pod or "All",
            "metrics": {
                "open_demand": sum(row["remaining_headcount"] for row in active_roles), "critical_roles": sum(row["priority"] == "CRITICAL" for row in active_roles),
                "candidates": len(active_candidates), "with_ms": sum(row["stage"] in {"SUBMITTED_TO_MS", "MS_REVIEW"} for row in active_candidates),
                "offers": len(offers), "pending_offers": sum(row["stage"] == "OFFER" for row in offers), "onboarding": len(active_boards),
                "blocked": sum(row["blocked_steps"] > 0 for row in active_boards), "starting_30_days": len(starting),
                "starting_at_risk": sum(row["risk"] == "START_AT_RISK" for row in starting), "roles_over_30_days": sum(row["age_days"] > 30 for row in active_roles),
                "waiting_on_ms": sum(row["responsible_party"] == "MORGAN_STANLEY" for row in active_boards),
                "waiting_on_capco": sum(row["responsible_party"] == "CAPCO" for row in active_boards),
                "progressing": sum(row["responsible_party"] is None for row in active_boards),
                "avg_time_to_fill": round(mean(time_to_fill), 1) if time_to_fill else None, "avg_onboarding_days": onboarding_average,
            },
            "funnel": [{"stage": stage, "count": count} for stage, count in funnel], "critical_items": critical,
            "starting_soon": starting, "open_demand": [{"role": role, "count": count} for role, count in sorted(role_summary.items(), key=lambda item: -item[1])],
            "analytics": analytics,
        }

    def start_candidate(self, onboarding_id):
        now, today = utcnow(), date.today()
        with self.engine.begin() as connection:
            board = connection.execute(select(onboarding_records).where(onboarding_records.c.id == onboarding_id)).mappings().one_or_none()
            if not board: raise NotFoundError("Onboarding record not found")
            if board["actual_start_date"]:
                raise ConflictError("This candidate has already started")
            candidate = connection.execute(select(candidates).where(candidates.c.id == board["candidate_id"])).mappings().one()
            requirement = connection.execute(select(resource_requirements).where(resource_requirements.c.id == candidate["resource_requirement_id"])).mappings().one()
            incomplete = connection.execute(select(func.count()).select_from(onboarding_steps).where(and_(onboarding_steps.c.onboarding_record_id == onboarding_id, onboarding_steps.c.step_type != "STARTED", onboarding_steps.c.status.notin_(["COMPLETE", "NOT_APPLICABLE"])))).scalar_one()
            if incomplete:
                raise ConflictError("All required onboarding steps must be complete before the candidate can start")
            employee_id = candidate["capco_employee_id"]
            if not employee_id:
                employee_id = f"capco-{uuid4().hex[:12]}"
                connection.execute(insert(employees).values(id=employee_id, name=f"{candidate['first_name']} {candidate['last_name']}", first_name=candidate["first_name"], last_name=candidate["last_name"], title=candidate["level"], level=candidate["level"], role=requirement["role"], capability=requirement["role"], location=candidate["location"], active=True, source_system="resourcing", source_record_id=candidate["id"], created_at=now, updated_at=now))
                connection.execute(update(candidates).where(candidates.c.id == candidate["id"]).values(capco_employee_id=employee_id, stage="SELECTED", updated_at=now))
            existing_allocation = connection.execute(select(func.coalesce(func.sum(engagement_assignments.c.allocation_percent), 0)).where(
                engagement_assignments.c.employee_id == employee_id,
                engagement_assignments.c.status.in_(["Active", "Planned"]),
                engagement_assignments.c.start_date <= today + timedelta(days=180),
                engagement_assignments.c.end_date >= today,
            )).scalar_one()
            if float(existing_allocation) + 100 > 100:
                raise ConflictError("Starting this candidate would allocate the employee above 100%; adjust existing assignments first")
            assignment_id = f"assignment-{uuid4().hex[:12]}"
            connection.execute(insert(engagement_assignments).values(id=assignment_id, employee_id=employee_id, engagement_id=requirement["engagement_id"], allocation_percent=100, assignment_role=requirement["role"], billable=True, status="Active", start_date=today, end_date=today + timedelta(days=180)))
            connection.execute(update(onboarding_records).where(onboarding_records.c.id == onboarding_id).values(actual_start_date=today, overall_status="COMPLETE", updated_at=now))
            connection.execute(update(onboarding_steps).where(onboarding_steps.c.onboarding_record_id == onboarding_id).values(status="COMPLETE", completed_at=now, updated_at=now))
            connection.execute(insert(resourcing_events).values(
                id=f"event-{uuid4().hex[:12]}", requirement_id=requirement["id"], candidate_id=candidate["id"],
                onboarding_record_id=onboarding_id, event_type="CANDIDATE_STARTED",
                headline=f"{candidate['first_name']} {candidate['last_name']} started", detail=requirement["title"], occurred_at=now,
            ))
        return {"onboarding": self.get_onboarding(onboarding_id), "employee_id": employee_id, "assignment_id": assignment_id}
