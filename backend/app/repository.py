from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from itertools import cycle
from threading import RLock
from typing import Iterable, Optional
from uuid import uuid4

from .models import (
    AssignmentHistory,
    DocumentLink,
    DocumentLinkCreate,
    DocumentLinkUpdate,
    MapResponse,
    Meeting,
    MeetingCreate,
    MeetingUpdate,
    Note,
    NoteCreate,
    NoteUpdate,
    Opportunity,
    OpportunityCreate,
    OpportunityUpdate,
    ReportingLine,
    Stakeholder,
    StakeholderCreate,
    StakeholderUpdate,
)


POD_STRUCTURE = {
    "ISG": {
        "Front Office": ["Equities", "Fixed Income", "Prime Services", "Research"],
        "Middle Office": ["Risk Management", "Data Management", "Compliance", "Operations"],
        "Back Office": ["Finance", "Settlement", "Client Services"],
    },
    "Wealth Management": {
        "Front Office": ["Private Wealth", "Family Office", "Client Coverage"],
        "Middle Office": ["Advisory Operations", "Data & Insights"],
        "Back Office": ["Risk & Controls", "Client Technology"],
    },
    "MSIM": {
        "Front Office": ["Public Markets", "Alternatives", "Institutional Distribution"],
        "Middle Office": ["Fund Services", "Performance & Analytics", "Investment Risk"],
        "Back Office": ["Finance", "Operations Technology"],
    },
}

DIVISION_COLORS = {
    "Front Office": "#1675d1",
    "Middle Office": "#287a5b",
    "Back Office": "#8850a6",
}

DIVISION_HEADS = {
    "ISG": ["John Smith", "David Patel", "Robert Brown"],
    "Wealth Management": ["Laura Bennett", "Marcus Reed", "Amelia Grant"],
    "MSIM": ["Victor Shaw", "Sofia Martin", "Grace Lee"],
}

POD_HEADS = {
    "ISG": ("Dan Simkowitz", "Co-President; responsible for Institutional Securities Group"),
    "Wealth Management": ("Jed Finn", "Head of Wealth Management"),
    "MSIM": ("Ben Huneke", "Head of Morgan Stanley Investment Management"),
}

UNIT_LEADS = [
    "Emily Davis", "Michael Lowe", "Tom Green", "Laura Hill", "Luca Chen", "Maya Wong",
    "Noah Patel", "Jordan Tan", "Katie Thompson", "Ben Wilson", "Nicole Martin", "Olivia Stone",
    "Ava Patel", "Lucas Wong", "Mason Lee", "Iris Chen", "Nora Diaz", "Kai Wong", "Ari Davis",
    "Victor Lee", "Tara Singh", "Evan Cole", "Oliver Shah", "Ian Chen", "Sofia Grant",
]

TECHNOLOGY_LEADS = [
    "Daniel Kim", "Victoria Kim", "Nora Patel", "Julia Cole", "Hugo Park", "Yara Patel",
    "Amelia Grant", "Sarah Malik", "Paul White", "Zoe Kim", "Riley Martin", "Priya Rao",
    "Rina Shah", "Tom Blake", "Maya Singh", "Hugo Chen", "Amelia Ford", "Samir Desai",
]

PEOPLE = [
    "Robert Stone", "Anna Clark", "Maya Wilson", "Sarah Singh", "Michael Tan", "Alan Li",
    "Jon Bell", "Sofia Patel", "James Lee", "Ravi Shah", "Hana Bae", "Ava Martin",
    "Sofia Khan", "Nina Victor", "Ben Cole", "Hugo Brown", "Priya Menon", "Alex Adams",
    "Dylan Stone", "Zoe Khan", "Rina Mehta", "Ethan Gray", "Victor Cole", "Gabe Bell",
    "Amelia Lewis", "Kai Menon", "Lena Kim", "Mason Gray", "Sofia Chen", "Ravi Rao",
    "Peter Long", "Sasha Bell", "Simon Price", "Dina Ross", "Jordan Davis", "Nora Lee",
    "Mark Ross", "Priya Morris", "Riley Stone", "Mia Green", "Ravi Patel", "Emma Wong",
    "Hannah Lee", "Chris Wong", "Julia Grant", "Kai Thomas", "James Patel", "Amanda Chen",
    "Robert Jones", "Priya Shah", "Victor Kim", "Liam Ross", "Chloe Martin", "Yara Price",
    "Imani Das", "Alex Grant", "Sam Miller", "Ben Price", "Tariq Bell", "Tessa Brooks",
    "Leo Patel", "Uma Singh", "Avery Cole", "Riley Shah", "Morgan Blake", "Taylor Brooks",
    "Casey Rivera", "Riley Chen", "Morgan Shah", "Aiden Murphy", "Charlotte Evans", "Diego Santos",
    "Fatima Noor", "Kenji Sato", "Mei Lin", "Elena Rossi", "Omar Haddad", "Lucia Garcia",
]

LOCATIONS = [
    ("New York, USA", "US"), ("London, UK", "UK"), ("Toronto, Canada", "CA"),
    ("Singapore", "SG"), ("Mumbai, India", "IN"), ("Hong Kong", "HK"),
    ("Tokyo, Japan", "JP"), ("Frankfurt, Germany", "DE"),
]

CAPCO_OWNERS = ["Alex Morgan", "Priya Desai", "Chris Walker", "Jordan Brooks", "Unassigned"]
RELATIONSHIP_STRENGTHS = ["Strong", "Medium", "Developing", "Unknown"]
LEVELS = ["Executive Director", "Vice President", "Vice President", "Director", "Associate"]

UNIT_TAGS = {
    "Equities": ["Electronic Trading", "Digital Assets", "Market Data", "AI/ML"],
    "Fixed Income": ["Pricing", "Risk Analytics", "Trading Platforms", "Cloud"],
    "Prime Services": ["Client Experience", "Financing", "Collateral", "Automation"],
    "Research": ["GenAI", "Knowledge Management", "Data", "Analytics"],
    "Risk Management": ["Market Risk", "Controls", "Scenario Analysis", "Regulatory"],
    "Data Management": ["Data Governance", "Data Quality", "Cloud", "Metadata"],
    "Compliance": ["Surveillance", "Regulatory", "Financial Crime", "Automation"],
    "Operations": ["Process Optimization", "Automation", "Controls", "Resilience"],
    "Finance": ["Product Control", "Treasury", "Reporting", "Data"],
    "Settlement": ["Post Trade", "Payments", "Reconciliation", "Resilience"],
    "Client Services": ["Client Experience", "Onboarding", "Workflow", "Digital"],
    "Private Wealth": ["Advisor Experience", "Portfolio Management", "Digital", "Data"],
    "Family Office": ["Alternatives", "Tax", "Reporting", "Client Experience"],
    "Client Coverage": ["CRM", "Analytics", "Client Experience", "Digital"],
    "Advisory Operations": ["Workflow", "Controls", "Automation", "Data"],
    "Data & Insights": ["AI/ML", "Analytics", "Cloud", "Data Governance"],
    "Risk & Controls": ["Operational Risk", "Controls", "Regulatory", "Resilience"],
    "Client Technology": ["Digital", "Cloud", "Cyber", "Client Experience"],
    "Public Markets": ["Portfolio Analytics", "Trading", "Research", "Data"],
    "Alternatives": ["Private Markets", "Portfolio Management", "Data", "Reporting"],
    "Institutional Distribution": ["CRM", "Client Experience", "Analytics", "Digital"],
    "Fund Services": ["Fund Accounting", "NAV", "Controls", "Automation"],
    "Performance & Analytics": ["Attribution", "Data", "Analytics", "Cloud"],
    "Investment Risk": ["Risk Analytics", "Scenario Analysis", "Data", "Regulatory"],
    "Operations Technology": ["Cloud", "Automation", "Resilience", "Cyber"],
}

ENTERPRISE_FUNCTIONS = [
    ("Center of Enablement", "Jessica Adams", "Head of Enablement"),
    ("HR Team", "Priya Nair", "HR Director"),
    ("Legal Team", "George Hall", "General Counsel"),
]


def slug(value: str) -> str:
    return "-".join("".join(char.lower() if char.isalnum() else " " for char in value).split())


class DomainError(ValueError):
    pass


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class StakeholderRepository:
    """Thread-safe seeded repository used by the API and replaceable by PostgreSQL storage."""

    def __init__(self, seed_data: bool = True) -> None:
        self._lock = RLock()
        self.account_name = "Morgan Stanley"
        self.pod_order: list[str] = []
        self.stakeholders: dict[str, Stakeholder] = {}
        self.pod_heads: dict[str, str] = {}
        self.units: dict[str, dict] = {}
        self.divisions: dict[str, dict] = {}
        self.enterprise: dict[str, list[dict]] = defaultdict(list)
        self.meetings: dict[str, Meeting] = {}
        self.notes: dict[str, Note] = {}
        self.documents: dict[str, DocumentLink] = {}
        self.opportunities: dict[str, Opportunity] = {}
        self.history: list[AssignmentHistory] = []
        self.dashboard_task_statuses: dict[str, str] = {}
        self.dashboard_task_records: dict[str, dict] = {}
        self.dashboard_focus: dict[str, list[str]] = {}
        self.dashboard_critical_statuses: dict[str, str] = {}
        if seed_data:
            self._seed()

    def pod_names(self) -> list[str]:
        """Return the persisted pod order, falling back to loaded stakeholder scope."""
        if self.pod_order:
            return list(self.pod_order)
        return list(dict.fromkeys(item.pod for item in self.stakeholders.values()))

    def organization_structure(self) -> dict[str, dict[str, list[str]]]:
        structure: dict[str, dict[str, list[str]]] = {pod: {} for pod in self.pod_names()}
        divisions = sorted(self.divisions.values(), key=lambda item: (self.pod_names().index(item["pod"]), item["name"]))
        for division in divisions:
            structure.setdefault(division["pod"], {})[division["name"]] = [
                self.units[unit_id]["name"] for unit_id in division["unit_ids"]
            ]
        return structure

    def update_dashboard_task_status(self, pod: str, task_id: str, status: str) -> None:
        with self._lock:
            self.dashboard_task_statuses[f"{pod}:{task_id}"] = status

    def save_dashboard_task(self, pod: str, task: dict) -> dict:
        with self._lock:
            record = {**task, "pod": pod}
            self.dashboard_task_records[f"{pod}:{task['id']}"] = record
            return record

    def save_dashboard_focus(self, pod: str, focus: list[str]) -> list[str]:
        with self._lock:
            self.dashboard_focus[pod] = focus
            return focus

    def update_dashboard_critical_status(self, pod: str, item_id: str, status: str) -> None:
        with self._lock:
            self.dashboard_critical_statuses[f"{pod}:{item_id}"] = status

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)

    def _seed(self) -> None:
        name_stream = cycle(PEOPLE)
        lead_stream = cycle(UNIT_LEADS)
        tech_stream = cycle(TECHNOLOGY_LEADS)
        location_stream = cycle(LOCATIONS)
        global_unit_index = 0

        for pod_index, (pod, division_structure) in enumerate(POD_STRUCTURE.items()):
            self.pod_order.append(pod)
            pod_head_name, pod_head_title = POD_HEADS[pod]
            pod_head = self._seed_person(
                stakeholder_id=f"{slug(pod)}-pod-head",
                name=pod_head_name,
                title=pod_head_title,
                pod=pod,
                division=None,
                unit=None,
                team_type="Business",
                role="Pod Head",
                level="Executive Leadership",
                location=("Not recorded", ""),
                relationship="Strong",
                buyer=True,
                budget_holder=True,
                tags=[pod, "Executive Leadership"],
            )
            self.pod_heads[pod] = pod_head.id
            for division_index, (division_name, unit_names) in enumerate(division_structure.items()):
                division_id = f"{slug(pod)}-{slug(division_name)}"
                head_name = DIVISION_HEADS[pod][division_index]
                head = self._seed_person(
                    stakeholder_id=f"{division_id}-head",
                    name=head_name,
                    title=f"Head of {division_name}",
                    pod=pod,
                    division=division_name,
                    unit="Division Leadership",
                    team_type="Business",
                    role="Division Head",
                    level="Managing Director",
                    location=LOCATIONS[(pod_index + division_index) % len(LOCATIONS)],
                    relationship="Strong",
                    manager_id=pod_head.id,
                    buyer=True,
                    budget_holder=True,
                    tags=["Strategy", "Transformation", "Executive Leadership"],
                )
                self.divisions[division_id] = {
                    "id": division_id,
                    "pod": pod,
                    "name": division_name,
                    "color": DIVISION_COLORS[division_name],
                    "head_stakeholder_id": head.id,
                    "unit_ids": [],
                }

                for local_unit_index, unit_name in enumerate(unit_names):
                    unit_index = global_unit_index
                    global_unit_index += 1
                    unit_id = f"{division_id}-{slug(unit_name)}"
                    tags = UNIT_TAGS.get(unit_name, ["Transformation", "Data", "Cloud"])
                    lead_name = next(lead_stream)
                    lead = self._seed_person(
                        stakeholder_id=f"{unit_id}-business-head",
                        name=lead_name,
                        title=f"Head of {unit_name}",
                        pod=pod,
                        division=division_name,
                        unit=unit_name,
                        team_type="Business",
                        role="Business Unit Head",
                        level="Managing Director" if unit_index % 3 == 0 else "Executive Director",
                        manager_id=head.id,
                        location=next(location_stream),
                        relationship=RELATIONSHIP_STRENGTHS[unit_index % 3],
                        buyer=True,
                        budget_holder=unit_index % 2 == 0,
                        tags=tags,
                    )

                    business_ids = [lead.id]
                    branch_leads: list[Stakeholder] = []
                    branch_titles = self._branch_titles(unit_name)
                    for branch_index, branch_title in enumerate(branch_titles):
                        branch = self._seed_person(
                            stakeholder_id=f"{unit_id}-business-{branch_index + 1}",
                            name=next(name_stream),
                            title=branch_title,
                            pod=pod,
                            division=division_name,
                            unit=unit_name,
                            team_type="Business",
                            role="Business Stakeholder",
                            level=LEVELS[(unit_index + branch_index) % len(LEVELS)],
                            manager_id=lead.id,
                            location=next(location_stream),
                            relationship=RELATIONSHIP_STRENGTHS[(unit_index + branch_index) % len(RELATIONSHIP_STRENGTHS)],
                            buyer=branch_index == 0 and unit_index % 2 == 0,
                            budget_holder=branch_index == 1 and unit_index % 3 == 0,
                            tags=tags[branch_index % len(tags):] + tags[:branch_index % len(tags)],
                        )
                        branch_leads.append(branch)
                        business_ids.append(branch.id)

                    # Vary depth by business unit: some branches have one report, others two.
                    nested_count = 2 if unit_index % 3 == 0 else 1
                    for nested_index in range(nested_count):
                        parent = branch_leads[nested_index % len(branch_leads)]
                        report = self._seed_person(
                            stakeholder_id=f"{unit_id}-business-nested-{nested_index + 1}",
                            name=next(name_stream),
                            title=self._specialist_title(unit_name, nested_index),
                            pod=pod,
                            division=division_name,
                            unit=unit_name,
                            team_type="Business",
                            role="Business Stakeholder",
                            level="Director" if nested_index == 0 else "Vice President",
                            manager_id=parent.id,
                            location=next(location_stream),
                            relationship=RELATIONSHIP_STRENGTHS[(unit_index + nested_index + 1) % len(RELATIONSHIP_STRENGTHS)],
                            tags=tags,
                        )
                        business_ids.append(report.id)

                    unknown_ids: list[str] = []

                    tech_name = next(tech_stream)
                    primary_tech = self._seed_person(
                        stakeholder_id=f"{unit_id}-technology-primary",
                        name=tech_name,
                        title=f"VP, {unit_name} Technology",
                        pod=pod,
                        division=division_name,
                        unit=unit_name,
                        team_type="Technology",
                        role="Primary Technology Stakeholder",
                        level="Executive Director" if unit_index % 4 == 0 else "Vice President",
                        manager_id=lead.id,
                        is_primary=True,
                        location=next(location_stream),
                        relationship="Strong" if unit_index % 2 == 0 else "Medium",
                        buyer=unit_index % 5 == 0,
                        budget_holder=unit_index % 2 == 0,
                        tags=["Technology Strategy", *tags[:3]],
                    )
                    technology_ids = [primary_tech.id]
                    technology_team_size = 3 + unit_index % 5
                    for tech_index in range(technology_team_size):
                        technologist = self._seed_person(
                            stakeholder_id=f"{unit_id}-technology-{tech_index + 1}",
                            name=next(name_stream),
                            title=["Engineering Director", "Platform Lead", "Product Manager", "Architecture Lead", "Delivery Lead", "Data Engineering Lead", "Site Reliability Lead"][tech_index],
                            pod=pod,
                            division=division_name,
                            unit=unit_name,
                            team_type="Technology",
                            role="Technology Team Member",
                            level=LEVELS[(tech_index + 2) % len(LEVELS)],
                            manager_id=primary_tech.id,
                            location=next(location_stream),
                            relationship=RELATIONSHIP_STRENGTHS[(tech_index + unit_index) % len(RELATIONSHIP_STRENGTHS)],
                            tags=["Technology", *tags[:2]],
                        )
                        technology_ids.append(technologist.id)

                    self.units[unit_id] = {
                        "id": unit_id,
                        "pod": pod,
                        "division": division_name,
                        "name": unit_name,
                        "sort_order": local_unit_index,
                        "business_stakeholder_ids": business_ids,
                        "technology_stakeholder_ids": technology_ids,
                        "primary_technology_id": primary_tech.id,
                        "reporting_unknown_ids": unknown_ids,
                    }
                    self.divisions[division_id]["unit_ids"].append(unit_id)

            self._seed_enterprise_functions(pod, name_stream, location_stream)

        self._seed_activity()
        self._seed_documents()
        self._refresh_derived_fields()

    def _seed_person(
        self,
        *, stakeholder_id: str, name: str, title: str, pod: str, division: Optional[str], unit: Optional[str],
        team_type: str, role: str, level: str, location: tuple[str, str], relationship: str,
        manager_id: Optional[str] = None, is_primary: bool = False, buyer: bool = False,
        budget_holder: bool = False, tags: Optional[list[str]] = None,
    ) -> Stakeholder:
        now = self.now()
        relationship_offset = {"Strong": 18, "Medium": 55, "Developing": 105, "Unknown": 220}[relationship]
        stakeholder = Stakeholder(
            id=stakeholder_id,
            assignment_id=f"assignment-{stakeholder_id}",
            name=name,
            title=title,
            pod=pod,
            division=division,
            business_unit=unit,
            team_type=team_type,
            organizational_role=role,
            level=level,
            location=location[0],
            country_code=location[1],
            manager_id=manager_id,
            is_primary_technology=is_primary,
            is_buyer=buyer,
            is_influencer=level in {"Managing Director", "Executive Director", "Vice President"},
            is_budget_holder=budget_holder,
            relationship_strength=relationship,
            capco_contingents=0 if relationship == "Unknown" else 1 + (sum(ord(c) for c in stakeholder_id) % 4),
            capco_owner=None if relationship == "Unknown" else CAPCO_OWNERS[sum(ord(c) for c in name) % (len(CAPCO_OWNERS) - 1)],
            budget_amount=(1_000_000 + (sum(ord(c) for c in name) % 8) * 500_000) if budget_holder else None,
            biography=f"{name} is a {role.lower()} focused on {', '.join((tags or ['transformation'])[:2])}. The account team tracks organizational priorities, decision influence, and engagement history for this stakeholder.",
            tags=list(dict.fromkeys(tags or [])),
            last_meeting=(now - timedelta(days=relationship_offset)).date() if relationship != "Unknown" else None,
            next_meeting=(now + timedelta(days=12 + relationship_offset % 21)).date() if relationship in {"Strong", "Medium"} else None,
            opportunity_count=0,
            created_at=now - timedelta(days=365 + relationship_offset),
            updated_at=now - timedelta(days=relationship_offset // 2),
        )
        self.stakeholders[stakeholder.id] = stakeholder
        return stakeholder

    @staticmethod
    def _branch_titles(unit_name: str) -> list[str]:
        stem = unit_name.replace("Management", "").replace("Services", "").strip()
        return [f"{stem} Product Lead", f"{stem} Coverage Lead", f"{stem} Operations Lead"]

    @staticmethod
    def _specialist_title(unit_name: str, index: int) -> str:
        suffixes = ["Senior Specialist", "Regional Lead", "Subject Matter Expert"]
        return f"{unit_name} {suffixes[index % len(suffixes)]}"

    def _seed_enterprise_functions(self, pod: str, names: Iterable[str], locations: Iterable[tuple[str, str]]) -> None:
        for function_index, (function_name, lead_name, lead_title) in enumerate(ENTERPRISE_FUNCTIONS):
            function_id = f"{slug(pod)}-enterprise-{slug(function_name)}"
            lead = self._seed_person(
                stakeholder_id=f"{function_id}-lead",
                name=lead_name,
                title=lead_title,
                pod=pod,
                division="Enterprise Functions",
                unit=function_name,
                team_type="Business",
                role="Enterprise Function Lead",
                level="Managing Director" if function_index != 1 else "Executive Director",
                manager_id=self.pod_heads[pod],
                location=next(locations),
                relationship="Strong",
                buyer=function_index != 1,
                budget_holder=function_index == 0,
                tags=[function_name, "Enterprise", "Transformation"],
            )
            member_ids = []
            for member_index in range(3 + function_index % 2):
                member = self._seed_person(
                    stakeholder_id=f"{function_id}-member-{member_index + 1}",
                    name=next(names),
                    title=["Business Partner", "Transformation Lead", "Program Director", "Senior Counsel"][member_index],
                    pod=pod,
                    division="Enterprise Functions",
                    unit=function_name,
                    team_type="Business",
                    role="Enterprise Stakeholder",
                    level=LEVELS[(member_index + 1) % len(LEVELS)],
                    manager_id=lead.id,
                    location=next(locations),
                    relationship=RELATIONSHIP_STRENGTHS[(member_index + function_index) % 3],
                    tags=[function_name, "Enterprise"],
                )
                member_ids.append(member.id)
            self.enterprise[pod].append({"id": function_id, "name": function_name, "lead_stakeholder_id": lead.id, "member_ids": member_ids})

    def _seed_activity(self) -> None:
        now = self.now()
        prioritized = [
            s for s in self.stakeholders.values()
            if s.organizational_role != "Pod Head" and (s.is_primary_technology or s.is_buyer)
        ]
        meeting_subjects = [
            "Platform modernization roadmap", "AI-enabled workflow discovery", "Data quality and controls review",
            "Cloud migration planning", "Operating model alignment", "Quarterly relationship review",
        ]
        outcomes = ["Executive sponsorship confirmed", "Technical workshop requested", "Business case refinement required", "Follow-up with procurement", "Pilot scope agreed"]
        for index, stakeholder in enumerate(prioritized[:90]):
            for meeting_index in range(1 + index % 3):
                meeting_date = now - timedelta(days=12 + meeting_index * 38 + index % 17)
                meeting = Meeting(
                    id=f"meeting-{index + 1}-{meeting_index + 1}",
                    subject=meeting_subjects[(index + meeting_index) % len(meeting_subjects)],
                    meeting_date=meeting_date,
                    summary=f"Discussed {stakeholder.business_unit.lower()} priorities, delivery constraints, and the next decision point with {stakeholder.name}.",
                    stakeholder_ids=[stakeholder.id],
                    organizer=stakeholder.capco_owner or "Capco Account Team",
                    outcome=outcomes[(index + meeting_index) % len(outcomes)],
                    next_steps=["Share capability materials", "Confirm working-session attendees"] if meeting_index == 0 else ["Update account plan"],
                    created_at=meeting_date,
                )
                self.meetings[meeting.id] = meeting

            note = Note(
                id=f"note-{index + 1}",
                stakeholder_id=stakeholder.id,
                body=f"{stakeholder.name} is {stakeholder.relationship_strength.lower()}ly engaged. Current interests include {', '.join(stakeholder.tags[:3])}. Validate decision timing before the next steering discussion.",
                category="Relationship",
                author=stakeholder.capco_owner or "Capco Account Team",
                created_at=now - timedelta(days=8 + index % 30),
                updated_at=now - timedelta(days=8 + index % 30),
            )
            self.notes[note.id] = note

        opportunity_stages = ["Discovery", "Qualification", "Proposal", "Negotiation"]
        opportunity_names = ["AI-enabled trading workflow", "Data governance modernization", "Cloud platform transformation", "Client onboarding redesign", "Risk analytics acceleration", "Operations automation program"]
        for index, stakeholder in enumerate(prioritized[:45]):
            if index % 2:
                continue
            opportunity = Opportunity(
                id=f"opportunity-{index + 1}",
                name=f"{stakeholder.business_unit}: {opportunity_names[index % len(opportunity_names)]}",
                description=f"Potential engagement aligned to {stakeholder.name}'s priorities across {', '.join(stakeholder.tags[:2])}.",
                estimated_value=450_000 + (index % 8) * 275_000,
                probability=25 + (index % 6) * 10,
                stage=opportunity_stages[index % len(opportunity_stages)],
                stakeholder_ids=[stakeholder.id],
                owner=stakeholder.capco_owner or "Capco Account Team",
                target_close_date=(now + timedelta(days=60 + index * 3)).date(),
                created_at=now - timedelta(days=45 + index),
                updated_at=now - timedelta(days=index % 12),
            )
            self.opportunities[opportunity.id] = opportunity

    def _refresh_derived_fields(self) -> None:
        meetings_by_stakeholder: dict[str, list[Meeting]] = defaultdict(list)
        for meeting in self.meetings.values():
            for stakeholder_id in meeting.stakeholder_ids:
                meetings_by_stakeholder[stakeholder_id].append(meeting)
        opportunities_by_stakeholder: dict[str, int] = defaultdict(int)
        for opportunity in self.opportunities.values():
            if opportunity.stage != "Closed Lost":
                for stakeholder_id in opportunity.stakeholder_ids:
                    opportunities_by_stakeholder[stakeholder_id] += 1
        today = self.now().date()
        for stakeholder in self.stakeholders.values():
            meetings = sorted(meetings_by_stakeholder[stakeholder.id], key=lambda item: item.meeting_date)
            past = [meeting for meeting in meetings if meeting.meeting_date.date() <= today]
            future = [meeting for meeting in meetings if meeting.meeting_date.date() > today]
            if past:
                stakeholder.last_meeting = past[-1].meeting_date.date()
            if future:
                stakeholder.next_meeting = future[0].meeting_date.date()
            stakeholder.opportunity_count = opportunities_by_stakeholder[stakeholder.id]

    def _seed_documents(self) -> None:
        now = self.now()
        priority_people = [
            item
            for pod in POD_STRUCTURE
            for item in [value for value in self.stakeholders.values() if value.pod == pod and (value.is_buyer or value.is_primary_technology)][:12]
        ]
        documented_stakeholders = {item.stakeholder_id for item in self.documents.values()}
        document_types = ["Account Plan", "Meeting Brief", "Proposal", "Research", "Delivery", "Contract"]
        titles = [
            "Executive account plan", "Latest meeting brief", "Transformation proposal",
            "Stakeholder research summary", "Delivery recovery plan", "Commercial assumptions",
        ]
        for index, stakeholder in enumerate(priority_people):
            if stakeholder.id in documented_stakeholders:
                continue
            document = DocumentLink(
                id=f"document-seed-{stakeholder.id}",
                stakeholder_id=stakeholder.id,
                title=f"{stakeholder.business_unit} — {titles[index % len(titles)]}",
                url=f"https://sharepoint.example.com/sites/ms-account/{stakeholder.id}/{index + 1}",
                document_type=document_types[index % len(document_types)],
                description=f"Working account material linked to {stakeholder.name} and the {stakeholder.business_unit} relationship plan.",
                owner=stakeholder.capco_owner or "Capco Account Team",
                tags=list(stakeholder.tags),
                created_at=now - timedelta(days=30 - index % 20),
                updated_at=now - timedelta(days=index % 12),
            )
            self.documents[document.id] = document

    def _validate_org(self, pod: str, division: str, business_unit: str) -> str:
        structure = self.organization_structure()
        if pod not in structure:
            raise NotFoundError(f"Unknown pod: {pod}")
        if division not in structure[pod]:
            raise NotFoundError(f"Unknown division '{division}' for {pod}")
        if business_unit not in structure[pod][division]:
            raise NotFoundError(f"Unknown business unit '{business_unit}' for {division}")
        unit = next((item for item in self.units.values() if item["pod"] == pod and item["division"] == division and item["name"] == business_unit), None)
        if not unit:
            raise NotFoundError(f"Business unit '{business_unit}' is not loaded")
        return unit["id"]

    def get_stakeholder(self, stakeholder_id: str) -> Stakeholder:
        try:
            return self.stakeholders[stakeholder_id]
        except KeyError as error:
            raise NotFoundError("Stakeholder not found") from error

    def list_stakeholders(
        self, *, pod: Optional[str] = None, search: Optional[str] = None, division: Optional[str] = None,
        business_unit: Optional[str] = None, team_type: Optional[str] = None, location: Optional[str] = None,
        level: Optional[str] = None, role: Optional[str] = None, budget_holder: Optional[bool] = None,
        relationship_strength: Optional[str] = None, capco_owner: Optional[str] = None,
        meeting_recency: Optional[str] = None, has_opportunities: Optional[bool] = None,
        tag: Optional[str] = None,
    ) -> list[Stakeholder]:
        records = list(self.stakeholders.values())
        if pod:
            records = [item for item in records if item.pod == pod]
        if division and division != "All":
            records = [item for item in records if item.division == division]
        if business_unit and business_unit != "All":
            records = [item for item in records if item.business_unit == business_unit]
        if team_type and team_type != "All":
            records = [item for item in records if item.team_type == team_type]
        if location and location != "All":
            records = [item for item in records if item.location == location]
        if level and level != "All":
            records = [item for item in records if item.level == level]
        if role == "Buyer":
            records = [item for item in records if item.is_buyer]
        elif role == "Influencer":
            records = [item for item in records if item.is_influencer]
        if budget_holder is not None:
            records = [item for item in records if item.is_budget_holder is budget_holder]
        if relationship_strength and relationship_strength != "All":
            records = [item for item in records if item.relationship_strength == relationship_strength]
        if capco_owner and capco_owner != "All":
            records = [item for item in records if item.capco_owner == capco_owner]
        if has_opportunities is not None:
            records = [item for item in records if (item.opportunity_count > 0) is has_opportunities]
        if tag and tag != "All":
            records = [item for item in records if tag.lower() in {value.lower() for value in item.tags}]
        if meeting_recency and meeting_recency != "All":
            today = self.now().date()
            days = {"Last 30 days": 30, "Last 90 days": 90}.get(meeting_recency)
            if days:
                records = [item for item in records if item.last_meeting and (today - item.last_meeting).days <= days]
            elif meeting_recency == "No recent meeting":
                records = [item for item in records if not item.last_meeting or (today - item.last_meeting).days > 90]
        if search:
            needle = search.casefold()
            records = [
                item for item in records
                if needle in " ".join(filter(None, [item.name, item.title, item.division, item.business_unit, " ".join(item.tags)])).casefold()
            ]
        return sorted(records, key=lambda item: (item.pod, item.division or "", item.business_unit or "", item.name))

    def build_map(self, pod: str, **filters) -> MapResponse:
        structure = self.organization_structure()
        if pod not in structure:
            raise NotFoundError("Pod not found")
        selected = self.list_stakeholders(pod=pod, **filters)
        selected_ids = {item.id for item in selected}
        has_filters = any(value not in (None, "", "All") for value in filters.values())
        divisions = []
        for division in sorted((item for item in self.divisions.values() if item["pod"] == pod), key=lambda item: list(structure[pod]).index(item["name"])):
            units = []
            for unit_id in division["unit_ids"]:
                unit = self.units[unit_id]
                business_ids = [item for item in unit["business_stakeholder_ids"] if not has_filters or item in selected_ids]
                primary_id = unit["primary_technology_id"]
                primary_visible = not has_filters or primary_id in selected_ids
                if has_filters and not business_ids and not primary_visible:
                    continue
                units.append({
                    "id": unit["id"],
                    "name": unit["name"],
                    "sort_order": unit["sort_order"],
                    "business_stakeholder_ids": business_ids,
                    "primary_technology_id": primary_id if primary_visible else None,
                    "technology_team_size": max(0, len(unit["technology_stakeholder_ids"]) - 1),
                    "reporting_unknown_ids": [item for item in unit["reporting_unknown_ids"] if not has_filters or item in selected_ids],
                })
            if units or not has_filters:
                divisions.append({
                    "id": division["id"], "name": division["name"], "color": division["color"],
                    "head_stakeholder_id": division["head_stakeholder_id"], "units": units,
                })
        reporting_lines = [
            ReportingLine(manager_id=item.manager_id, report_id=item.id)
            for item in selected if item.manager_id and item.manager_id in selected_ids
        ]
        enterprise = []
        for group in self.enterprise[pod]:
            member_ids = [item for item in group["member_ids"] if not has_filters or item in selected_ids]
            lead_visible = not has_filters or group["lead_stakeholder_id"] in selected_ids
            if lead_visible or member_ids:
                enterprise.append({**group, "lead_stakeholder_id": group["lead_stakeholder_id"] if lead_visible else None, "member_ids": member_ids})
        return MapResponse(
            pod=pod,
            generated_at=self.now(),
            pod_head_stakeholder_id=self.pod_heads.get(pod),
            divisions=divisions,
            stakeholders=selected,
            reporting_lines=reporting_lines,
            enterprise_functions=enterprise,
            filters_applied=filters,
        )

    def _unit_for_stakeholder(self, stakeholder_id: str) -> Optional[dict]:
        return next((unit for unit in self.units.values() if stakeholder_id in unit["business_stakeholder_ids"] or stakeholder_id in unit["technology_stakeholder_ids"]), None)

    def _business_head_id(self, unit: dict) -> Optional[str]:
        return next((stakeholder_id for stakeholder_id in unit["business_stakeholder_ids"] if self.stakeholders[stakeholder_id].organizational_role == "Business Unit Head"), unit["business_stakeholder_ids"][0] if unit["business_stakeholder_ids"] else None)

    def _enterprise_lead_id(self, person: Stakeholder) -> Optional[str]:
        group = next((group for group in self.enterprise.get(person.pod, []) if person.id == group["lead_stakeholder_id"] or person.id in group["member_ids"]), None)
        return group["lead_stakeholder_id"] if group else None

    def _required_structural_manager(self, person: Stakeholder) -> Optional[str]:
        if person.organizational_role == "Pod Head":
            return None
        if person.organizational_role == "Division Head":
            return self.pod_heads.get(person.pod)
        if person.organizational_role == "Enterprise Function Lead":
            return self.pod_heads.get(person.pod)
        if person.division == "Enterprise Functions":
            return self._enterprise_lead_id(person)
        unit = self._unit_for_stakeholder(person.id)
        if not unit:
            return None
        business_head_id = self._business_head_id(unit)
        if person.organizational_role == "Business Unit Head" or person.is_primary_technology:
            return next((division["head_stakeholder_id"] for division in self.divisions.values() if division["pod"] == person.pod and division["name"] == person.division), None) if person.organizational_role == "Business Unit Head" else business_head_id
        if person.team_type == "Technology":
            return unit["primary_technology_id"] or business_head_id
        return None

    def create_stakeholder(self, payload: StakeholderCreate) -> Stakeholder:
        with self._lock:
            unit_id = self._validate_org(payload.pod, payload.division, payload.business_unit)
            if payload.is_primary_technology and payload.team_type != "Technology":
                raise ConflictError("Primary technology stakeholder must be on the Technology team")
            role = payload.organizational_role or f"{payload.team_type} Stakeholder"
            unit = self.units[unit_id]
            manager_id = payload.manager_id
            if not manager_id:
                if role == "Business Unit Head":
                    manager_id = next(division["head_stakeholder_id"] for division in self.divisions.values() if division["pod"] == payload.pod and division["name"] == payload.division)
                elif payload.team_type == "Technology":
                    manager_id = self._business_head_id(unit) if payload.is_primary_technology else unit["primary_technology_id"] or self._business_head_id(unit)
                else:
                    manager_id = self._business_head_id(unit)
            if not manager_id:
                raise ConflictError("Every stakeholder must have a manager")
            manager = self.get_stakeholder(manager_id)
            if manager.pod != payload.pod:
                raise ConflictError("Manager must belong to the same pod")
            stakeholder_id = f"stakeholder-{uuid4().hex[:12]}"
            now = self.now()
            record = Stakeholder(
                id=stakeholder_id,
                assignment_id=f"assignment-{uuid4().hex[:12]}",
                name=payload.name,
                title=payload.title,
                pod=payload.pod,
                division=payload.division,
                business_unit=payload.business_unit,
                team_type=payload.team_type,
                organizational_role=role,
                level=payload.level,
                location=payload.location,
                country_code=payload.country_code,
                manager_id=manager_id,
                is_primary_technology=False,
                is_buyer=payload.is_buyer,
                is_influencer=payload.is_influencer,
                is_budget_holder=payload.is_budget_holder,
                relationship_strength=payload.relationship_strength,
                capco_contingents=0,
                capco_owner=payload.capco_owner,
                budget_amount=payload.budget_amount,
                biography=payload.biography,
                tags=list(dict.fromkeys(payload.tags)),
                created_at=now,
                updated_at=now,
            )
            self.stakeholders[record.id] = record
            target = self.units[unit_id]
            key = "technology_stakeholder_ids" if record.team_type == "Technology" else "business_stakeholder_ids"
            target[key].append(record.id)
            self._add_history(record.id, "Created", None, record.assignment_id, "Stakeholder created")
            if payload.is_primary_technology:
                self.set_primary_technology(unit_id, record.id, "Selected during stakeholder creation")
            return record

    def update_stakeholder(self, stakeholder_id: str, payload: StakeholderUpdate) -> Stakeholder:
        with self._lock:
            record = self.get_stakeholder(stakeholder_id)
            changes = payload.model_dump(exclude_unset=True)
            if "country_code" in changes and changes["country_code"]:
                changes["country_code"] = changes["country_code"].upper()
            for field, value in changes.items():
                setattr(record, field, value)
            record.updated_at = self.now()
            return record

    def delete_stakeholder(self, stakeholder_id: str) -> None:
        with self._lock:
            record = self.get_stakeholder(stakeholder_id)
            if stakeholder_id in self.pod_heads.values() or any(division["head_stakeholder_id"] == stakeholder_id for division in self.divisions.values()):
                raise ConflictError("Assign a replacement organization head before deletion")
            if any(unit["primary_technology_id"] == stakeholder_id for unit in self.units.values()):
                raise ConflictError("Assign a replacement primary technology stakeholder before deletion")
            if any(stakeholder.manager_id == stakeholder_id for stakeholder in self.stakeholders.values()):
                raise ConflictError("Reassign direct reports before deleting this stakeholder")
            for unit in self.units.values():
                for key in ("business_stakeholder_ids", "technology_stakeholder_ids", "reporting_unknown_ids"):
                    unit[key] = [item for item in unit[key] if item != stakeholder_id]
            self.meetings = {key: value for key, value in self.meetings.items() if stakeholder_id not in value.stakeholder_ids}
            self.notes = {key: value for key, value in self.notes.items() if value.stakeholder_id != stakeholder_id}
            self.documents = {key: value for key, value in self.documents.items() if value.stakeholder_id != stakeholder_id}
            for opportunity in self.opportunities.values():
                opportunity.stakeholder_ids = [item for item in opportunity.stakeholder_ids if item != stakeholder_id]
            del self.stakeholders[stakeholder_id]
            self._refresh_derived_fields()

    def get_team(self, stakeholder_id: str) -> dict:
        stakeholder = self.get_stakeholder(stakeholder_id)
        manager = self.stakeholders.get(stakeholder.manager_id) if stakeholder.manager_id else None
        reports = sorted((item for item in self.stakeholders.values() if item.manager_id == stakeholder_id), key=lambda item: item.name)
        return {
            "stakeholder": stakeholder,
            "manager": manager,
            "direct_reports": reports,
            "reporting_line_known": stakeholder.manager_id is not None,
            "is_primary_technology": stakeholder.is_primary_technology,
            "hidden_on_primary_map": stakeholder.team_type == "Technology" and not stakeholder.is_primary_technology,
        }

    def update_reporting_line(self, report_id: str, manager_id: Optional[str], reason: str) -> dict:
        with self._lock:
            report = self.get_stakeholder(report_id)
            previous = report.manager_id
            required_manager = self._required_structural_manager(report)
            if report.organizational_role == "Pod Head":
                if manager_id is not None:
                    raise ConflictError("A pod head cannot have a manager")
            elif manager_id is None:
                raise ConflictError("Every stakeholder except the pod head must have a manager")
            elif required_manager and manager_id != required_manager:
                raise ConflictError("This leadership role has a governed reporting line")
            if manager_id:
                manager = self.get_stakeholder(manager_id)
                if manager.id == report.id:
                    raise ConflictError("A stakeholder cannot manage themselves")
                if manager.pod != report.pod:
                    raise ConflictError("Reporting lines must remain within the same pod")
                cursor_id: Optional[str] = manager.id
                visited: set[str] = set()
                while cursor_id:
                    if cursor_id == report.id or cursor_id in visited:
                        raise ConflictError("Reporting line would create a cycle")
                    visited.add(cursor_id)
                    cursor_id = self.get_stakeholder(cursor_id).manager_id
            report.manager_id = manager_id
            report.updated_at = self.now()
            unit = next((item for item in self.units.values() if report.id in item["business_stakeholder_ids"]), None)
            if unit:
                unit["reporting_unknown_ids"] = [item for item in unit["reporting_unknown_ids"] if item != report.id]
            history = self._add_history(report.id, "Reporting Line", previous, manager_id, reason)
            return {"report_id": report.id, "previous_manager_id": previous, "manager_id": manager_id, "history_id": history.id, "status": "saved"}

    def set_primary_technology(self, unit_id: str, stakeholder_id: str, reason: str) -> dict:
        with self._lock:
            if unit_id not in self.units:
                raise NotFoundError("Business unit not found")
            unit = self.units[unit_id]
            stakeholder = self.get_stakeholder(stakeholder_id)
            if stakeholder_id not in unit["technology_stakeholder_ids"] or stakeholder.team_type != "Technology":
                raise ConflictError("Primary technology stakeholder must belong to this unit's Technology team")
            previous = unit["primary_technology_id"]
            if previous == stakeholder_id:
                return {"business_unit_id": unit_id, "previous_stakeholder_id": previous, "stakeholder_id": stakeholder_id, "status": "unchanged"}
            if previous in self.stakeholders:
                self.stakeholders[previous].is_primary_technology = False
                self.stakeholders[previous].manager_id = stakeholder_id
                self.stakeholders[previous].updated_at = self.now()
            stakeholder.is_primary_technology = True
            stakeholder.manager_id = self._business_head_id(unit)
            stakeholder.updated_at = self.now()
            for report in self.stakeholders.values():
                if report.id in unit["technology_stakeholder_ids"] and report.id != stakeholder_id and report.manager_id == previous:
                    report.manager_id = stakeholder_id
                    report.updated_at = self.now()
            unit["primary_technology_id"] = stakeholder_id
            history = self._add_history(stakeholder_id, "Primary Technology", previous, stakeholder_id, reason)
            return {"business_unit_id": unit_id, "previous_stakeholder_id": previous, "stakeholder_id": stakeholder_id, "history_id": history.id, "status": "saved"}

    def set_pod_head(self, pod: str, stakeholder_id: str, reason: str) -> dict:
        with self._lock:
            if pod not in self.pod_names():
                raise NotFoundError("Pod not found")
            stakeholder = self.get_stakeholder(stakeholder_id)
            if stakeholder.pod != pod:
                raise ConflictError("Pod head must belong to the same pod")
            previous = self.pod_heads.get(pod)
            if previous == stakeholder_id:
                return {
                    "pod": pod, "previous_stakeholder_id": previous,
                    "stakeholder_id": stakeholder_id, "head_stakeholder_id": stakeholder_id,
                    "status": "unchanged",
                }
            if previous in self.stakeholders:
                previous_head = self.stakeholders[previous]
                target_unit = self._unit_for_stakeholder(stakeholder_id)
                governed_roles = {"Pod Head", "Division Head", "Business Unit Head", "Enterprise Function Lead"}
                if stakeholder.organizational_role != "Pod Head" and (
                    stakeholder.team_type != "Business" or stakeholder.is_primary_technology
                    or stakeholder.organizational_role in governed_roles or target_unit is None
                    or any(item.manager_id == stakeholder_id for item in self.stakeholders.values())
                ):
                    raise ConflictError("Select an ungoverned business stakeholder without direct reports as the new pod head")
                previous_scope = {
                    "division": stakeholder.division,
                    "business_unit": stakeholder.business_unit,
                    "team_type": stakeholder.team_type,
                    "organizational_role": stakeholder.organizational_role,
                    "manager_id": stakeholder.manager_id,
                }
                if target_unit:
                    target_unit["business_stakeholder_ids"] = [
                        previous if item == stakeholder_id else item
                        for item in target_unit["business_stakeholder_ids"]
                    ]
                previous_head.division = previous_scope["division"]
                previous_head.business_unit = previous_scope["business_unit"]
                previous_head.team_type = previous_scope["team_type"]
                previous_head.organizational_role = previous_scope["organizational_role"]
                previous_head.manager_id = previous_scope["manager_id"]
                previous_head.updated_at = self.now()
            stakeholder.division = None
            stakeholder.business_unit = None
            stakeholder.team_type = "Business"
            stakeholder.organizational_role = "Pod Head"
            stakeholder.level = "Executive Leadership"
            stakeholder.manager_id = None
            stakeholder.updated_at = self.now()
            self.pod_heads[pod] = stakeholder_id
            for division in self.divisions.values():
                if division["pod"] == pod and division["head_stakeholder_id"] in self.stakeholders:
                    self.stakeholders[division["head_stakeholder_id"]].manager_id = stakeholder_id
            history = self._add_history(stakeholder_id, "Assignment", previous, stakeholder_id, reason)
            return {
                "pod": pod, "previous_stakeholder_id": previous, "stakeholder_id": stakeholder_id,
                "head_stakeholder_id": stakeholder_id, "history_id": history.id, "status": "saved",
            }

    def _add_history(self, stakeholder_id: str, change_type: str, previous: Optional[str], new: Optional[str], reason: str) -> AssignmentHistory:
        history = AssignmentHistory(
            id=f"history-{uuid4().hex[:12]}", stakeholder_id=stakeholder_id, change_type=change_type,
            previous_value=previous, new_value=new, reason=reason, effective_at=self.now(),
        )
        self.history.append(history)
        return history

    def list_history(self, stakeholder_id: Optional[str] = None) -> list[AssignmentHistory]:
        records = self.history
        if stakeholder_id:
            self.get_stakeholder(stakeholder_id)
            records = [item for item in records if item.stakeholder_id == stakeholder_id]
        return sorted(records, key=lambda item: item.effective_at, reverse=True)

    def list_meetings(self, stakeholder_id: Optional[str] = None, upcoming: Optional[bool] = None) -> list[Meeting]:
        records = list(self.meetings.values())
        if stakeholder_id:
            self.get_stakeholder(stakeholder_id)
            records = [item for item in records if stakeholder_id in item.stakeholder_ids]
        now = self.now()
        if upcoming is True:
            records = [item for item in records if item.meeting_date > now]
        elif upcoming is False:
            records = [item for item in records if item.meeting_date <= now]
        return sorted(records, key=lambda item: item.meeting_date, reverse=upcoming is not True)

    def get_meeting(self, meeting_id: str) -> Meeting:
        try:
            return self.meetings[meeting_id]
        except KeyError as error:
            raise NotFoundError("Meeting not found") from error

    def create_meeting(self, payload: MeetingCreate) -> Meeting:
        with self._lock:
            for stakeholder_id in payload.stakeholder_ids:
                self.get_stakeholder(stakeholder_id)
            meeting = Meeting(id=f"meeting-{uuid4().hex[:12]}", created_at=self.now(), **payload.model_dump())
            self.meetings[meeting.id] = meeting
            self._refresh_derived_fields()
            return meeting

    def update_meeting(self, meeting_id: str, payload: MeetingUpdate) -> Meeting:
        with self._lock:
            if meeting_id not in self.meetings:
                raise NotFoundError("Meeting not found")
            changes = payload.model_dump(exclude_unset=True)
            if "stakeholder_ids" in changes:
                for stakeholder_id in changes["stakeholder_ids"]:
                    self.get_stakeholder(stakeholder_id)
            meeting = self.meetings[meeting_id]
            for field, value in changes.items():
                setattr(meeting, field, value)
            self._refresh_derived_fields()
            return meeting

    def list_notes(self, stakeholder_id: str) -> list[Note]:
        self.get_stakeholder(stakeholder_id)
        return sorted((item for item in self.notes.values() if item.stakeholder_id == stakeholder_id), key=lambda item: item.created_at, reverse=True)

    def create_note(self, stakeholder_id: str, payload: NoteCreate) -> Note:
        with self._lock:
            self.get_stakeholder(stakeholder_id)
            now = self.now()
            note = Note(id=f"note-{uuid4().hex[:12]}", stakeholder_id=stakeholder_id, created_at=now, updated_at=now, **payload.model_dump())
            self.notes[note.id] = note
            return note

    def update_note(self, note_id: str, payload: NoteUpdate) -> Note:
        with self._lock:
            if note_id not in self.notes:
                raise NotFoundError("Note not found")
            note = self.notes[note_id]
            for field, value in payload.model_dump(exclude_unset=True).items():
                setattr(note, field, value)
            note.updated_at = self.now()
            return note

    def delete_note(self, note_id: str) -> None:
        with self._lock:
            if note_id not in self.notes:
                raise NotFoundError("Note not found")
            del self.notes[note_id]

    def list_documents(self, stakeholder_id: str) -> list[DocumentLink]:
        self.get_stakeholder(stakeholder_id)
        return sorted(
            (item for item in self.documents.values() if item.stakeholder_id == stakeholder_id),
            key=lambda item: item.updated_at,
            reverse=True,
        )

    def list_meeting_documents(self, meeting_id: str) -> list[DocumentLink]:
        return sorted(
            (item for item in self.documents.values() if item.meeting_id == meeting_id),
            key=lambda item: item.updated_at,
            reverse=True,
        )

    def get_document(self, document_id: str) -> DocumentLink:
        if document_id not in self.documents:
            raise NotFoundError("Document not found")
        return self.documents[document_id]

    def _create_document(self, payload: DocumentLinkCreate, *, stakeholder_id: str | None = None, meeting_id: str | None = None) -> DocumentLink:
        now = self.now()
        document_id = f"document-{uuid4().hex[:12]}"
        values = payload.model_dump()
        if not values["tags"]:
            if stakeholder_id in self.stakeholders:
                values["tags"] = list(self.stakeholders[stakeholder_id].tags)
            elif meeting_id in self.meetings:
                values["tags"] = list(self.meetings[meeting_id].tags)
        document = DocumentLink(
            id=document_id,
            stakeholder_id=stakeholder_id,
            meeting_id=meeting_id,
            download_url=f"/api/documents/{document_id}/download" if payload.stored_name else None,
            created_at=now,
            updated_at=now,
            **values,
        )
        self.documents[document.id] = document
        return document

    def create_document(self, stakeholder_id: str, payload: DocumentLinkCreate) -> DocumentLink:
        with self._lock:
            self.get_stakeholder(stakeholder_id)
            return self._create_document(payload, stakeholder_id=stakeholder_id)

    def create_meeting_document(self, meeting_id: str, payload: DocumentLinkCreate) -> DocumentLink:
        with self._lock:
            return self._create_document(payload, meeting_id=meeting_id)

    def update_document(self, document_id: str, payload: DocumentLinkUpdate) -> DocumentLink:
        with self._lock:
            if document_id not in self.documents:
                raise NotFoundError("Document link not found")
            document = self.documents[document_id]
            for field, value in payload.model_dump(exclude_unset=True).items():
                setattr(document, field, value)
            document.updated_at = self.now()
            return document

    def delete_document(self, document_id: str) -> None:
        with self._lock:
            if document_id not in self.documents:
                raise NotFoundError("Document link not found")
            del self.documents[document_id]

    def list_opportunities(self, stakeholder_id: Optional[str] = None, stage: Optional[str] = None) -> list[Opportunity]:
        records = list(self.opportunities.values())
        if stakeholder_id:
            self.get_stakeholder(stakeholder_id)
            records = [item for item in records if stakeholder_id in item.stakeholder_ids]
        if stage and stage != "All":
            records = [item for item in records if item.stage == stage]
        return sorted(records, key=lambda item: (item.probability, item.estimated_value), reverse=True)

    def get_opportunity(self, opportunity_id: str) -> Opportunity:
        try:
            return self.opportunities[opportunity_id]
        except KeyError as error:
            raise NotFoundError("Opportunity not found") from error

    def create_opportunity(self, payload: OpportunityCreate) -> Opportunity:
        with self._lock:
            for stakeholder_id in payload.stakeholder_ids:
                self.get_stakeholder(stakeholder_id)
            now = self.now()
            record = Opportunity(id=f"opportunity-{uuid4().hex[:12]}", created_at=now, updated_at=now, **payload.model_dump())
            self.opportunities[record.id] = record
            self._refresh_derived_fields()
            return record

    def update_opportunity(self, opportunity_id: str, payload: OpportunityUpdate) -> Opportunity:
        with self._lock:
            if opportunity_id not in self.opportunities:
                raise NotFoundError("Opportunity not found")
            record = self.opportunities[opportunity_id]
            changes = payload.model_dump(exclude_unset=True)
            if "stakeholder_ids" in changes:
                for stakeholder_id in changes["stakeholder_ids"]:
                    self.get_stakeholder(stakeholder_id)
            for field, value in changes.items():
                setattr(record, field, value)
            record.updated_at = self.now()
            self._refresh_derived_fields()
            return record

    def coverage(self, pod: str) -> dict:
        if pod not in self.pod_names():
            raise NotFoundError("Pod not found")
        divisions = []
        for division in (item for item in self.divisions.values() if item["pod"] == pod):
            units = []
            for unit_id in division["unit_ids"]:
                unit = self.units[unit_id]
                records = [self.stakeholders[item] for item in unit["business_stakeholder_ids"] + unit["technology_stakeholder_ids"]]
                known = [item for item in records if item.relationship_strength != "Unknown"]
                strong = [item for item in records if item.relationship_strength == "Strong"]
                coverage_score = round((len(known) / max(1, len(records))) * 65 + (len(strong) / max(1, len(records))) * 35)
                rating = "Strong" if coverage_score >= 75 else "Medium" if coverage_score >= 50 else "Developing"
                units.append({
                    "id": unit_id, "name": unit["name"], "known_stakeholders": len(known),
                    "total_stakeholders": len(records), "coverage_score": coverage_score, "coverage": rating,
                    "buyers": sum(item.is_buyer for item in records),
                    "budget_holders": sum(item.is_budget_holder for item in records),
                    "open_opportunities": sum(item.opportunity_count for item in records),
                })
            divisions.append({"id": division["id"], "name": division["name"], "business_units": units})
        return {"pod": pod, "generated_at": self.now(), "divisions": divisions}

    def filter_options(self, pod: str) -> dict:
        structure = self.organization_structure()
        if pod not in structure:
            raise NotFoundError("Pod not found")
        records = self.list_stakeholders(pod=pod)
        return {
            "divisions": list(structure[pod]),
            "business_units": sorted({
                item.business_unit
                for item in records
                if item.business_unit and item.business_unit != "Division Leadership"
            }),
            "team_types": ["Business", "Technology"],
            "locations": sorted({item.location for item in records}),
            "levels": sorted({item.level for item in records}),
            "relationship_strengths": RELATIONSHIP_STRENGTHS,
            "capco_owners": sorted({item.capco_owner for item in records if item.capco_owner}),
            "tags": sorted({tag for item in records for tag in item.tags}),
        }
