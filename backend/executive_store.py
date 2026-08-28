from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from math import ceil

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, Index, Integer, MetaData, String,
    Table, Text, and_, func, insert, inspect, or_, select, update,
)
from sqlalchemy.engine import Engine

from .pod_store import (
    pod_change_events, pod_critical_items, pod_event_attendees, pod_events,
    pod_milestones, pod_tasks,
)
from .repository import POD_STRUCTURE
from .models import OpportunityCreate
from .account_team import ACCOUNT_TEAM


executive_metadata = MetaData()

engagements = Table(
    "executive_engagements", executive_metadata,
    Column("id", String(120), primary_key=True),
    Column("pod_id", String(80), nullable=False),
    Column("division_id", String(160), nullable=False),
    Column("business_unit_id", String(220), nullable=False),
    Column("division", String(120), nullable=False),
    Column("business_unit", String(160), nullable=False),
    Column("name", String(240), nullable=False),
    Column("health", String(20), nullable=False),
    Column("status", String(30), nullable=False),
    Column("commercial_value", Float, nullable=False),
    Column("quarterly_revenue_target", Float, nullable=False),
    Column("start_date", Date, nullable=False),
    Column("end_date", Date, nullable=False),
    Column("renewal_date", Date),
    Column("executive_sponsor_id", String(180)),
    Column("opportunity_id", String(180)),
)
Index("idx_executive_engagement_period", engagements.c.pod_id, engagements.c.start_date, engagements.c.end_date)

engagement_stakeholders = Table(
    "engagement_stakeholders", executive_metadata,
    Column("engagement_id", String(120), primary_key=True),
    Column("stakeholder_id", String(180), primary_key=True),
    Column("relationship_role", String(80), nullable=False, default="Sponsor"),
    Column("is_primary", Boolean, nullable=False, default=False),
)
Index("idx_engagement_stakeholders_person", engagement_stakeholders.c.stakeholder_id, engagement_stakeholders.c.engagement_id)

employees = Table(
    "capco_employees", executive_metadata,
    Column("id", String(120), primary_key=True),
    Column("name", String(180), nullable=False),
    Column("first_name", String(90)),
    Column("last_name", String(90)),
    Column("title", String(160)),
    Column("level", String(80), nullable=False),
    Column("role", String(120), nullable=False),
    Column("capability", String(120)),
    Column("location", String(120), nullable=False),
    Column("active", Boolean, nullable=False, default=True),
    Column("manager_employee_id", String(120)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("source_system", String(80), nullable=False, default="manual"),
    Column("source_record_id", String(240)),
    Column("last_synced_at", DateTime(timezone=True)),
)
Index("uq_capco_employee_source_record", employees.c.source_system, employees.c.source_record_id, unique=True)
Index("idx_capco_employees_manager", employees.c.manager_employee_id)

employee_skills = Table(
    "employee_skills", executive_metadata,
    Column("id", String(150), primary_key=True),
    Column("employee_id", String(120), nullable=False),
    Column("capability", String(120), nullable=False),
)
Index("idx_employee_skills_capability", employee_skills.c.capability, employee_skills.c.employee_id)

employee_capacity = Table(
    "employee_capacity", executive_metadata,
    Column("id", String(160), primary_key=True),
    Column("employee_id", String(120), nullable=False),
    Column("period_start", Date, nullable=False),
    Column("period_end", Date, nullable=False),
    Column("available_hours", Float, nullable=False),
)
Index("idx_employee_capacity_period", employee_capacity.c.period_start, employee_capacity.c.period_end)

engagement_assignments = Table(
    "engagement_assignments", executive_metadata,
    Column("id", String(160), primary_key=True),
    Column("employee_id", String(120), nullable=False),
    Column("engagement_id", String(120), nullable=False),
    Column("allocation_percent", Float, nullable=False),
    Column("assignment_role", String(120)),
    Column("billable", Boolean, nullable=False),
    Column("status", String(30), nullable=False, default="Active"),
    Column("start_date", Date, nullable=False),
    Column("end_date", Date, nullable=False),
)
Index("idx_engagement_assignments_period", engagement_assignments.c.engagement_id, engagement_assignments.c.start_date, engagement_assignments.c.end_date)

revenue_records = Table(
    "revenue_records", executive_metadata,
    Column("id", String(160), primary_key=True),
    Column("engagement_id", String(120), nullable=False),
    Column("recognized_on", Date, nullable=False),
    Column("amount", Float, nullable=False),
)
Index("idx_revenue_records_period", revenue_records.c.recognized_on, revenue_records.c.engagement_id)

engagement_milestones = Table(
    "engagement_milestones", executive_metadata,
    Column("id", String(160), primary_key=True),
    Column("engagement_id", String(120), nullable=False),
    Column("title", String(240), nullable=False),
    Column("due_date", Date, nullable=False),
    Column("status", String(30), nullable=False),
    Column("completed_date", Date),
)
Index("idx_engagement_milestones_period", engagement_milestones.c.engagement_id, engagement_milestones.c.due_date)

resource_demand = Table(
    "resource_demand", executive_metadata,
    Column("id", String(160), primary_key=True),
    Column("pod_id", String(80), nullable=False),
    Column("engagement_id", String(120)),
    Column("opportunity_id", String(180)),
    Column("capability", String(120), nullable=False),
    Column("required_fte", Float, nullable=False),
    Column("start_date", Date, nullable=False),
    Column("end_date", Date, nullable=False),
    Column("status", String(30), nullable=False),
)
Index("idx_resource_demand_period", resource_demand.c.pod_id, resource_demand.c.start_date, resource_demand.c.end_date)

executive_changes = Table(
    "account_metric_history", executive_metadata,
    Column("id", String(160), primary_key=True),
    Column("event_date", Date, nullable=False),
    Column("pod_id", String(80), nullable=False),
    Column("kind", String(40), nullable=False),
    Column("headline", String(300), nullable=False),
    Column("detail", Text, nullable=False),
    Column("engagement_id", String(120)),
    Column("employee_id", String(120)),
    Column("metric_name", String(100)),
    Column("previous_value", Float),
    Column("new_value", Float),
)
Index("idx_account_metric_history_period", executive_changes.c.event_date, executive_changes.c.pod_id)

executive_seed_registry = Table(
    "executive_seed_registry", executive_metadata,
    Column("id", String(80), primary_key=True),
    Column("seeded_at", DateTime(timezone=True), nullable=False),
    Column("row_count", Integer, nullable=False),
)


PROJECTS = [
    ("eng-isg-equities", "ISG", "Front Office", "Equities", "Equities Transformation", "GREEN", 3_200_000, 2_250_000),
    ("eng-isg-fixed-income", "ISG", "Front Office", "Fixed Income", "Fixed Income Controls Modernization", "AMBER", 2_400_000, 1_650_000),
    ("eng-isg-risk-data", "ISG", "Middle Office", "Risk Management", "Risk Data Platform", "RED", 3_400_000, 2_100_000),
    ("eng-isg-prime-cloud", "ISG", "Front Office", "Prime Services", "Prime Services Cloud", "GREEN", 1_800_000, 1_250_000),
    ("eng-wm-digital", "Wealth Management", "Front Office", "Private Wealth", "Digital Advisory Experience", "GREEN", 2_600_000, 1_750_000),
    ("eng-wm-onboarding", "Wealth Management", "Middle Office", "Advisory Operations", "Client Onboarding Transformation", "AMBER", 2_100_000, 1_450_000),
    ("eng-wm-data", "Wealth Management", "Middle Office", "Data & Insights", "Wealth Data Foundation", "GREEN", 1_700_000, 1_150_000),
    ("eng-msim-data", "MSIM", "Back Office", "Operations Technology", "MSIM Data Platform", "RED", 3_400_000, 1_900_000),
    ("eng-msim-risk", "MSIM", "Middle Office", "Investment Risk", "Investment Risk Analytics", "AMBER", 2_300_000, 1_450_000),
    ("eng-msim-alt", "MSIM", "Front Office", "Alternatives", "Alternatives Operating Model", "GREEN", 1_900_000, 1_250_000),
    ("eng-msim-ai", "MSIM", "Front Office", "Public Markets", "Public Markets AI Enablement", "GREEN", 2_700_000, 1_650_000),
]

CAPABILITIES = ["AI / GenAI", "Data Engineering", "Business Analysis", "Cloud", "Program Management"]
LEVELS = ["Consultant", "Senior Consultant", "Principal Consultant", "Managing Principal"]
LOCATIONS = ["New York", "Charlotte", "London", "Toronto"]


class ExecutiveAnalyticsStore:
    """Canonical SQL analytics layer for the account-level executive view."""

    seed_id = "executive-analytics-v1"

    def __init__(self, engine: Engine, repository, pod_store, *, seed_demo_data: bool = True, auto_create_schema: bool = True) -> None:
        self.engine = engine
        self.repository = repository
        self.pod_store = pod_store
        if auto_create_schema:
            executive_metadata.create_all(engine)
        elif not inspect(engine).has_table("executive_engagements"):
            raise RuntimeError("Executive analytics schema is missing; run Alembic migrations before startup")
        if seed_demo_data:
            self._seed_if_needed()
            self._reconcile_demo_identities()
            self._ensure_cross_pod_pipeline()

    @staticmethod
    def period_bounds(period: str, anchor: date | None = None, start_date: date | None = None, end_date: date | None = None) -> tuple[date, date]:
        anchor = anchor or date.today()
        if period == "custom":
            if not start_date or not end_date or end_date < start_date:
                raise ValueError("Custom periods require a valid start_date and end_date")
            return start_date, end_date
        if period == "month":
            start = anchor.replace(day=1)
            following = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            return start, following - timedelta(days=1)
        if period == "ytd":
            return date(anchor.year, 1, 1), anchor
        quarter_month = ((anchor.month - 1) // 3) * 3 + 1
        start = date(anchor.year, quarter_month, 1)
        following = date(anchor.year + (quarter_month == 10), 1 if quarter_month == 10 else quarter_month + 3, 1)
        return start, following - timedelta(days=1)

    def _seed_if_needed(self) -> None:
        with self.engine.connect() as connection:
            exists = connection.execute(select(executive_seed_registry.c.id).where(executive_seed_registry.c.id == self.seed_id)).scalar_one_or_none()
        if exists:
            return
        today = date.today()
        year = today.year
        q3_start, q3_end = date(year, 7, 1), date(year, 9, 30)
        q2_start, q2_end = date(year, 4, 1), date(year, 6, 30)
        repository_people = list(self.repository.list_stakeholders())
        opportunity_by_pod_unit = {}
        for opportunity in self.repository.list_opportunities():
            person = next((self.repository.stakeholders.get(value) for value in opportunity.stakeholder_ids if value in self.repository.stakeholders), None)
            if person:
                opportunity_by_pod_unit.setdefault((person.pod, person.business_unit), opportunity)

        project_rows = []
        for index, row in enumerate(PROJECTS):
            project_id, pod, division, unit, name, health, value, target = row
            unit_record = next(
                item for item in self.repository.units.values()
                if item["pod"] == pod and item["division"] == division and item["name"] == unit
            )
            division_record = next(
                item for item in self.repository.divisions.values()
                if item["pod"] == pod and item["name"] == division
            )
            sponsor = next((person for person in repository_people if person.pod == pod and person.business_unit == unit and person.is_buyer), None)
            sponsor = sponsor or next(person for person in repository_people if person.pod == pod and person.business_unit == unit)
            opportunity = opportunity_by_pod_unit.get((pod, unit))
            project_rows.append({
                "id": project_id, "pod_id": pod, "division_id": division_record["id"],
                "business_unit_id": unit_record["id"], "division": division, "business_unit": unit,
                "name": name, "health": health, "status": "Active", "commercial_value": value,
                "quarterly_revenue_target": target, "start_date": date(year - 1, 10, 1),
                "end_date": date(year + 1, 3, 31), "renewal_date": q3_end + timedelta(days=30 + index * 5),
                "executive_sponsor_id": sponsor.id, "opportunity_id": opportunity.id if opportunity else None,
            })

        engagement_stakeholder_rows = []
        for project in project_rows:
            related_ids = {project["executive_sponsor_id"]}
            opportunity = self.repository.opportunities.get(project["opportunity_id"])
            if opportunity:
                related_ids.update(opportunity.stakeholder_ids)
            for stakeholder_id in sorted(related_ids):
                engagement_stakeholder_rows.append({
                    "engagement_id": project["id"],
                    "stakeholder_id": stakeholder_id,
                    "relationship_role": "Executive sponsor" if stakeholder_id == project["executive_sponsor_id"] else "Opportunity stakeholder",
                    "is_primary": stakeholder_id == project["executive_sponsor_id"],
                })

        first_names = ["Avery", "Jordan", "Priya", "Marcus", "Elena", "Daniel", "Maya", "Noah", "Sofia", "Liam", "Chloe", "Ethan"]
        last_names = ["Patel", "Morgan", "Chen", "Williams", "Singh", "Brooks", "Kim"]
        employee_rows, skill_rows, capacity_rows, assignment_rows = [], [], [], []
        for index in range(84):
            employee_id = f"capco-{index + 1:03d}"
            if index < len(ACCOUNT_TEAM):
                _, employee_name, account_role = ACCOUNT_TEAM[index]
            else:
                employee_name = f"{first_names[index % len(first_names)]} {last_names[index // len(first_names)]}"
                account_role = CAPABILITIES[index % len(CAPABILITIES)]
            primary_skill = CAPABILITIES[index % len(CAPABILITIES)]
            employee_rows.append({
                "id": employee_id, "name": employee_name,
                "first_name": employee_name.split(" ", 1)[0],
                "last_name": employee_name.split(" ", 1)[1] if " " in employee_name else "",
                "title": account_role,
                "level": LEVELS[index % len(LEVELS)], "role": account_role,
                "capability": primary_skill,
                "location": LOCATIONS[index % len(LOCATIONS)], "active": True,
                "manager_employee_id": "capco-001" if index > 0 else None,
                "source_system": "demo_seed", "source_record_id": employee_id,
            })
            skill_rows.append({"id": f"skill-{index + 1:03d}-1", "employee_id": employee_id, "capability": primary_skill})
            if index % 3 == 0:
                skill_rows.append({"id": f"skill-{index + 1:03d}-2", "employee_id": employee_id, "capability": CAPABILITIES[(index + 2) % len(CAPABILITIES)]})
            for period_label, period_start, period_end in (("q2", q2_start, q2_end), ("q3", q3_start, q3_end)):
                capacity_rows.append({"id": f"capacity-{period_label}-{index + 1:03d}", "employee_id": employee_id, "period_start": period_start, "period_end": period_end, "available_hours": 520.0})
            project = project_rows[index % len(project_rows)]
            allocation = [70, 80, 85, 90, 95, 100][index % 6]
            if index in (11, 37, 62, 79):
                allocation = 110
            rolloff = q3_start + timedelta(days=75 + (index % 14)) if index in (5, 16, 27, 38, 49) else project["end_date"]
            assignment_rows.append({
                "id": f"assignment-{index + 1:03d}", "employee_id": employee_id,
                "engagement_id": project["id"], "allocation_percent": allocation,
                "assignment_role": account_role if index < len(ACCOUNT_TEAM) else primary_skill,
                "billable": index % 9 != 0, "status": "Active",
                "start_date": date(year, 1, 1), "end_date": rolloff,
            })

        revenue_rows = []
        for project_index, project in enumerate(project_rows):
            q3_total = project["quarterly_revenue_target"] * (0.88 + (project_index % 5) * 0.025)
            q2_total = q3_total / (1.04 + (project_index % 3) * 0.025)
            for month_index, month in enumerate((4, 5, 6)):
                revenue_rows.append({"id": f"rev-{project['id']}-q2-{month}", "engagement_id": project["id"], "recognized_on": date(year, month, 20), "amount": round(q2_total * [0.31, 0.33, 0.36][month_index], 2)})
            for month_index, month in enumerate((7, 8, 9)):
                revenue_rows.append({"id": f"rev-{project['id']}-q3-{month}", "engagement_id": project["id"], "recognized_on": date(year, month, 20), "amount": round(q3_total * [0.32, 0.34, 0.34][month_index], 2)})

        milestone_rows = []
        statuses = {
            "GREEN": ["Completed", "Completed", "On Track", "On Track"],
            "AMBER": ["Completed", "Delayed", "On Track", "At Risk"],
            "RED": ["Delayed", "Delayed", "At Risk", "At Risk"],
        }
        for project in project_rows:
            for index, status in enumerate(statuses[project["health"]]):
                due = q3_start + timedelta(days=18 + index * 21)
                completed = due - timedelta(days=2) if status == "Completed" else due + timedelta(days=8) if status == "Delayed" else None
                milestone_rows.append({"id": f"milestone-{project['id']}-{index + 1}", "engagement_id": project["id"], "title": ["Design sign-off", "Data readiness", "Release checkpoint", "Executive outcome review"][index], "due_date": due, "status": status, "completed_date": completed})

        demand_rows = []
        demand_values = {
            "AI / GenAI": [2.5, 2.0, 1.8], "Data Engineering": [2.0, 2.5, 2.0],
            "Business Analysis": [1.4, 1.5, 1.3], "Cloud": [2.3, 2.4, 1.7],
            "Program Management": [1.0, 1.1, 1.0],
        }
        pods = list(POD_STRUCTURE)
        for capability, values in demand_values.items():
            for pod_index, pod in enumerate(pods):
                project = next(row for row in project_rows if row["pod_id"] == pod and (capability.split()[0].casefold() in row["name"].casefold() or True))
                demand_rows.append({"id": f"demand-{capability.lower().replace(' ', '-').replace('/', '-')}-{pod_index}", "pod_id": pod, "engagement_id": project["id"], "opportunity_id": project["opportunity_id"], "capability": capability, "required_fte": values[pod_index], "start_date": today, "end_date": today + timedelta(days=60), "status": "Open"})

        change_rows = [
            {"id": "exec-change-1", "event_date": today - timedelta(days=3), "pod_id": "ISG", "kind": "PIPELINE", "headline": "$1.8M opportunity expanded in ISG Equities", "detail": "Scope validation increased the commercial opportunity attached to Equities.", "engagement_id": "eng-isg-equities", "metric_name": "pipeline", "previous_value": 1_400_000, "new_value": 1_800_000},
            {"id": "exec-change-2", "event_date": today - timedelta(days=6), "pod_id": "MSIM", "kind": "UTILIZATION", "headline": "MSIM utilization improved 4 points", "detail": "New billable allocations started on Public Markets AI Enablement.", "engagement_id": "eng-msim-ai", "metric_name": "utilization", "previous_value": 0.79, "new_value": 0.83},
            {"id": "exec-change-3", "event_date": today - timedelta(days=9), "pod_id": "Wealth Management", "kind": "DELIVERY", "headline": "Digital Advisory moved Amber to Green", "detail": "The release plan and client acceptance criteria were confirmed.", "engagement_id": "eng-wm-digital", "metric_name": "delivery_health", "previous_value": None, "new_value": None},
            {"id": "exec-change-4", "event_date": today - timedelta(days=12), "pod_id": "ISG", "kind": "RISK", "headline": "Risk Data Platform moved Green to Red", "detail": "Two milestones are delayed and an executive escalation remains open.", "engagement_id": "eng-isg-risk-data", "metric_name": "delivery_health", "previous_value": None, "new_value": None},
            {"id": "exec-change-5", "event_date": today - timedelta(days=15), "pod_id": "All", "kind": "WORKFORCE", "headline": "Five consultants entered the 30-day roll-off window", "detail": "Capacity is becoming available across Data Engineering and Business Analysis.", "engagement_id": None, "metric_name": "rolloff_count", "previous_value": 2, "new_value": 5},
        ]

        with self.engine.begin() as connection:
            for table, rows in ((engagements, project_rows), (engagement_stakeholders, engagement_stakeholder_rows), (employees, employee_rows), (employee_skills, skill_rows), (employee_capacity, capacity_rows), (engagement_assignments, assignment_rows), (revenue_records, revenue_rows), (engagement_milestones, milestone_rows), (resource_demand, demand_rows), (executive_changes, change_rows)):
                connection.execute(insert(table), rows)
            connection.execute(insert(executive_seed_registry).values(id=self.seed_id, seeded_at=datetime.now(timezone.utc), row_count=sum(map(len, (project_rows, engagement_stakeholder_rows, employee_rows, skill_rows, capacity_rows, assignment_rows, revenue_rows, milestone_rows, demand_rows, change_rows)))))

    def reconcile_operating_links(self) -> None:
        """Connect Pod risks created before or after portfolio seeding."""
        if not inspect(self.engine).has_table("pod_critical_items"):
            return
        with self.engine.begin() as connection:
            project_rows = connection.execute(select(engagements)).mappings().all()
            for pod in POD_STRUCTURE:
                pod_projects = [row for row in project_rows if row["pod_id"] == pod]
                if not pod_projects:
                    continue
                risk_rows = connection.execute(
                    select(pod_critical_items.c.id)
                    .where(pod_critical_items.c.pod_id == pod)
                    .order_by(pod_critical_items.c.id)
                ).scalars().all()
                for index, risk_id in enumerate(risk_rows):
                    connection.execute(
                        update(pod_critical_items)
                        .where(pod_critical_items.c.id == risk_id)
                        .values(engagement_id=pod_projects[index % len(pod_projects)]["id"])
                    )

    def _reconcile_demo_identities(self) -> None:
        """Upgrade earlier demo rows to the same stable IDs used by all domains."""
        with self.engine.begin() as connection:
            for employee_id, name, role in ACCOUNT_TEAM:
                connection.execute(
                    update(employees).where(employees.c.id == employee_id).values(
                        name=name,
                        first_name=name.split(" ", 1)[0],
                        last_name=name.split(" ", 1)[1] if " " in name else "",
                        title=role,
                        role=role,
                        source_system="demo_seed",
                        source_record_id=employee_id,
                    )
                )
            project_rows = connection.execute(select(engagements)).mappings().all()
            existing_links = {
                (row["engagement_id"], row["stakeholder_id"])
                for row in connection.execute(select(engagement_stakeholders)).mappings()
            }
            for project in project_rows:
                unit = next((
                    item for item in self.repository.units.values()
                    if item["pod"] == project["pod_id"]
                    and item["division"] == project["division"]
                    and item["name"] == project["business_unit"]
                ), None)
                division = next((
                    item for item in self.repository.divisions.values()
                    if item["pod"] == project["pod_id"] and item["name"] == project["division"]
                ), None)
                if unit and division:
                    connection.execute(
                        update(engagements).where(engagements.c.id == project["id"]).values(
                            division_id=division["id"], business_unit_id=unit["id"]
                        )
                    )
                related_ids = {project["executive_sponsor_id"]} if project["executive_sponsor_id"] else set()
                opportunity = self.repository.opportunities.get(project["opportunity_id"])
                if opportunity:
                    related_ids.update(opportunity.stakeholder_ids)
                for stakeholder_id in related_ids:
                    key = (project["id"], stakeholder_id)
                    if key in existing_links:
                        continue
                    connection.execute(insert(engagement_stakeholders).values(
                        engagement_id=project["id"],
                        stakeholder_id=stakeholder_id,
                        relationship_role="Executive sponsor" if stakeholder_id == project["executive_sponsor_id"] else "Opportunity stakeholder",
                        is_primary=stakeholder_id == project["executive_sponsor_id"],
                    ))
                    existing_links.add(key)

    def _ensure_cross_pod_pipeline(self) -> None:
        """Fill only missing pod coverage through the canonical opportunity repository."""
        existing_names = {item.name for item in self.repository.list_opportunities()}
        templates = [
            ("Operations Technology", "MSIM Data Platform expansion", 3_100_000, 55, "Proposal", ["Data", "Cloud"]),
            ("Investment Risk", "Investment risk analytics expansion", 2_400_000, 45, "Discovery", ["Risk", "Analytics"]),
            ("Alternatives", "Alternatives operating model extension", 1_600_000, 35, "Qualification", ["Operating Model"]),
            ("Public Markets", "Public Markets AI scale-up", 2_800_000, 60, "Negotiation", ["AI", "GenAI"]),
        ]
        created_by_unit = {}
        for unit, name, value, probability, stage, tags in templates:
            existing = next((item for item in self.repository.list_opportunities() if item.name == name), None)
            if existing:
                created_by_unit[unit] = existing
                continue
            sponsor = next((person for person in self.repository.list_stakeholders(pod="MSIM") if person.business_unit == unit and person.is_buyer), None)
            sponsor = sponsor or next((person for person in self.repository.list_stakeholders(pod="MSIM") if person.business_unit == unit), None)
            if not sponsor or name in existing_names:
                continue
            created_by_unit[unit] = self.repository.create_opportunity(OpportunityCreate(
                name=name,
                description=f"Account expansion opportunity connected to the active {unit} engagement.",
                estimated_value=value,
                probability=probability,
                stage=stage,
                stakeholder_ids=[sponsor.id],
                owner=sponsor.capco_owner or "Capco Account Team",
                tags=tags + ["MSIM"],
                target_close_date=date.today() + timedelta(days=75),
            ))
            existing_names.add(name)
        if created_by_unit:
            with self.engine.begin() as connection:
                for unit, opportunity in created_by_unit.items():
                    connection.execute(update(engagements).where(and_(engagements.c.pod_id == "MSIM", engagements.c.business_unit == unit)).values(opportunity_id=opportunity.id))

    @staticmethod
    def _status(value: float, strong: float, watch: float, inverse: bool = False) -> str:
        if inverse:
            return "Strong" if value <= strong else "Watch" if value <= watch else "Action"
        return "Strong" if value >= strong else "Watch" if value >= watch else "Action"

    @staticmethod
    def _prior_bounds(start: date, end: date) -> tuple[date, date]:
        days = (end - start).days + 1
        return start - timedelta(days=days), start - timedelta(days=1)

    def _opportunities(self, pod: str | None) -> list[dict]:
        records = []
        for opportunity in self.repository.list_opportunities():
            person = next((self.repository.stakeholders.get(value) for value in opportunity.stakeholder_ids if value in self.repository.stakeholders), None)
            if not person or (pod and pod != "All" and person.pod != pod):
                continue
            stage = {"Closed Won": "Won", "Closed Lost": "Lost"}.get(opportunity.stage, opportunity.stage)
            records.append({"id": opportunity.id, "name": opportunity.name, "pod": person.pod, "division": person.division, "businessUnit": person.business_unit, "stage": stage, "value": opportunity.estimated_value, "probability": opportunity.probability, "weightedValue": opportunity.estimated_value * opportunity.probability / 100, "stakeholderId": person.id, "stakeholder": person.name, "targetCloseDate": opportunity.target_close_date.isoformat() if opportunity.target_close_date else None})
        return records

    def overview(self, period: str = "quarter", anchor: date | None = None, start_date: date | None = None, end_date: date | None = None, pod: str | None = None) -> dict:
        if pod and pod != "All" and pod not in POD_STRUCTURE:
            raise ValueError("Unknown pod")
        start, end = self.period_bounds(period, anchor, start_date, end_date)
        prior_start, prior_end = self._prior_bounds(start, end)
        pod_filter = None if not pod or pod == "All" else pod
        with self.engine.connect() as connection:
            project_rows = [dict(row) for row in connection.execute(select(engagements).where(and_(engagements.c.start_date <= end, engagements.c.end_date >= start, *([engagements.c.pod_id == pod_filter] if pod_filter else [])))).mappings()]
            project_ids = [row["id"] for row in project_rows]
            revenue = [dict(row) for row in connection.execute(select(revenue_records).where(and_(revenue_records.c.engagement_id.in_(project_ids), revenue_records.c.recognized_on.between(start, end)))).mappings()] if project_ids else []
            prior_revenue = [dict(row) for row in connection.execute(select(revenue_records).where(and_(revenue_records.c.engagement_id.in_(project_ids), revenue_records.c.recognized_on.between(prior_start, prior_end)))).mappings()] if project_ids else []
            assignments = [dict(row) for row in connection.execute(select(engagement_assignments).where(and_(engagement_assignments.c.engagement_id.in_(project_ids), engagement_assignments.c.start_date <= end, engagement_assignments.c.end_date >= start))).mappings()] if project_ids else []
            employee_ids = sorted({row["employee_id"] for row in assignments})
            employee_rows = [dict(row) for row in connection.execute(select(employees).where(employees.c.id.in_(employee_ids))).mappings()] if employee_ids else []
            capacities = [dict(row) for row in connection.execute(select(employee_capacity).where(and_(employee_capacity.c.employee_id.in_(employee_ids), employee_capacity.c.period_start <= end, employee_capacity.c.period_end >= start))).mappings()] if employee_ids else []
            skills = [dict(row) for row in connection.execute(select(employee_skills).where(employee_skills.c.employee_id.in_(employee_ids))).mappings()] if employee_ids else []
            milestones = [dict(row) for row in connection.execute(select(engagement_milestones).where(and_(engagement_milestones.c.engagement_id.in_(project_ids), engagement_milestones.c.due_date.between(start, end)))).mappings()] if project_ids else []
            demands = [dict(row) for row in connection.execute(select(resource_demand).where(and_(resource_demand.c.status == "Open", resource_demand.c.start_date <= end + timedelta(days=60), resource_demand.c.end_date >= start, *([resource_demand.c.pod_id == pod_filter] if pod_filter else [])))).mappings()]
            risks = [dict(row) for row in connection.execute(select(pod_critical_items).where(and_(pod_critical_items.c.status != "Resolved", *([pod_critical_items.c.pod_id == pod_filter] if pod_filter else [])))).mappings()]
            changes = [dict(row) for row in connection.execute(select(executive_changes).where(and_(executive_changes.c.event_date.between(start, end), *([or_(executive_changes.c.pod_id == pod_filter, executive_changes.c.pod_id == "All")] if pod_filter else []))).order_by(executive_changes.c.event_date.desc())).mappings()]

        projects_by_id = {row["id"]: row for row in project_rows}
        employee_by_id = {row["id"]: row for row in employee_rows}
        capacity_by_employee = defaultdict(float)
        for row in capacities:
            capacity_by_employee[row["employee_id"]] += row["available_hours"]
        allocation_hours_by_employee = defaultdict(float)
        billable_hours_by_employee = defaultdict(float)
        assignments_by_project = defaultdict(list)
        for row in assignments:
            assignments_by_project[row["engagement_id"]].append(row)
            hours = capacity_by_employee[row["employee_id"]] * row["allocation_percent"] / 100
            allocation_hours_by_employee[row["employee_id"]] += hours
            if row["billable"]:
                billable_hours_by_employee[row["employee_id"]] += hours
        available_hours = sum(capacity_by_employee.values())
        billable_hours = sum(billable_hours_by_employee.values())
        allocated_hours = sum(allocation_hours_by_employee.values())
        utilization = billable_hours / available_hours if available_hours else None
        allocated_utilization = allocated_hours / available_hours if available_hours else None
        available_fte = sum(max(0, capacity_by_employee[value] - allocation_hours_by_employee[value]) for value in employee_ids) / 520
        overallocated = sum(allocation_hours_by_employee[value] > capacity_by_employee[value] for value in employee_ids)
        rolling_off = sum(start <= row["end_date"] <= min(end + timedelta(days=30), date.today() + timedelta(days=30)) for row in assignments)

        revenue_by_project = defaultdict(float)
        prior_by_project = defaultdict(float)
        for row in revenue:
            revenue_by_project[row["engagement_id"]] += row["amount"]
        for row in prior_revenue:
            prior_by_project[row["engagement_id"]] += row["amount"]
        risk_by_project = defaultdict(list)
        for row in risks:
            if row.get("engagement_id") in projects_by_id:
                risk_by_project[row["engagement_id"]].append(row)
        milestones_by_project = defaultdict(list)
        for row in milestones:
            milestones_by_project[row["engagement_id"]].append(row)

        opportunities = self._opportunities(pod_filter)
        pipeline_by_segment = defaultdict(float)
        weighted_by_segment = defaultdict(float)
        for row in opportunities:
            key = (row["pod"], row["division"], row["businessUnit"])
            pipeline_by_segment[key] += row["value"]
            weighted_by_segment[key] += row["weightedValue"]

        pod_dashboards = {pod_name: self.pod_store.dashboard(pod_name, "month", start.replace(day=1)) for pod_name in POD_STRUCTURE if not pod_filter or pod_name == pod_filter}
        relationship_by_segment = defaultdict(list)
        for pod_name, dashboard in pod_dashboards.items():
            people = {item["id"]: item for item in dashboard["people"]}
            for relationship in dashboard["relationships"]:
                person = people.get(relationship["stakeholderId"])
                if person and "Buyer" in person.get("role", ""):
                    relationship_by_segment[(pod_name, person.get("division"), person.get("unit"))].append(relationship)

        project_views = []
        for row in project_rows:
            team = assignments_by_project[row["id"]]
            team_capacity = sum(capacity_by_employee[value["employee_id"]] for value in team)
            team_billable = sum(billable_hours_by_employee[value["employee_id"]] for value in team)
            project_milestones = milestones_by_project[row["id"]]
            on_track = sum(value["status"] in ("Completed", "On Track") for value in project_milestones)
            sponsor = self.repository.stakeholders.get(row["executive_sponsor_id"])
            project_views.append({
                "id": row["id"], "name": row["name"], "pod": row["pod_id"], "division": row["division"], "businessUnit": row["business_unit"],
                "health": row["health"], "portfolioGroup": "Healthy" if row["health"] == "GREEN" else "Watch" if row["health"] == "AMBER" else "At Risk",
                "commercialValue": row["commercial_value"], "revenue": revenue_by_project[row["id"]], "teamSize": len(team),
                "utilization": team_billable / team_capacity if team_capacity else None, "milestonesOnTrack": on_track, "milestoneCount": len(project_milestones),
                "nextMilestone": min((value["due_date"] for value in project_milestones if value["due_date"] >= date.today()), default=None),
                "openRisks": len(risk_by_project[row["id"]]), "executiveSponsor": sponsor.name if sponsor else "Not linked", "stakeholderId": row["executive_sponsor_id"],
                "opportunityId": row["opportunity_id"], "renewalDate": row["renewal_date"].isoformat() if row["renewal_date"] else None,
            })
        for value in project_views:
            value["nextMilestone"] = value["nextMilestone"].isoformat() if value["nextMilestone"] else None

        pod_views, segment_views = [], []
        segment_keys = sorted({(row["pod_id"], row["division"], row["business_unit"]) for row in project_rows})
        for pod_name in sorted({row["pod_id"] for row in project_rows}, key=list(POD_STRUCTURE).index):
            rows = [row for row in project_views if row["pod"] == pod_name]
            pod_employee_ids = {value["employee_id"] for project in project_rows if project["pod_id"] == pod_name for value in assignments_by_project[project["id"]]}
            pod_capacity = sum(capacity_by_employee[value] for value in pod_employee_ids)
            pod_billable = sum(billable_hours_by_employee[value] for value in pod_employee_ids)
            dash = pod_dashboards[pod_name]
            pod_opps = [value for value in opportunities if value["pod"] == pod_name]
            pod_views.append({"pod": pod_name, "revenue": sum(row["revenue"] for row in rows), "pipeline": sum(value["value"] for value in pod_opps), "weightedPipeline": sum(value["weightedValue"] for value in pod_opps), "utilization": pod_billable / pod_capacity if pod_capacity else None, "headcount": len(pod_employee_ids), "activeProjects": len(rows), "projectsAtRisk": sum(row["health"] == "RED" for row in rows), "strategicStakeholders": sum("Buyer" in person["role"] for person in dash["people"]), "criticalIssues": sum(item["severity"] in ("RED", "AMBER") for item in dash["criticalItems"])})

        for key in segment_keys:
            pod_name, division, unit = key
            rows = [row for row in project_views if (row["pod"], row["division"], row["businessUnit"]) == key]
            project_ids_for_segment = {row["id"] for row in rows}
            segment_employee_ids = {value["employee_id"] for project_id in project_ids_for_segment for value in assignments_by_project[project_id]}
            segment_capacity = sum(capacity_by_employee[value] for value in segment_employee_ids)
            segment_billable = sum(billable_hours_by_employee[value] for value in segment_employee_ids)
            relationships = relationship_by_segment.get(key, [])
            attention_rate = sum(value["needsAttention"] for value in relationships) / len(relationships) if relationships else 1
            segment_revenue = sum(row["revenue"] for row in rows)
            segment_pipeline = pipeline_by_segment[key]
            segment_utilization = segment_billable / segment_capacity if segment_capacity else None
            red_risks = sum(row["health"] == "RED" for row in rows)
            milestone_total = sum(row["milestoneCount"] for row in rows)
            milestone_on_track = sum(row["milestonesOnTrack"] for row in rows)
            delivery_rate = milestone_on_track / milestone_total if milestone_total else None
            segment_views.append({"id": "-".join(value.lower().replace(" ", "-") for value in key), "pod": pod_name, "division": division, "businessUnit": unit, "revenue": segment_revenue, "pipeline": segment_pipeline, "weightedPipeline": weighted_by_segment[key], "utilization": segment_utilization, "headcount": len(segment_employee_ids), "activeProjects": len(rows), "projectsAtRisk": red_risks, "strategicStakeholders": sum(value.get("importance") == "High" for value in relationships), "meetingActivity": sum(value.get("days") is not None and value["days"] <= 60 for value in relationships), "deliveryOnTimeRate": delivery_rate, "relationshipAttentionRate": attention_rate, "heatmap": {"revenue": self._status(segment_revenue, 1_000_000, 500_000), "pipeline": self._status(segment_pipeline, 1_500_000, 500_000), "utilization": self._status(segment_utilization or 0, .85, .75), "delivery": self._status(delivery_rate or 0, .85, .70), "relationships": self._status(attention_rate, .25, .50, inverse=True), "risk": self._status(red_risks, 0, 1, inverse=True)}})

        total_revenue = sum(row["amount"] for row in revenue)
        total_prior_revenue = sum(row["amount"] for row in prior_revenue)
        target = sum(row["quarterly_revenue_target"] for row in project_rows)
        if period == "month": target /= 3
        elif period == "ytd": target *= max(1, ceil(end.month / 3))
        revenue_change = (total_revenue - total_prior_revenue) / total_prior_revenue if total_prior_revenue else None
        milestone_total = len(milestones)
        milestone_on_track = sum(row["status"] in ("Completed", "On Track") for row in milestones)
        red_risks = [row for row in risks if row["severity"] == "RED"]
        strategic_count = sum("Buyer" in person["role"] for dashboard in pod_dashboards.values() for person in dashboard["people"])
        relationship_attention = [
            row for dashboard in pod_dashboards.values()
            for row in dashboard["relationshipAttention"]
            if "Buyer" in next((person["role"] for person in dashboard["people"] if person["id"] == row["stakeholderId"]), "")
        ]

        capability_by_employee = defaultdict(set)
        for row in skills:
            capability_by_employee[row["employee_id"]].add(row["capability"])
        capability_rows = []
        for capability in CAPABILITIES:
            capable = [value for value in employee_ids if capability in capability_by_employee[value]]
            capacity_fte = sum(max(0, capacity_by_employee[value] - allocation_hours_by_employee[value]) for value in capable) / 520
            demand = sum(row["required_fte"] for row in demands if row["capability"] == capability)
            rounded_capacity, rounded_demand = round(capacity_fte, 1), round(demand, 1)
            capability_rows.append({"capability": capability, "availableCapacity": rounded_capacity, "demand": rounded_demand, "gap": round(rounded_capacity - rounded_demand, 1), "employeeIds": capable, "employees": [{"id": value, "name": employee_by_id[value]["name"], "role": employee_by_id[value]["role"]} for value in capable if value in employee_by_id], "demandIds": [row["id"] for row in demands if row["capability"] == capability]})

        attention = []
        for project in sorted((row for row in project_views if row["health"] == "RED"), key=lambda value: value["commercialValue"], reverse=True):
            attention.append({"id": f"attention-{project['id']}", "severity": "RED", "category": "DELIVERY", "title": project["name"], "context": f"{project['pod']} · {project['businessUnit']} · ${project['commercialValue'] / 1_000_000:.1f}M engagement", "reason": f"{project['milestoneCount'] - project['milestonesOnTrack']} milestones delayed or at risk · {project['openRisks']} linked open risks", "action": "Review engagement", "related": {"engagementIds": [project["id"]], "stakeholderIds": [project["stakeholderId"]], "opportunityIds": [project["opportunityId"]] if project["opportunityId"] else []}})
        for capability in sorted((row for row in capability_rows if row["gap"] < 0), key=lambda value: value["gap"]):
            attention.append({"id": f"attention-capacity-{capability['capability']}", "severity": "AMBER", "category": "CAPACITY", "title": f"{capability['capability']} capacity gap", "context": f"{capability['demand']:.1f} FTE demand vs {capability['availableCapacity']:.1f} FTE available", "reason": f"The 60-day demand plan exceeds qualified unallocated capacity by {abs(capability['gap']):.1f} FTE.", "action": "Review staffing", "related": {"employeeIds": capability["employeeIds"], "demandIds": capability["demandIds"]}})

        recommendations = []
        for project in sorted((row for row in project_views if row["health"] == "RED" and row["commercialValue"] >= 2_000_000), key=lambda value: value["commercialValue"], reverse=True):
            recommendations.append({"id": f"recommendation-delivery-{project['id']}", "category": "DELIVERY", "priority": "High", "recommendation": f"Intervene in {project['name']} delivery recovery", "why": f"A ${project['commercialValue'] / 1_000_000:.1f}M engagement is Red with {project['milestoneCount'] - project['milestonesOnTrack']} milestones delayed or at risk.", "suggestedAction": "Convene the Capco and client executive sponsors to agree a dated recovery plan this week.", "confidence": "High · direct project, milestone and risk records", "supportingMetrics": [{"label": "Commercial value", "value": project["commercialValue"]}, {"label": "Delivery health", "value": project["health"]}, {"label": "Milestones off track", "value": project["milestoneCount"] - project["milestonesOnTrack"]}], "relatedEntities": {"engagementIds": [project["id"]], "stakeholderIds": [project["stakeholderId"]], "opportunityIds": [project["opportunityId"]] if project["opportunityId"] else []}, "sourcePeriod": {"start": start.isoformat(), "end": end.isoformat()}})
        for capability in sorted((row for row in capability_rows if row["gap"] <= -1), key=lambda value: value["gap"]):
            recommendations.append({"id": f"recommendation-capacity-{capability['capability'].lower().replace(' ', '-')}", "category": "CAPACITY", "priority": "High" if capability["gap"] <= -3 else "Medium", "recommendation": f"Close the {capability['capability']} capacity gap", "why": f"Open 60-day demand is {capability['demand']:.1f} FTE while qualified available capacity is {capability['availableCapacity']:.1f} FTE.", "suggestedAction": f"Start redeployment or recruiting for {ceil(abs(capability['gap']))} additional FTE before the next mobilization gate.", "confidence": "High · employee skill, capacity, assignment and demand records", "supportingMetrics": [{"label": "Available capacity", "value": capability["availableCapacity"]}, {"label": "Demand", "value": capability["demand"]}, {"label": "Gap", "value": capability["gap"]}], "relatedEntities": {"employeeIds": capability["employeeIds"], "demandIds": capability["demandIds"]}, "sourcePeriod": {"start": start.isoformat(), "end": end.isoformat()}})
        stale_high = [row for row in relationship_attention if row.get("importance") == "High"]
        if stale_high:
            top = stale_high[0]
            linked_person = self.repository.stakeholders.get(top["stakeholderId"])
            relevant_opps = [row for row in opportunities if row["stakeholderId"] == top["stakeholderId"]]
            recommendations.append({"id": f"recommendation-relationship-{top['stakeholderId']}", "category": "RELATIONSHIP", "priority": "Medium", "recommendation": f"Re-engage {top['stakeholder']}", "why": f"This strategic relationship has {top['days'] if top['days'] is not None else 'no recorded'} days since the last linked client meeting and is tied to ${sum(row['value'] for row in relevant_opps) / 1_000_000:.1f}M pipeline.", "suggestedAction": "Schedule a Partner-level relationship meeting within two weeks and confirm the client decision path.", "confidence": "High · canonical stakeholder, meeting and opportunity records", "supportingMetrics": [{"label": "Days since meeting", "value": top["days"]}, {"label": "Linked pipeline", "value": sum(row["value"] for row in relevant_opps)}], "relatedEntities": {"stakeholderIds": [top["stakeholderId"]], "opportunityIds": [row["id"] for row in relevant_opps], "businessUnits": [linked_person.business_unit] if linked_person else []}, "sourcePeriod": {"start": start.isoformat(), "end": end.isoformat()}})

        stage_order = ["Qualification", "Discovery", "Proposal", "Negotiation", "Won", "Lost"]
        funnel = []
        for stage in stage_order:
            rows = [row for row in opportunities if row["stage"].casefold() == stage.casefold()]
            funnel.append({"stage": stage, "count": len(rows), "value": sum(row["value"] for row in rows), "weightedValue": sum(row["weightedValue"] for row in rows), "opportunityIds": [row["id"] for row in rows]})

        change_views = [{**row, "event_date": row["event_date"].isoformat()} for row in changes]
        return {
            "meta": {"period": period, "startDate": start.isoformat(), "endDate": end.isoformat(), "pod": pod_filter or "All", "generatedAt": datetime.now(timezone.utc).isoformat(), "dataSource": "sql", "definitions": {"utilization": "Billable allocated hours ÷ available working hours for employees with capacity records.", "weightedPipeline": "Opportunity value × persisted probability.", "deliveryOnTime": "Completed or on-track milestones ÷ milestones due in the selected period.", "capacityGap": "Qualified available FTE − open 60-day resource demand.", "heatmap": "Revenue: Strong ≥ $1M, Watch ≥ $500K. Pipeline: Strong ≥ $1.5M, Watch ≥ $500K. Utilization: Strong ≥ 85%, Watch ≥ 75%. Delivery: Strong ≥ 85%, Watch ≥ 70%. Relationships: Strong ≤ 25% attention, Watch ≤ 50%. Risk: Strong = 0 Red projects, Watch = 1."}},
            "accountPulse": {"revenue": total_revenue, "revenueChange": revenue_change, "revenueTargetAttainment": total_revenue / target if target else None, "pipeline": sum(row["value"] for row in opportunities), "weightedPipeline": sum(row["weightedValue"] for row in opportunities), "activeProjects": len(project_views), "projectsAtRisk": sum(row["health"] == "RED" for row in project_views), "headcount": len(employee_ids), "utilization": utilization, "milestonesOnTrack": milestone_on_track / milestone_total if milestone_total else None, "strategicStakeholders": strategic_count, "relationshipsNeedingAttention": len(relationship_attention), "criticalItems": len(risks), "redCriticalItems": len(red_risks)},
            "executiveAttention": attention[:6], "podPerformance": pod_views, "segmentPerformance": segment_views,
            "projectPortfolio": project_views, "workforce": {"activeEmployees": len(employee_ids), "billableEmployees": sum(billable_hours_by_employee[value] > 0 for value in employee_ids), "nonBillableEmployees": sum(billable_hours_by_employee[value] == 0 for value in employee_ids), "utilization": utilization, "allocatedUtilization": allocated_utilization, "availableCapacityFte": round(available_fte, 1), "rollingOff30Days": rolling_off, "openDemandFte": round(sum(row["required_fte"] for row in demands), 1), "overallocatedPeople": overallocated, "byPod": [{"pod": row["pod"], "utilization": row["utilization"], "headcount": row["headcount"]} for row in pod_views], "byLevel": [{"level": level, "count": sum(row["level"] == level for row in employee_rows)} for level in LEVELS], "byLocation": [{"location": location, "count": sum(row["location"] == location for row in employee_rows)} for location in LOCATIONS]},
            "capacityDemand": capability_rows, "commercial": {"revenue": total_revenue, "pipeline": sum(row["value"] for row in opportunities), "weightedPipeline": sum(row["weightedValue"] for row in opportunities), "averageDealSize": sum(row["value"] for row in opportunities) / len(opportunities) if opportunities else None, "funnel": funnel, "opportunities": opportunities},
            "delivery": {"activeEngagements": len(project_views), "green": sum(row["health"] == "GREEN" for row in project_views), "amber": sum(row["health"] == "AMBER" for row in project_views), "red": sum(row["health"] == "RED" for row in project_views), "milestonesOnTimeRate": milestone_on_track / milestone_total if milestone_total else None, "clientEscalations": sum("ESCALATION" in row["item_type"] for row in risks), "renewals90Days": sum(row.get("renewalDate") and date.fromisoformat(row["renewalDate"]) <= end + timedelta(days=90) for row in project_views)},
            "relationships": {"strategicStakeholders": strategic_count, "needingAttention": len(relationship_attention), "byPod": [{"pod": pod_name, "count": len([row for row in dashboard["relationshipAttention"] if "Buyer" in next((person["role"] for person in dashboard["people"] if person["id"] == row["stakeholderId"]), "")]), "high": sum(row["importance"] == "High" and "Buyer" in next((person["role"] for person in dashboard["people"] if person["id"] == row["stakeholderId"]), "") for row in dashboard["relationshipAttention"])} for pod_name, dashboard in pod_dashboards.items()], "items": relationship_attention[:10]},
            "changes": change_views, "recommendations": recommendations[:6],
        }

    @staticmethod
    def week_bounds(week_start: date | None = None) -> tuple[date, date]:
        anchor = week_start or date.today()
        start = anchor - timedelta(days=anchor.weekday())
        return start, start + timedelta(days=6)

    @staticmethod
    def _date_value(value) -> date | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value)[:10])

    def weekly(self, week_start: date | None = None, pod: str | None = None, outlook_weeks: int = 4) -> dict:
        """Weekly operating view derived from canonical people and account records."""
        if pod and pod != "All" and pod not in POD_STRUCTURE:
            raise ValueError("Unknown pod")
        if outlook_weeks not in range(1, 9):
            raise ValueError("outlook_weeks must be between 1 and 8")
        start, end = self.week_bounds(week_start)
        outlook_end = end + timedelta(weeks=outlook_weeks)
        pod_filter = None if not pod or pod == "All" else pod
        event_start = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
        event_end = datetime.combine(outlook_end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)

        with self.engine.connect() as connection:
            project_rows = [dict(row) for row in connection.execute(
                select(engagements).where(and_(
                    engagements.c.status == "Active", engagements.c.start_date <= outlook_end,
                    engagements.c.end_date >= start,
                    *([engagements.c.pod_id == pod_filter] if pod_filter else []),
                )).order_by(engagements.c.pod_id, engagements.c.name)
            ).mappings()]
            project_ids = [row["id"] for row in project_rows]
            assignment_rows = [dict(row) for row in connection.execute(
                select(engagement_assignments).where(and_(
                    engagement_assignments.c.engagement_id.in_(project_ids),
                    engagement_assignments.c.start_date <= end,
                    engagement_assignments.c.end_date >= start,
                    engagement_assignments.c.status == "Active",
                ))
            ).mappings()] if project_ids else []
            employee_ids = sorted({row["employee_id"] for row in assignment_rows})
            employee_rows = [dict(row) for row in connection.execute(
                select(employees).where(and_(employees.c.id.in_(employee_ids), employees.c.active.is_(True))).order_by(employees.c.name)
            ).mappings()] if employee_ids else []
            skill_rows = [dict(row) for row in connection.execute(
                select(employee_skills).where(employee_skills.c.employee_id.in_(employee_ids))
            ).mappings()] if employee_ids else []
            event_rows = [dict(row) for row in connection.execute(
                select(pod_events).where(and_(
                    pod_events.c.start_at >= event_start, pod_events.c.start_at < event_end,
                    *([pod_events.c.pod_id == pod_filter] if pod_filter else []),
                )).order_by(pod_events.c.start_at)
            ).mappings()]
            event_ids = [row["id"] for row in event_rows]
            attendee_rows = [dict(row) for row in connection.execute(
                select(pod_event_attendees).where(pod_event_attendees.c.event_id.in_(event_ids))
            ).mappings()] if event_ids else []
            task_rows = [dict(row) for row in connection.execute(
                select(pod_tasks).where(and_(
                    pod_tasks.c.due_date.between(start, outlook_end), pod_tasks.c.status != "Done",
                    *([pod_tasks.c.pod_id == pod_filter] if pod_filter else []),
                )).order_by(pod_tasks.c.due_date)
            ).mappings()]
            pod_milestone_rows = [dict(row) for row in connection.execute(
                select(pod_milestones).where(and_(
                    pod_milestones.c.milestone_date.between(start, outlook_end),
                    *([pod_milestones.c.pod_id == pod_filter] if pod_filter else []),
                )).order_by(pod_milestones.c.milestone_date)
            ).mappings()]
            engagement_milestone_rows = [dict(row) for row in connection.execute(
                select(engagement_milestones).where(and_(
                    engagement_milestones.c.engagement_id.in_(project_ids),
                    engagement_milestones.c.due_date.between(start, outlook_end),
                )).order_by(engagement_milestones.c.due_date)
            ).mappings()] if project_ids else []
            risk_rows = [dict(row) for row in connection.execute(
                select(pod_critical_items).where(and_(
                    pod_critical_items.c.status != "Resolved",
                    *([pod_critical_items.c.pod_id == pod_filter] if pod_filter else []),
                )).order_by(pod_critical_items.c.severity.desc(), pod_critical_items.c.due_date)
            ).mappings()]
            change_rows = [dict(row) for row in connection.execute(
                select(executive_changes).where(and_(
                    executive_changes.c.event_date.between(start - timedelta(days=7), end),
                    *([or_(executive_changes.c.pod_id == pod_filter, executive_changes.c.pod_id == "All")] if pod_filter else []),
                )).order_by(executive_changes.c.event_date.desc())
            ).mappings()]

        projects_by_id = {row["id"]: row for row in project_rows}
        employee_by_id = {row["id"]: row for row in employee_rows}
        assignments_by_employee = defaultdict(list)
        assignments_by_project = defaultdict(list)
        for row in assignment_rows:
            assignments_by_employee[row["employee_id"]].append(row)
            assignments_by_project[row["engagement_id"]].append(row)
        skills_by_employee = defaultdict(list)
        for row in skill_rows:
            skills_by_employee[row["employee_id"]].append(row["capability"])
        attendees_by_event = defaultdict(list)
        for row in attendee_rows:
            if row.get("employee_id") in employee_by_id:
                attendees_by_event[row["event_id"]].append(row["employee_id"])

        opportunity_to_project = {row["opportunity_id"]: row["id"] for row in project_rows if row.get("opportunity_id")}
        project_by_scope = {(row["pod_id"], row["business_unit"]): row["id"] for row in project_rows}
        activity_by_employee = defaultdict(list)
        calendar = []

        def event_project(row: dict) -> str | None:
            return opportunity_to_project.get(row.get("opportunity_id")) or project_by_scope.get((row["pod_id"], row.get("business_unit")))

        for row in event_rows:
            event_date = self._date_value(row["start_at"])
            project_id = event_project(row)
            employee_values = attendees_by_event[row["id"]]
            important = bool(row["is_client"] or row["importance"] == "High" or row["event_type"] in {"workshop", "deadline", "critical"})
            item = {
                "id": row["id"], "sourceType": "meeting" if row.get("source_meeting_id") else "event",
                "sourceId": row.get("source_meeting_id") or row["id"], "type": row["event_type"],
                "title": row["title"], "date": event_date.isoformat(),
                "start": row["start_at"].isoformat(), "end": row["end_at"].isoformat(),
                "allDay": row["all_day"], "pod": row["pod_id"], "businessUnit": row["business_unit"],
                "engagementId": project_id, "stakeholderId": row.get("stakeholder_id"),
                "opportunityId": row.get("opportunity_id"), "employeeIds": employee_values,
                "employees": [employee_by_id[value]["name"] for value in employee_values],
                "importance": row["importance"], "isClient": row["is_client"], "status": row["status"],
            }
            if start <= event_date <= end and important:
                calendar.append(item)
            for employee_id in employee_values:
                activity_by_employee[employee_id].append(item)

        for row in task_rows:
            employee_id = row.get("owner_employee_id")
            project_id = row.get("critical_item_id") and next((risk.get("engagement_id") for risk in risk_rows if risk["id"] == row["critical_item_id"]), None)
            project_id = project_id or opportunity_to_project.get(row.get("opportunity_id"))
            item = {
                "id": row["id"], "sourceType": "task", "sourceId": row["id"], "type": "deliverable",
                "title": row["title"], "date": row["due_date"].isoformat(), "allDay": True,
                "pod": row["pod_id"], "engagementId": project_id, "stakeholderId": row.get("stakeholder_id"),
                "opportunityId": row.get("opportunity_id"), "employeeIds": [employee_id] if employee_id else [],
                "employees": [employee_by_id[employee_id]["name"]] if employee_id in employee_by_id else [],
                "importance": row["priority"], "isClient": False, "status": row["status"],
            }
            if start <= row["due_date"] <= end and row["priority"] in {"High", "Critical"}:
                calendar.append(item)
            if employee_id in employee_by_id:
                activity_by_employee[employee_id].append(item)

        for row in pod_milestone_rows:
            employee_id = row.get("owner_employee_id")
            project_id = row.get("engagement_id") or opportunity_to_project.get(row.get("opportunity_id"))
            item = {
                "id": row["id"], "sourceType": "milestone", "sourceId": row["id"], "type": "milestone",
                "title": row["title"], "date": row["milestone_date"].isoformat(), "allDay": True,
                "pod": row["pod_id"], "engagementId": project_id, "stakeholderId": row.get("stakeholder_id"),
                "opportunityId": row.get("opportunity_id"), "employeeIds": [employee_id] if employee_id else [],
                "employees": [employee_by_id[employee_id]["name"]] if employee_id in employee_by_id else [],
                "importance": "High", "isClient": True, "status": "Upcoming",
            }
            if start <= row["milestone_date"] <= end:
                calendar.append(item)
            if employee_id in employee_by_id:
                activity_by_employee[employee_id].append(item)

        for row in engagement_milestone_rows:
            project = projects_by_id[row["engagement_id"]]
            lead_id = next((value["employee_id"] for value in assignments_by_project[row["engagement_id"]] if value["employee_id"] in employee_by_id), None)
            item = {
                "id": row["id"], "sourceType": "engagement_milestone", "sourceId": row["id"], "type": "milestone",
                "title": row["title"], "date": row["due_date"].isoformat(), "allDay": True,
                "pod": project["pod_id"], "businessUnit": project["business_unit"], "engagementId": project["id"],
                "stakeholderId": project.get("executive_sponsor_id"), "opportunityId": project.get("opportunity_id"),
                "employeeIds": [lead_id] if lead_id else [], "employees": [employee_by_id[lead_id]["name"]] if lead_id else [],
                "importance": "High" if row["status"] in {"Delayed", "At Risk"} else "Medium",
                "isClient": True, "status": row["status"],
            }
            if start <= row["due_date"] <= end:
                calendar.append(item)
            if lead_id:
                activity_by_employee[lead_id].append(item)

        calendar.sort(key=lambda item: (item["date"], item.get("start") or "23:59", item["title"]))

        team_activity = []
        for employee in employee_rows:
            employee_assignments = assignments_by_employee[employee["id"]]
            assignment_views = []
            for assignment in employee_assignments:
                project = projects_by_id[assignment["engagement_id"]]
                assignment_views.append({
                    "id": assignment["id"], "engagementId": project["id"], "engagement": project["name"],
                    "pod": project["pod_id"], "division": project["division"], "businessUnit": project["business_unit"],
                    "allocationPercent": assignment["allocation_percent"],
                    "role": assignment.get("assignment_role") or employee["role"],
                    "startDate": assignment["start_date"].isoformat(), "endDate": assignment["end_date"].isoformat(),
                })
            activities = sorted(activity_by_employee[employee["id"]], key=lambda item: (item["date"], item["title"]))
            current = [item for item in activities if start <= date.fromisoformat(item["date"]) <= end]
            upcoming = [item for item in activities if end < date.fromisoformat(item["date"]) <= outlook_end]
            if not current and assignment_views:
                primary = assignment_views[0]
                current = [{
                    "id": f"assignment-focus-{primary['id']}-{start.isoformat()}", "sourceType": "assignment",
                    "sourceId": primary["id"], "type": "project delivery",
                    "title": f"Core delivery on {primary['engagement']}", "date": start.isoformat(), "allDay": True,
                    "pod": primary["pod"], "businessUnit": primary["businessUnit"], "engagementId": primary["engagementId"],
                    "employeeIds": [employee["id"]], "employees": [employee["name"]], "importance": "Standard",
                    "isClient": False, "status": "Active assignment",
                }]
            primary_assignment = max(assignment_views, key=lambda value: value["allocationPercent"], default=None)
            name_parts = employee["name"].split(" ", 1)
            team_activity.append({
                "id": employee["id"], "name": employee["name"],
                "firstName": employee.get("first_name") or name_parts[0],
                "lastName": employee.get("last_name") or (name_parts[1] if len(name_parts) > 1 else ""),
                "title": employee.get("title") or employee["role"], "level": employee["level"], "role": employee["role"],
                "location": employee["location"], "capabilities": sorted(set(skills_by_employee[employee["id"]])),
                "pods": sorted({value["pod"] for value in assignment_views}, key=list(POD_STRUCTURE).index),
                "assignments": assignment_views, "primaryProject": primary_assignment["engagement"] if primary_assignment else "Account investment",
                "primaryEngagementId": primary_assignment["engagementId"] if primary_assignment else None,
                "allocationPercent": sum(value["allocationPercent"] for value in assignment_views),
                "activities": current, "nextFewWeeks": upcoming,
                "meetings": [value for value in current if value["sourceType"] == "meeting"],
                "tasks": [value for value in current if value["sourceType"] == "task"],
                "milestones": [value for value in current if "milestone" in value["sourceType"]],
                "stakeholderIds": sorted({value.get("stakeholderId") for value in activities if value.get("stakeholderId")}),
                "opportunityIds": sorted({value.get("opportunityId") for value in activities if value.get("opportunityId")}),
            })

        opportunities = self._opportunities(pod_filter)
        opportunity_by_id = {row["id"]: row for row in opportunities}
        for employee in team_activity:
            employee["stakeholders"] = [
                {"id": stakeholder_id, "name": self.repository.stakeholders[stakeholder_id].name}
                for stakeholder_id in employee["stakeholderIds"]
                if stakeholder_id in self.repository.stakeholders
            ]
            employee["opportunities"] = [
                {
                    "id": opportunity_id,
                    "name": opportunity_by_id[opportunity_id]["name"],
                    "stage": opportunity_by_id[opportunity_id]["stage"],
                    "value": opportunity_by_id[opportunity_id]["value"],
                }
                for opportunity_id in employee["opportunityIds"]
                if opportunity_id in opportunity_by_id
            ]
        pipeline = sum(row["value"] for row in opportunities if row["stage"] not in {"Won", "Lost"})
        weighted_pipeline = sum(row["weightedValue"] for row in opportunities if row["stage"] not in {"Won", "Lost"})
        near_term_end = end + timedelta(weeks=8)
        near_term = [row for row in opportunities if row.get("targetCloseDate") and start <= date.fromisoformat(row["targetCloseDate"]) <= near_term_end and row["stage"] not in {"Won", "Lost"}]
        if not near_term:
            near_term = sorted((row for row in opportunities if row["stage"] in {"Proposal", "Negotiation"}), key=lambda row: row["value"], reverse=True)[:5]
        project_by_opportunity = {row.get("opportunity_id"): row for row in project_rows if row.get("opportunity_id")}
        sales_items = []
        for row in sorted(near_term, key=lambda value: (value.get("targetCloseDate") or "9999", -value["value"]))[:6]:
            project = project_by_opportunity.get(row["id"])
            project_team = assignments_by_project[project["id"]] if project else []
            sales_items.append({
                **row, "engagementId": project["id"] if project else None,
                "project": project["name"] if project else None,
                "team": [{"id": value["employee_id"], "name": employee_by_id[value["employee_id"]]["name"]} for value in project_team[:4] if value["employee_id"] in employee_by_id],
                "nextStep": "Prepare the client decision and proposal discussion" if row["stage"] in {"Proposal", "Negotiation"} else "Confirm the next qualification commitment",
            })

        project_views = []
        for project in project_rows:
            project_team = [value for value in assignments_by_project[project["id"]] if value["employee_id"] in employee_by_id]
            future_milestones = [value for value in engagement_milestone_rows if value["engagement_id"] == project["id"] and value["due_date"] >= start]
            future_pod_milestones = [value for value in pod_milestone_rows if value.get("engagement_id") == project["id"] and value["milestone_date"] >= start]
            candidates = ([{"title": value["title"], "date": value["due_date"], "status": value["status"]} for value in future_milestones] +
                          [{"title": value["title"], "date": value["milestone_date"], "status": "Upcoming"} for value in future_pod_milestones])
            next_milestone = min(candidates, key=lambda value: value["date"], default=None)
            sponsor = self.repository.stakeholders.get(project.get("executive_sponsor_id"))
            project_views.append({
                "id": project["id"], "name": project["name"], "pod": project["pod_id"], "division": project["division"],
                "businessUnit": project["business_unit"], "health": project["health"],
                "commercialValue": project["commercial_value"], "teamSize": len(project_team),
                "team": [{"id": value["employee_id"], "name": employee_by_id[value["employee_id"]]["name"], "role": value.get("assignment_role") or employee_by_id[value["employee_id"]]["role"], "allocationPercent": value["allocation_percent"]} for value in project_team],
                "nextMilestone": {**next_milestone, "date": next_milestone["date"].isoformat()} if next_milestone else None,
                "stakeholderId": project.get("executive_sponsor_id"), "executiveSponsor": sponsor.name if sponsor else "Not linked",
                "opportunityId": project.get("opportunity_id"),
            })

        attention = []
        for project in sorted((value for value in project_views if value["health"] == "RED"), key=lambda value: value["commercialValue"], reverse=True):
            lead = project["team"][0] if project["team"] else None
            attention.append({
                "id": f"weekly-attention-{project['id']}", "severity": "RED", "category": "DELIVERY",
                "title": f"{project['name']} requires delivery intervention", "pod": project["pod"],
                "context": f"{project['businessUnit']} · {project['teamSize']} Capco", "impact": project["commercialValue"],
                "owner": lead["name"] if lead else "Account leadership", "ownerEmployeeId": lead["id"] if lead else None,
                "nextAction": project["nextMilestone"]["title"] if project["nextMilestone"] else "Agree a dated recovery plan this week",
                "dueDate": project["nextMilestone"]["date"] if project["nextMilestone"] else end.isoformat(),
                "engagementId": project["id"], "stakeholderId": project["stakeholderId"], "opportunityId": project["opportunityId"],
            })
        for risk in risk_rows:
            if len(attention) >= 5 or risk["severity"] not in {"RED", "AMBER"}:
                continue
            owner = employee_by_id.get(risk.get("owner_employee_id"))
            attention.append({
                "id": f"weekly-risk-{risk['id']}", "severity": risk["severity"], "category": risk["item_type"],
                "title": risk["title"], "pod": risk["pod_id"], "context": risk["description"],
                "impact": projects_by_id.get(risk.get("engagement_id"), {}).get("commercial_value"),
                "owner": owner["name"] if owner else risk.get("owner_id") or "Account leadership",
                "ownerEmployeeId": owner["id"] if owner else None,
                "nextAction": "Resolve or confirm the management path", "dueDate": risk["due_date"].isoformat() if risk.get("due_date") else None,
                "engagementId": risk.get("engagement_id"), "stakeholderId": risk.get("stakeholder_id"), "opportunityId": risk.get("opportunity_id"),
            })
        rolloffs = [row for row in assignment_rows if end < row["end_date"] <= outlook_end]
        if rolloffs and len(attention) < 5:
            attention.append({
                "id": "weekly-rolloffs", "severity": "AMBER", "category": "STAFFING",
                "title": f"{len(rolloffs)} consultants roll off in the next {outlook_weeks} weeks", "pod": "All" if not pod_filter else pod_filter,
                "context": "Confirm replacement demand and redeployment plans", "impact": None,
                "owner": "Account leadership", "ownerEmployeeId": None,
                "nextAction": "Review assignment end dates and open demand", "dueDate": min(row["end_date"] for row in rolloffs).isoformat(),
                "employeeIds": [row["employee_id"] for row in rolloffs],
            })

        pod_summaries = []
        for pod_name in POD_STRUCTURE:
            if pod_filter and pod_name != pod_filter:
                continue
            pod_projects = [row for row in project_views if row["pod"] == pod_name]
            pod_project_ids = {row["id"] for row in pod_projects}
            pod_employee_ids = {row["employee_id"] for project_id in pod_project_ids for row in assignments_by_project[project_id]}
            pod_calendar = [row for row in calendar if row["pod"] == pod_name]
            critical_count = sum(row["pod"] == pod_name and row["severity"] == "RED" for row in attention)
            focus_project = next((row for row in pod_projects if row["health"] == "RED"), None) or (max(pod_projects, key=lambda row: row["commercialValue"], default=None))
            pod_summaries.append({
                "pod": pod_name, "employeeCount": len(pod_employee_ids),
                "clientMeetings": sum(row["isClient"] and row["type"] in {"client", "workshop"} for row in pod_calendar),
                "keyMilestones": sum(row["type"] in {"milestone", "deadline", "deliverable"} for row in pod_calendar),
                "criticalIssues": critical_count, "primaryFocus": focus_project["name"] if focus_project else "Account coverage",
                "primaryEngagementId": focus_project["id"] if focus_project else None,
            })

        upcoming_weeks = []
        all_future_items = []
        for row in event_rows:
            event_date = self._date_value(row["start_at"])
            if end < event_date <= outlook_end and (row["is_client"] or row["importance"] == "High" or row["event_type"] in {"deadline", "critical", "workshop"}):
                all_future_items.append({"id": row["id"], "date": event_date, "type": row["event_type"], "title": row["title"], "pod": row["pod_id"], "engagementId": event_project(row), "stakeholderId": row.get("stakeholder_id"), "opportunityId": row.get("opportunity_id")})
        for row in task_rows:
            if end < row["due_date"] <= outlook_end and row["priority"] in {"High", "Critical"}:
                all_future_items.append({"id": row["id"], "date": row["due_date"], "type": "deliverable", "title": row["title"], "pod": row["pod_id"], "opportunityId": row.get("opportunity_id")})
        for row in pod_milestone_rows:
            if end < row["milestone_date"] <= outlook_end:
                all_future_items.append({"id": row["id"], "date": row["milestone_date"], "type": "milestone", "title": row["title"], "pod": row["pod_id"], "engagementId": row.get("engagement_id"), "stakeholderId": row.get("stakeholder_id")})
        for row in engagement_milestone_rows:
            if end < row["due_date"] <= outlook_end:
                project = projects_by_id[row["engagement_id"]]
                all_future_items.append({"id": row["id"], "date": row["due_date"], "type": "milestone", "title": f"{project['name']}: {row['title']}", "pod": project["pod_id"], "engagementId": project["id"]})
        for row in rolloffs:
            project = projects_by_id[row["engagement_id"]]
            all_future_items.append({"id": f"rolloff-{row['id']}", "date": row["end_date"], "type": "staffing", "title": f"{employee_by_id[row['employee_id']]['name']} rolls off {project['name']}", "pod": project["pod_id"], "engagementId": project["id"], "employeeId": row["employee_id"]})
        for index in range(1, outlook_weeks + 1):
            bucket_start = start + timedelta(weeks=index)
            bucket_end = bucket_start + timedelta(days=6)
            items = sorted((row for row in all_future_items if bucket_start <= row["date"] <= bucket_end), key=lambda row: row["date"])
            upcoming_weeks.append({"weekStart": bucket_start.isoformat(), "weekEnd": bucket_end.isoformat(), "items": [{**row, "date": row["date"].isoformat()} for row in items[:6]]})

        change_views = [{**row, "event_date": row["event_date"].isoformat()} for row in change_rows[:5]]
        historical = self.overview("quarter", anchor=start, pod=pod_filter)
        return {
            "meta": {"weekStart": start.isoformat(), "weekEnd": end.isoformat(), "outlookEnd": outlook_end.isoformat(), "pod": pod_filter or "All", "generatedAt": datetime.now(timezone.utc).isoformat(), "dataSource": "normalized-sql"},
            "pulse": {"activeEmployees": len(employee_ids), "importantEvents": len(calendar), "attentionItems": len(attention), "activeProjects": len(project_views), "pipeline": pipeline, "upcomingMilestones": sum(row["type"] in {"milestone", "deadline", "deliverable"} for row in calendar)},
            "teamActivity": team_activity, "weeklyCalendar": calendar, "attentionItems": attention,
            "podSummaries": pod_summaries, "upcomingWeeks": upcoming_weeks, "projects": project_views,
            "salesSummary": {"pipeline": pipeline, "weightedPipeline": weighted_pipeline, "nearTermOpportunities": len(near_term), "upcomingProposalsDecisions": sum(row["stage"] in {"Proposal", "Negotiation"} for row in near_term), "opportunities": sales_items},
            "changes": change_views, "recommendations": historical["recommendations"][:3],
        }

    def counts(self) -> dict:
        with self.engine.connect() as connection:
            return {table.name: connection.execute(select(func.count()).select_from(table)).scalar_one() for table in (engagements, employees, employee_skills, employee_capacity, engagement_assignments, revenue_records, engagement_milestones, resource_demand, executive_changes)}
