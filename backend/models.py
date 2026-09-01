from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


TeamType = Literal["Business", "Technology"]
RelationshipStrength = Literal["Strong", "Medium", "Developing", "Unknown"]
OpportunityStage = Literal["Discovery", "Qualification", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]
RequirementPriority = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
RequirementStatus = Literal["DRAFT", "OPEN", "SOURCING", "PARTIALLY_FILLED", "ON_HOLD", "FILLED", "CANCELLED"]
CandidateType = Literal["EXTERNAL", "INTERNAL_CAPCO"]
CandidateStage = Literal["IDENTIFIED", "CAPCO_REVIEW", "SUBMITTED_TO_MS", "MS_REVIEW", "INTERVIEW_SCHEDULED", "INTERVIEWING", "OFFER", "SELECTED", "REJECTED", "WITHDRAWN"]
InterviewStatus = Literal["SCHEDULED", "COMPLETED", "CANCELLED"]
OfferStatus = Literal["OFFER_PENDING", "RATE_NEGOTIATION", "OFFER_ACCEPTED", "OFFER_DECLINED"]
OnboardingStatus = Literal["NOT_STARTED", "IN_PROGRESS", "BLOCKED", "READY_TO_START", "COMPLETE"]
OnboardingStepStatus = Literal["NOT_STARTED", "IN_PROGRESS", "BLOCKED", "COMPLETE", "NOT_APPLICABLE"]
ResponsibleParty = Literal["CAPCO", "MORGAN_STANLEY"]


class EmployeeSummary(BaseModel):
    id: str
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    level: str
    role: str
    capability: Optional[str] = None
    location: str
    active: bool
    manager_employee_id: Optional[str] = None


class EmployeeProfile(EmployeeSummary):
    skills: list[str] = Field(default_factory=list)
    assignments: list[dict] = Field(default_factory=list)
    stakeholder_relationships: list[dict] = Field(default_factory=list)
    meetings: list[dict] = Field(default_factory=list)
    owned_opportunities: list[dict] = Field(default_factory=list)
    capacity: list[dict] = Field(default_factory=list)
    resourcing: list[dict] = Field(default_factory=list)


class Stakeholder(BaseModel):
    id: str
    assignment_id: str
    name: str
    title: str
    pod: str
    division: str
    business_unit: str
    team_type: TeamType
    organizational_role: str
    level: str = "Vice President"
    location: str = "New York, USA"
    country_code: str = "US"
    manager_id: Optional[str] = None
    is_primary_technology: bool = False
    is_buyer: bool = False
    is_influencer: bool = True
    is_budget_holder: bool = False
    relationship_strength: RelationshipStrength = "Developing"
    capco_contingents: int = Field(default=0, ge=0)
    capco_owner: Optional[str] = None
    capco_owner_employee_id: Optional[str] = None
    budget_amount: Optional[float] = Field(default=None, ge=0)
    biography: str = ""
    tags: list[str] = Field(default_factory=list)
    last_meeting: Optional[date] = None
    next_meeting: Optional[date] = None
    opportunity_count: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime


class StakeholderCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    title: str = Field(min_length=2, max_length=160)
    pod: str = "ISG"
    division: str = "Front Office"
    business_unit: str = "Equities"
    team_type: TeamType = "Business"
    organizational_role: Optional[str] = None
    level: str = "Vice President"
    location: str = "New York, USA"
    country_code: str = Field(default="US", min_length=2, max_length=2)
    manager_id: Optional[str] = None
    is_primary_technology: bool = False
    is_buyer: bool = False
    is_influencer: bool = True
    is_budget_holder: bool = False
    relationship_strength: RelationshipStrength = "Developing"
    capco_owner: Optional[str] = None
    capco_owner_employee_id: Optional[str] = None
    budget_amount: Optional[float] = Field(default=None, ge=0)
    biography: str = ""
    tags: list[str] = Field(default_factory=list)

    @field_validator("country_code")
    @classmethod
    def uppercase_country(cls, value: str) -> str:
        return value.upper()


class StakeholderUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=160)
    title: Optional[str] = Field(default=None, min_length=2, max_length=160)
    level: Optional[str] = None
    location: Optional[str] = None
    country_code: Optional[str] = Field(default=None, min_length=2, max_length=2)
    organizational_role: Optional[str] = None
    is_buyer: Optional[bool] = None
    is_influencer: Optional[bool] = None
    is_budget_holder: Optional[bool] = None
    relationship_strength: Optional[RelationshipStrength] = None
    capco_owner: Optional[str] = None
    capco_owner_employee_id: Optional[str] = None
    budget_amount: Optional[float] = Field(default=None, ge=0)
    biography: Optional[str] = None
    tags: Optional[list[str]] = None


class ReportingLineUpdate(BaseModel):
    report_id: str
    manager_id: Optional[str] = None
    reason: str = Field(default="Organization map update", max_length=240)


class PrimaryTechnologyUpdate(BaseModel):
    stakeholder_id: str
    reason: str = Field(default="Primary technology ownership update", max_length=240)


class Meeting(BaseModel):
    id: str
    subject: str
    meeting_date: datetime
    summary: str
    stakeholder_ids: list[str]
    organizer: str
    organizer_employee_id: Optional[str] = None
    capco_attendee_ids: list[str] = Field(default_factory=list)
    opportunity_ids: list[str] = Field(default_factory=list)
    outcome: str
    next_steps: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime


class MeetingCreate(BaseModel):
    subject: str = Field(min_length=2, max_length=200)
    meeting_date: datetime
    summary: str = Field(default="", max_length=4000)
    stakeholder_ids: list[str] = Field(min_length=1)
    organizer: str = Field(default="Capco Account Team", max_length=160)
    organizer_employee_id: Optional[str] = None
    capco_attendee_ids: list[str] = Field(default_factory=list)
    opportunity_ids: list[str] = Field(default_factory=list)
    outcome: str = Field(default="Follow-up required", max_length=240)
    next_steps: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class MeetingUpdate(BaseModel):
    subject: Optional[str] = Field(default=None, min_length=2, max_length=200)
    meeting_date: Optional[datetime] = None
    summary: Optional[str] = Field(default=None, max_length=4000)
    stakeholder_ids: Optional[list[str]] = Field(default=None, min_length=1)
    organizer: Optional[str] = Field(default=None, max_length=160)
    organizer_employee_id: Optional[str] = None
    capco_attendee_ids: Optional[list[str]] = None
    opportunity_ids: Optional[list[str]] = None
    outcome: Optional[str] = Field(default=None, max_length=240)
    next_steps: Optional[list[str]] = None
    tags: Optional[list[str]] = None


class PodMeetingCreate(MeetingCreate):
    duration_minutes: int = Field(default=60, ge=15, le=480)
    event_type: Literal["client", "internal", "workshop", "critical", "deadline"] = "client"
    opportunity_id: Optional[str] = None
    capco_attendees: list[str] = Field(default_factory=list)
    prep_required: bool = True


class PodMeetingUpdate(MeetingUpdate):
    duration_minutes: Optional[int] = Field(default=None, ge=15, le=480)
    event_type: Optional[Literal["client", "internal", "workshop", "critical", "deadline"]] = None
    opportunity_id: Optional[str] = None
    capco_attendees: Optional[list[str]] = None
    prep_required: Optional[bool] = None


class Note(BaseModel):
    id: str
    stakeholder_id: str
    body: str
    category: Literal["Relationship", "Opportunity", "Meeting", "General"] = "General"
    author: str
    author_employee_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class NoteCreate(BaseModel):
    body: str = Field(min_length=2, max_length=5000)
    category: Literal["Relationship", "Opportunity", "Meeting", "General"] = "General"
    author: str = Field(default="Current User", max_length=160)
    author_employee_id: Optional[str] = None


class NoteUpdate(BaseModel):
    body: Optional[str] = Field(default=None, min_length=2, max_length=5000)
    category: Optional[Literal["Relationship", "Opportunity", "Meeting", "General"]] = None


DocumentType = Literal["Proposal", "Meeting Brief", "Account Plan", "Contract", "Delivery", "Research", "Other"]


class DocumentLink(BaseModel):
    id: str
    stakeholder_id: Optional[str] = None
    meeting_id: Optional[str] = None
    title: str
    url: Optional[str] = None
    sharepoint_url: Optional[str] = None
    file_name: Optional[str] = None
    stored_name: Optional[str] = None
    content_type: Optional[str] = None
    file_size: Optional[int] = Field(default=None, ge=0)
    download_url: Optional[str] = None
    document_type: DocumentType = "Other"
    description: str = ""
    owner: str = "Capco Account Team"
    owner_employee_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DocumentLinkCreate(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    url: Optional[str] = Field(default=None, min_length=8, max_length=2000)
    sharepoint_url: Optional[str] = Field(default=None, min_length=8, max_length=2000)
    file_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    stored_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    content_type: Optional[str] = Field(default=None, max_length=255)
    file_size: Optional[int] = Field(default=None, ge=0)
    document_type: DocumentType = "Other"
    description: str = Field(default="", max_length=2000)
    owner: str = Field(default="Capco Account Team", max_length=160)
    owner_employee_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("url", "sharepoint_url")
    @classmethod
    def validate_document_url(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.lower().startswith(("https://", "http://")):
            raise ValueError("Document URL must start with http:// or https://")
        return value

    @model_validator(mode="after")
    def require_file_or_link(self):
        if not self.stored_name and not self.url and not self.sharepoint_url:
            raise ValueError("A local file or document URL is required")
        return self


class DocumentLinkUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=240)
    url: Optional[str] = Field(default=None, min_length=8, max_length=2000)
    sharepoint_url: Optional[str] = Field(default=None, min_length=8, max_length=2000)
    document_type: Optional[DocumentType] = None
    description: Optional[str] = Field(default=None, max_length=2000)
    owner: Optional[str] = Field(default=None, max_length=160)
    owner_employee_id: Optional[str] = None
    tags: Optional[list[str]] = None

    @field_validator("url", "sharepoint_url")
    @classmethod
    def validate_document_url(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.lower().startswith(("https://", "http://")):
            raise ValueError("Document URL must start with http:// or https://")
        return value


class AssistantContext(BaseModel):
    pod: Optional[str] = Field(default=None, max_length=120)
    section: Optional[str] = Field(default=None, max_length=120)
    entity_type: Optional[str] = Field(default=None, max_length=80)
    entity_id: Optional[str] = Field(default=None, max_length=180)


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=4000)
    conversation_id: Optional[str] = Field(default=None, max_length=180)
    context: AssistantContext = Field(default_factory=AssistantContext)


class AssistantCitation(BaseModel):
    id: str
    source_type: str
    source_id: str
    title: str
    excerpt: str
    pod: Optional[str] = None
    url: Optional[str] = None
    navigation: dict = Field(default_factory=dict)


class AssistantMessage(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    citations: list[AssistantCitation] = Field(default_factory=list)
    provider: Optional[str] = None
    created_at: datetime


class AssistantConversation(BaseModel):
    id: str
    title: str
    context_pod: Optional[str] = None
    context_section: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: list[AssistantMessage] = Field(default_factory=list)


class AssistantChatResponse(BaseModel):
    conversation_id: str
    message: AssistantMessage
    grounded: bool = True
    retrieval_count: int = Field(ge=0)


class CriticalItemCreate(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    description: str = Field(default="", max_length=4000)
    item_type: str = Field(default="ACCOUNT", min_length=2, max_length=100)
    severity: Literal["RED", "AMBER", "YELLOW"] = "AMBER"
    capco_owner: str = Field(min_length=2, max_length=160)
    capco_owner_employee_id: Optional[str] = None
    due_date: date
    stakeholder_id: str
    opportunity_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class Opportunity(BaseModel):
    id: str
    name: str
    description: str
    estimated_value: float = Field(ge=0)
    probability: int = Field(ge=0, le=100)
    stage: OpportunityStage
    stakeholder_ids: list[str]
    owner: str
    owner_employee_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    target_close_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime


class OpportunityCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=4000)
    estimated_value: float = Field(default=0, ge=0)
    probability: int = Field(default=20, ge=0, le=100)
    stage: OpportunityStage = "Discovery"
    stakeholder_ids: list[str] = Field(min_length=1)
    owner: str = Field(default="Capco Account Team", max_length=160)
    owner_employee_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    target_close_date: Optional[date] = None


class OpportunityUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = None
    estimated_value: Optional[float] = Field(default=None, ge=0)
    probability: Optional[int] = Field(default=None, ge=0, le=100)
    stage: Optional[OpportunityStage] = None
    stakeholder_ids: Optional[list[str]] = None
    owner: Optional[str] = None
    owner_employee_id: Optional[str] = None
    tags: Optional[list[str]] = None
    target_close_date: Optional[date] = None


class AssignmentHistory(BaseModel):
    id: str
    stakeholder_id: str
    change_type: Literal["Created", "Reporting Line", "Primary Technology", "Assignment"]
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    reason: str
    effective_at: datetime


class ReportingLine(BaseModel):
    manager_id: str
    report_id: str


class MapResponse(BaseModel):
    pod: str
    generated_at: datetime
    divisions: list[dict]
    stakeholders: list[Stakeholder]
    reporting_lines: list[ReportingLine]
    enterprise_functions: list[dict]
    filters_applied: dict[str, str | bool | None]


class DashboardTaskCreate(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    owner: str = Field(default="PS", max_length=80)
    owner_employee_id: Optional[str] = None
    due: date
    priority: Literal["Low", "Medium", "High"] = "Medium"
    stakeholder_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class DashboardTaskUpdate(BaseModel):
    status: Optional[Literal["Open", "In Progress", "Done"]] = None
    title: Optional[str] = Field(default=None, min_length=2, max_length=240)
    owner: Optional[str] = None
    owner_employee_id: Optional[str] = None
    due: Optional[date] = None
    priority: Optional[Literal["Low", "Medium", "High"]] = None
    tags: Optional[list[str]] = None


class PodFocusUpdate(BaseModel):
    focus: list[str] = Field(min_length=1, max_length=5)


class CriticalItemUpdate(BaseModel):
    status: Optional[Literal["Open", "Resolved"]] = None
    title: Optional[str] = Field(default=None, min_length=2, max_length=240)
    description: Optional[str] = Field(default=None, max_length=4000)
    item_type: Optional[str] = Field(default=None, min_length=2, max_length=100)
    severity: Optional[Literal["RED", "AMBER", "YELLOW"]] = None
    capco_owner: Optional[str] = Field(default=None, min_length=2, max_length=160)
    capco_owner_employee_id: Optional[str] = None
    due_date: Optional[date] = None
    stakeholder_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    tags: Optional[list[str]] = None


class ResourceRequirementCreate(BaseModel):
    pod_id: str
    division_id: str
    business_unit_id: str
    engagement_id: str
    title: str = Field(min_length=2, max_length=180)
    role: str = Field(min_length=2, max_length=120)
    description: str = ""
    requested_headcount: int = Field(ge=1, le=100)
    level: str
    location: str
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    target_start_date: date
    priority: RequirementPriority = "MEDIUM"
    status: RequirementStatus = "OPEN"
    request_owner_capco_employee_id: str
    client_stakeholder_id: str


class ResourceRequirementUpdate(BaseModel):
    expected_updated_at: Optional[datetime] = None
    title: Optional[str] = Field(default=None, min_length=2, max_length=180)
    role: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = None
    requested_headcount: Optional[int] = Field(default=None, ge=1, le=100)
    level: Optional[str] = None
    location: Optional[str] = None
    required_skills: Optional[list[str]] = None
    preferred_skills: Optional[list[str]] = None
    target_start_date: Optional[date] = None
    priority: Optional[RequirementPriority] = None
    status: Optional[RequirementStatus] = None
    request_owner_capco_employee_id: Optional[str] = None
    client_stakeholder_id: Optional[str] = None


class CandidateCreate(BaseModel):
    resource_requirement_id: str
    capco_employee_id: Optional[str] = None
    candidate_type: CandidateType = "EXTERNAL"
    first_name: str = Field(min_length=1, max_length=90)
    last_name: str = Field(min_length=1, max_length=90)
    email: Optional[str] = None
    level: str
    location: str
    skills: list[str] = Field(default_factory=list)
    stage: CandidateStage = "IDENTIFIED"
    capco_reviewer_id: str
    ms_reviewer_stakeholder_id: Optional[str] = None
    expected_start_date: Optional[date] = None
    match_score: Optional[int] = Field(default=None, ge=0, le=100)


class CandidateUpdate(BaseModel):
    expected_updated_at: Optional[datetime] = None
    stage: Optional[CandidateStage] = None
    expected_start_date: Optional[date] = None
    capco_reviewer_id: Optional[str] = None
    ms_reviewer_stakeholder_id: Optional[str] = None
    note: Optional[str] = None


class CandidateInterviewCreate(BaseModel):
    interview_round: int = Field(ge=1, le=20)
    scheduled_at: datetime
    interview_type: str
    ms_interviewer_stakeholder_ids: list[str] = Field(default_factory=list)
    capco_attendee_ids: list[str] = Field(default_factory=list)
    status: InterviewStatus = "SCHEDULED"
    feedback: str = ""
    recommendation: Optional[str] = None


class CandidateInterviewUpdate(BaseModel):
    expected_updated_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[InterviewStatus] = None
    feedback: Optional[str] = None
    recommendation: Optional[str] = None


class OfferCreate(BaseModel):
    proposed_rate: Optional[Decimal] = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    agreed_rate: Optional[Decimal] = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    rate_currency: str = "USD"
    offer_status: OfferStatus = "OFFER_PENDING"
    notes: str = ""


class OfferUpdate(BaseModel):
    expected_updated_at: Optional[datetime] = None
    proposed_rate: Optional[Decimal] = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    agreed_rate: Optional[Decimal] = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    offer_status: Optional[OfferStatus] = None
    notes: Optional[str] = None


class OnboardingRecordUpdate(BaseModel):
    expected_updated_at: Optional[datetime] = None
    expected_start_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    overall_status: Optional[OnboardingStatus] = None


class OnboardingStepUpdate(BaseModel):
    expected_updated_at: Optional[datetime] = None
    status: Optional[OnboardingStepStatus] = None
    responsible_party: Optional[ResponsibleParty] = None
    owner_id: Optional[str] = None
    target_completion_date: Optional[date] = None
    blocker_reason: Optional[str] = None
    notes: Optional[str] = None
