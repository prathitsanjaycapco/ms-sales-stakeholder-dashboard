from pathlib import Path
from typing import Optional
from datetime import date, datetime, timezone
from uuid import uuid4
import logging

from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.pool import StaticPool

from .models import (
    AssignmentHistory,
    MapResponse,
    Meeting,
    MeetingCreate,
    MeetingUpdate,
    PodMeetingCreate,
    PodMeetingUpdate,
    Note,
    NoteCreate,
    NoteUpdate,
    Opportunity,
    OpportunityCreate,
    OpportunityUpdate,
    PrimaryTechnologyUpdate,
    ReportingLineUpdate,
    Stakeholder,
    StakeholderCreate,
    StakeholderUpdate,
    DashboardTaskUpdate,
    DashboardTaskCreate,
    DocumentLink,
    DocumentLinkCreate,
    DocumentLinkUpdate,
    PodFocusUpdate,
    CriticalItemUpdate,
    CriticalItemCreate,
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantConversation,
)
from .repository import (
    ConflictError,
    NotFoundError,
    POD_STRUCTURE,
    slug,
)
from .persistence import create_repository
from .pod_store import PodOperatingStore
from .executive_store import ExecutiveAnalyticsStore, engagements, employees
from .config import settings
from .integrity import reconcile_account
from .governance import READ_ROLES, principal_from_request, record_audit_event
from .identity_service import IdentityService
from .rag_service import AccountAssistantService


repository = create_repository()
pod_engine = getattr(repository, "engine", None) or create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
executive_store = ExecutiveAnalyticsStore(
    pod_engine, repository, None,
    seed_demo_data=settings.seed_demo_data,
    auto_create_schema=settings.auto_create_schema,
)
pod_store = PodOperatingStore(
    pod_engine, repository,
    seed_demo_data=settings.seed_demo_data,
    auto_create_schema=settings.auto_create_schema,
)
executive_store.pod_store = pod_store
executive_store.reconcile_operating_links()
if hasattr(repository, "reconcile_external_identities"):
    repository.reconcile_external_identities()
identity_service = IdentityService(pod_engine)
assistant_service = AccountAssistantService(pod_engine, repository, pod_store, executive_store, settings)

UPLOAD_ROOT = settings.upload_root
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".docm", ".xls", ".xlsx", ".xlsm", ".ppt", ".pptx",
    ".txt", ".csv", ".rtf", ".png", ".jpg", ".jpeg", ".msg", ".eml",
}
logger = logging.getLogger("stakeholder_intelligence")


app = FastAPI(
    title="Morgan Stanley Stakeholder Intelligence API",
    version="1.0.0",
    description="Organizational intelligence, relationship management, and opportunity APIs for the stakeholder map.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?" if settings.environment != "production" else None,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"] if settings.environment != "production" else ["Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def identity_permissions_and_audit(request: Request, call_next):
    request.state.request_id = request.headers.get("x-request-id") or f"request-{uuid4().hex}"
    if request.url.path == "/api/health":
        response = await call_next(request)
    else:
        principal = principal_from_request(request, settings)
        if principal is None:
            return JSONResponse(status_code=401, content={"detail": "Authenticated identity is required"})
        request.state.principal = principal
        if not principal.roles:
            return JSONResponse(status_code=403, content={"detail": "No application role is assigned"})
        personal_assistant_action = (
            request.method == "POST" and request.url.path == "/api/assistant/chat"
        ) or (
            request.method == "DELETE" and request.url.path.startswith("/api/assistant/conversations/")
        )
        if request.method not in {"GET", "HEAD", "OPTIONS"} and not personal_assistant_action and not principal.can_write:
            return JSONResponse(status_code=403, content={"detail": "This operation requires an Editor, Account Manager, or Account Admin role"})
        response = await call_next(request)
        if request.method not in {"GET", "HEAD", "OPTIONS"} and response.status_code < 400:
            audit_id = record_audit_event(pod_engine, principal, request, response.status_code)
            response.headers["X-Audit-Event-ID"] = audit_id
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


def translate_domain_error(error: Exception) -> HTTPException:
    if isinstance(error, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, ConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, ValueError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    if isinstance(error, IntegrityError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The change conflicts with an existing or referenced record")
    if isinstance(error, SQLAlchemyError):
        logger.error("Database operation failed (%s)", type(error).__name__)
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="The database operation could not be completed")
    logger.error("Unhandled application operation failed (%s)", type(error).__name__)
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="The operation could not be completed")


async def save_uploaded_document(request: Request, file_name: str) -> tuple[str, int, str]:
    safe_name = Path(file_name).name.strip()
    suffix = Path(safe_name).suffix.lower()
    if not safe_name or safe_name in {".", ".."} or suffix not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported document file type")
    declared_size = request.headers.get("content-length")
    if declared_size and int(declared_size) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Document exceeds the 25 MB limit")
    stored_name = f"{uuid4().hex}{suffix}"
    target = (UPLOAD_ROOT / stored_name).resolve()
    if target.parent != UPLOAD_ROOT.resolve():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document file name")
    size = 0
    try:
        with target.open("xb") as handle:
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Document exceeds the 25 MB limit")
                handle.write(chunk)
        if size == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded document is empty")
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return stored_name, size, request.headers.get("content-type", "application/octet-stream")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "stakeholder-intelligence-api",
        "version": app.version,
        "repository": getattr(repository, "backend_name", "memory"),
        "persistent": getattr(repository, "backend_name", "").startswith("normalized-sql"),
    }


@app.get("/api/health/details")
def health_details():
    return {
        "status": "ok",
        "service": "stakeholder-intelligence-api",
        "version": app.version,
        "environment": settings.environment,
        "repository": getattr(repository, "backend_name", "memory"),
        "persistent": getattr(repository, "backend_name", "").startswith("normalized-sql"),
        "demo_data_enabled": settings.seed_demo_data,
        "storage_warning": getattr(repository, "storage_warning", None),
        "counts": {
            "stakeholders": len(repository.stakeholders),
            "meetings": len(repository.meetings),
            "notes": len(repository.notes),
            "documents": len(repository.documents),
            "opportunities": len(repository.opportunities),
            "pod_view": pod_store.counts(),
            "executive_view": executive_store.counts(),
        },
    }


@app.get("/api/session")
def session(request: Request):
    return request.state.principal.as_dict()


@app.get("/api/assistant/conversations", response_model=list[AssistantConversation])
def assistant_conversations_list(request: Request, limit: int = Query(default=20, ge=1, le=50)):
    if not request.state.principal.roles.intersection(READ_ROLES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account read access is required")
    return assistant_service.list_conversations(request.state.principal.subject, limit)


@app.get("/api/assistant/conversations/{conversation_id}", response_model=AssistantConversation)
def assistant_conversation_detail(conversation_id: str, request: Request):
    if not request.state.principal.roles.intersection(READ_ROLES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account read access is required")
    try:
        return assistant_service.get_conversation(conversation_id, request.state.principal.subject)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.delete("/api/assistant/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def assistant_conversation_delete(conversation_id: str, request: Request):
    if not request.state.principal.roles.intersection(READ_ROLES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account read access is required")
    try:
        assistant_service.delete_conversation(conversation_id, request.state.principal.subject)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.post("/api/assistant/chat", response_model=AssistantChatResponse)
def assistant_chat(payload: AssistantChatRequest, request: Request):
    if not request.state.principal.roles.intersection(READ_ROLES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account read access is required")
    try:
        return assistant_service.ask(payload, request.state.principal.subject, UPLOAD_ROOT)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/assistant/document-index")
def assistant_document_index(request: Request):
    if not request.state.principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account Admin access is required")
    return assistant_service.document_index_status()


@app.post("/api/assistant/documents/reindex")
def assistant_reindex_documents(request: Request):
    if not request.state.principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account Admin access is required")
    return [assistant_service.index_document(document, UPLOAD_ROOT) for document in repository.documents.values()]


@app.get("/api/employees")
def list_employees(active: Optional[bool] = True, search: Optional[str] = None):
    return identity_service.list_employees(active, search)


@app.get("/api/employees/{employee_id}/profile")
def employee_profile(employee_id: str):
    try:
        return identity_service.employee_profile(employee_id)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/engagements/{engagement_id}")
def engagement_detail(engagement_id: str):
    try:
        return identity_service.engagement_detail(engagement_id)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/audit-events")
def audit_event_history(
    request: Request,
    limit: int = Query(default=100, ge=1, le=1000),
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
):
    if not request.state.principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account Admin role required")
    return identity_service.list_audit_events(limit, entity_type, entity_id)


@app.get("/api/integrity/reconciliation")
def integrity_reconciliation(anchor: Optional[date] = None):
    """Cross-screen and relational integrity evidence for deployment validation."""
    return reconcile_account(repository, pod_store, executive_store, anchor)


@app.get("/api/pods")
def pods():
    return [
        {
            "id": pod,
            "name": pod,
            "division_count": len(divisions),
            "business_unit_count": sum(len(units) for units in divisions.values()),
            "stakeholder_count": len(repository.list_stakeholders(pod=pod)),
        }
        for pod, divisions in POD_STRUCTURE.items()
    ]


@app.get("/api/search")
def global_search(q: str = Query(min_length=2, max_length=120), pod: Optional[str] = None, limit: int = Query(default=8, ge=1, le=20)):
    """Grouped search over canonical people, organization, activity, and portfolio records."""
    if pod and pod != "All" and pod not in POD_STRUCTURE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pod not found")
    needle = q.strip().casefold()
    people = [item for item in repository.list_stakeholders(pod=None if pod == "All" else pod) if needle in f"{item.name} {item.title} {item.business_unit} {item.division}".casefold()][:limit]
    stakeholder_ids = {item.id for item in repository.list_stakeholders(pod=None if not pod or pod == "All" else pod)}
    opportunity_rows = [item for item in repository.list_opportunities() if stakeholder_ids.intersection(item.stakeholder_ids) and needle in f"{item.name} {item.description} {item.stage}".casefold()][:limit]
    meeting_rows = [item for item in repository.list_meetings() if stakeholder_ids.intersection(item.stakeholder_ids) and needle in f"{item.subject} {item.summary} {item.outcome}".casefold()][:limit]
    unit_rows = [item for item in repository.units.values() if (not pod or pod == "All" or item["pod"] == pod) and needle in f"{item['name']} {item['division']} {item['pod']}".casefold()][:limit]
    with executive_store.engine.connect() as connection:
        project_rows = [dict(item) for item in connection.execute(select(engagements)).mappings() if (not pod or pod == "All" or item["pod_id"] == pod) and needle in f"{item['name']} {item['business_unit']} {item['division']}".casefold()][:limit]
        employee_rows = [dict(item) for item in connection.execute(select(employees)).mappings() if needle in f"{item['name']} {item['role']} {item['location']}".casefold()][:limit]

    def person_for(ids):
        return next((repository.stakeholders[value] for value in ids if value in repository.stakeholders), None)

    return {
        "query": q, "groups": {
            "Stakeholders": [{"type": "stakeholder", "id": item.id, "label": item.name, "context": f"{item.title} · {item.business_unit}", "pod": item.pod} for item in people],
            "Business units": [{"type": "business_unit", "id": item["id"], "label": item["name"], "context": item["division"], "pod": item["pod"]} for item in unit_rows],
            "Meetings": [{"type": "meeting", "id": item.id, "label": item.subject, "context": item.meeting_date.isoformat(), "pod": person_for(item.stakeholder_ids).pod if person_for(item.stakeholder_ids) else None} for item in meeting_rows],
            "Opportunities": [{"type": "opportunity", "id": item.id, "label": item.name, "context": f"{item.stage} · ${item.estimated_value:,.0f}", "pod": person_for(item.stakeholder_ids).pod if person_for(item.stakeholder_ids) else None} for item in opportunity_rows],
            "Engagements": [{"type": "engagement", "id": item["id"], "label": item["name"], "context": f"{item['business_unit']} · {item['health']}", "pod": item["pod_id"]} for item in project_rows],
            "Capco employees": [{"type": "employee", "id": item["id"], "label": item["name"], "context": f"{item['role']} · {item['location']}", "pod": None} for item in employee_rows],
        },
    }


@app.get("/api/pods/{pod}/filters")
def pod_filters(pod: str):
    try:
        return repository.filter_options(pod)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/pods/{pod}/dashboard")
def pod_dashboard(
    pod: str,
    period: str = Query(default="week", pattern="^(week|month)$"),
    period_start: Optional[date] = None,
    tag: Optional[str] = None,
):
    """Consolidated cockpit payload read from normalized SQL operating tables."""
    try:
        view_model = pod_store.dashboard(pod, period, period_start, tag)
        return {
            "pod": pod,
            "period": period,
            "period_start": period_start,
            "generated_at": datetime.now(timezone.utc),
            "data_source": "sql",
            "pulse": {
                "meetings": len(view_model["meetings"]),
                "critical": len(view_model["criticalItems"]),
                "actions": len([item for item in view_model["tasks"] if item["status"] != "Done"]),
                "pipeline": sum(item["value"] for item in view_model["opportunities"]),
                "weighted_pipeline": sum(item["value"] * item["probability"] / 100 for item in view_model["opportunities"]),
            },
            "calendar_events": [{
                "id": item["id"],
                "type": item["type"].upper(),
                "title": item["title"],
                "start_datetime": item["start"],
                "all_day": False,
                "stakeholder_ids": item["stakeholderIds"],
                "meeting_id": item["meetingId"],
            } for item in view_model["meetings"]],
            "opportunities": view_model["opportunities"],
            "critical_items": view_model["criticalItems"],
            "tasks": view_model["tasks"],
            "milestones": view_model["milestones"],
            "leadership_focus": view_model["focus"],
            "view_model": view_model,
        }
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/executive/overview")
def executive_overview(
    period: str = Query(default="quarter", pattern="^(month|quarter|ytd|custom)$"),
    anchor: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    pod: Optional[str] = None,
):
    """One connected, period-aware account command-center payload."""
    try:
        return executive_store.overview(period, anchor, start_date, end_date, pod)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/executive/weekly")
def executive_weekly(
    week_start: Optional[date] = None,
    pod: Optional[str] = None,
    outlook_weeks: int = Query(default=4, ge=1, le=8),
):
    """Week-first operating view across Capco people, account activity and management actions."""
    try:
        return executive_store.weekly(week_start, pod, outlook_weeks)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/pods/{pod}/tasks")
def pod_tasks(pod: str):
    try:
        return pod_store.list_tasks(pod)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.patch("/api/pods/{pod}/tasks/{task_id}")
def update_pod_task(pod: str, task_id: str, payload: DashboardTaskUpdate):
    try:
        return pod_store.update_task(pod, task_id, payload.model_dump(exclude_unset=True))
    except Exception as error:
        raise translate_domain_error(error) from error


@app.post("/api/pods/{pod}/tasks", status_code=status.HTTP_201_CREATED)
def create_pod_task(pod: str, payload: DashboardTaskCreate):
    try:
        return pod_store.create_task(pod, payload.model_dump(), f"task-{uuid4().hex[:12]}")
    except Exception as error:
        raise translate_domain_error(error) from error


@app.patch("/api/pods/{pod}/focus")
def update_pod_focus(pod: str, payload: PodFocusUpdate):
    try:
        return {"pod": pod, "focus": pod_store.update_focus(pod, payload.focus), "updated_at": datetime.now(timezone.utc)}
    except Exception as error:
        raise translate_domain_error(error) from error


@app.patch("/api/pods/{pod}/critical-items/{item_id}")
def update_critical_item(pod: str, item_id: str, payload: CriticalItemUpdate):
    try:
        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            raise ValueError("At least one critical item field is required")
        return pod_store.update_critical_item(pod, item_id, changes)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.post("/api/pods/{pod}/critical-items", status_code=status.HTTP_201_CREATED)
def create_critical_item(pod: str, payload: CriticalItemCreate):
    try:
        return pod_store.create_critical_item(pod, payload.model_dump(), f"critical-{uuid4().hex[:12]}")
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/pods/{pod}/map", response_model=MapResponse)
def pod_map(
    pod: str,
    search: Optional[str] = None,
    division: Optional[str] = None,
    business_unit: Optional[str] = None,
    team_type: Optional[str] = None,
    location: Optional[str] = None,
    level: Optional[str] = None,
    role: Optional[str] = None,
    budget_holder: Optional[bool] = None,
    relationship_strength: Optional[str] = None,
    capco_owner: Optional[str] = None,
    meeting_recency: Optional[str] = None,
    has_opportunities: Optional[bool] = None,
    tag: Optional[str] = None,
):
    try:
        return repository.build_map(
            pod,
            search=search,
            division=division,
            business_unit=business_unit,
            team_type=team_type,
            location=location,
            level=level,
            role=role,
            budget_holder=budget_holder,
            relationship_strength=relationship_strength,
            capco_owner=capco_owner,
            meeting_recency=meeting_recency,
            has_opportunities=has_opportunities,
            tag=tag,
        )
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/stakeholders", response_model=list[Stakeholder])
def list_stakeholders(
    pod: Optional[str] = Query(default="ISG"),
    search: Optional[str] = None,
    division: Optional[str] = None,
    business_unit: Optional[str] = None,
    team_type: Optional[str] = None,
    location: Optional[str] = None,
    level: Optional[str] = None,
    role: Optional[str] = None,
    budget_holder: Optional[bool] = None,
    relationship_strength: Optional[str] = None,
    capco_owner: Optional[str] = None,
    meeting_recency: Optional[str] = None,
    has_opportunities: Optional[bool] = None,
    tag: Optional[str] = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=1000),
):
    records = repository.list_stakeholders(
        pod=pod,
        search=search,
        division=division,
        business_unit=business_unit,
        team_type=team_type,
        location=location,
        level=level,
        role=role,
        budget_holder=budget_holder,
        relationship_strength=relationship_strength,
        capco_owner=capco_owner,
        meeting_recency=meeting_recency,
        has_opportunities=has_opportunities,
        tag=tag,
    )
    return records[offset:offset + limit]


@app.post("/api/stakeholders", response_model=Stakeholder, status_code=status.HTTP_201_CREATED)
def create_stakeholder(payload: StakeholderCreate):
    try:
        return repository.create_stakeholder(payload)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/stakeholders/{stakeholder_id}", response_model=Stakeholder)
def get_stakeholder(stakeholder_id: str):
    try:
        return repository.get_stakeholder(stakeholder_id)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.patch("/api/stakeholders/{stakeholder_id}", response_model=Stakeholder)
def update_stakeholder(stakeholder_id: str, payload: StakeholderUpdate):
    try:
        return repository.update_stakeholder(stakeholder_id, payload)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.delete("/api/stakeholders/{stakeholder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stakeholder(stakeholder_id: str):
    try:
        repository.delete_stakeholder(stakeholder_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/stakeholders/{stakeholder_id}/team")
def stakeholder_team(stakeholder_id: str):
    try:
        return repository.get_team(stakeholder_id)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/stakeholders/{stakeholder_id}/profile")
def stakeholder_profile(stakeholder_id: str):
    """Return the complete drawer payload in one request."""
    try:
        return {
            "stakeholder": repository.get_stakeholder(stakeholder_id),
            "team": repository.get_team(stakeholder_id),
            "meetings": repository.list_meetings(stakeholder_id),
            "notes": repository.list_notes(stakeholder_id),
            "documents": repository.list_documents(stakeholder_id),
            "opportunities": repository.list_opportunities(stakeholder_id),
            "assignment_history": repository.list_history(stakeholder_id),
        }
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/stakeholders/{stakeholder_id}/history", response_model=list[AssignmentHistory])
def stakeholder_history(stakeholder_id: str):
    try:
        return repository.list_history(stakeholder_id)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/organization/history", response_model=list[AssignmentHistory])
def organization_history(limit: int = Query(default=100, ge=1, le=1000)):
    return repository.list_history()[:limit]


@app.patch("/api/organization/reporting-line")
def update_reporting_line(payload: ReportingLineUpdate):
    try:
        return repository.update_reporting_line(payload.report_id, payload.manager_id, payload.reason)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.patch("/api/business-units/{business_unit_id}/primary-tech-stakeholder")
def update_primary_technology(business_unit_id: str, payload: PrimaryTechnologyUpdate):
    try:
        return repository.set_primary_technology(business_unit_id, payload.stakeholder_id, payload.reason)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/meetings", response_model=list[Meeting])
def list_meetings(stakeholder_id: Optional[str] = None, upcoming: Optional[bool] = None, pod: Optional[str] = None):
    try:
        records = repository.list_meetings(stakeholder_id, upcoming)
        if pod:
            stakeholder_ids = {item.id for item in repository.list_stakeholders(pod=pod)}
            records = [item for item in records if stakeholder_ids.intersection(item.stakeholder_ids)]
        return records
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/stakeholders/{stakeholder_id}/meetings", response_model=list[Meeting])
def stakeholder_meetings(stakeholder_id: str, upcoming: Optional[bool] = None):
    try:
        return repository.list_meetings(stakeholder_id, upcoming)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/meetings/{meeting_id}", response_model=Meeting)
def get_meeting(meeting_id: str):
    try:
        return repository.get_meeting(meeting_id)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.post("/api/meetings", response_model=Meeting, status_code=status.HTTP_201_CREATED)
def create_meeting(payload: MeetingCreate):
    try:
        return repository.create_meeting(payload)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/pods/{pod}/meeting-options")
def pod_meeting_options(pod: str):
    try:
        return pod_store.list_meeting_options(pod)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.post("/api/pods/{pod}/meetings", status_code=status.HTTP_201_CREATED)
def create_pod_meeting(pod: str, payload: PodMeetingCreate):
    try:
        pod_stakeholder_ids = {item.id for item in repository.list_stakeholders(pod=pod)}
        if not pod_stakeholder_ids or any(value not in pod_stakeholder_ids for value in payload.stakeholder_ids):
            raise NotFoundError("Meeting stakeholder is not available in this pod")
        if payload.opportunity_id:
            valid_opportunities = {
                item.id for item in repository.list_opportunities()
                if pod_stakeholder_ids.intersection(item.stakeholder_ids)
            }
            if payload.opportunity_id not in valid_opportunities:
                raise NotFoundError("Meeting opportunity is not available in this pod")
        meeting_payload = MeetingCreate(**payload.model_dump(include={
            "subject", "meeting_date", "summary", "stakeholder_ids", "organizer", "outcome", "next_steps", "tags",
            "organizer_employee_id", "capco_attendee_ids",
        }), opportunity_ids=[payload.opportunity_id] if payload.opportunity_id else [])
        if hasattr(repository, "create_meeting_transactional"):
            meeting, event = repository.create_meeting_transactional(
                meeting_payload,
                lambda connection, record: pod_store.create_meeting_event(
                    pod, record, payload.model_dump(), connection=connection,
                ),
            )
        else:
            meeting = repository.create_meeting(meeting_payload)
            event = pod_store.create_meeting_event(pod, meeting, payload.model_dump())
        return {"meeting": meeting, "event": event}
    except Exception as error:
        raise translate_domain_error(error) from error


@app.patch("/api/pods/{pod}/meetings/{meeting_id}")
def update_pod_meeting(pod: str, meeting_id: str, payload: PodMeetingUpdate):
    try:
        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            raise ValueError("At least one meeting field is required")
        meeting_fields = {key: value for key, value in changes.items() if key in {
            "subject", "meeting_date", "summary", "stakeholder_ids", "organizer", "organizer_employee_id",
            "capco_attendee_ids", "outcome", "next_steps", "tags",
        }}
        if "opportunity_id" in changes:
            meeting_fields["opportunity_ids"] = [changes["opportunity_id"]] if changes["opportunity_id"] else []
        if hasattr(repository, "update_meeting_transactional") and meeting_id in repository.meetings:
            _, event = repository.update_meeting_transactional(
                meeting_id,
                MeetingUpdate(**meeting_fields),
                lambda connection, _record: pod_store.update_meeting_event(
                    pod, meeting_id, changes, connection=connection, update_canonical=False,
                ),
            )
            return event
        return pod_store.update_meeting_event(pod, meeting_id, changes)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/stakeholders/{stakeholder_id}/notes", response_model=list[Note])
def stakeholder_notes(stakeholder_id: str):
    try:
        return repository.list_notes(stakeholder_id)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.post("/api/stakeholders/{stakeholder_id}/notes", response_model=Note, status_code=status.HTTP_201_CREATED)
def create_note(stakeholder_id: str, payload: NoteCreate):
    try:
        return repository.create_note(stakeholder_id, payload)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.patch("/api/notes/{note_id}", response_model=Note)
def update_note(note_id: str, payload: NoteUpdate):
    try:
        return repository.update_note(note_id, payload)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.delete("/api/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: str):
    try:
        repository.delete_note(note_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/stakeholders/{stakeholder_id}/documents", response_model=list[DocumentLink])
def stakeholder_documents(stakeholder_id: str):
    try:
        return repository.list_documents(stakeholder_id)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.post("/api/stakeholders/{stakeholder_id}/documents", response_model=DocumentLink, status_code=status.HTTP_201_CREATED)
def create_document(stakeholder_id: str, payload: DocumentLinkCreate):
    try:
        if payload.stored_name or payload.file_name or payload.file_size is not None:
            raise ValueError("Use the document upload endpoint to create a local file copy")
        document = repository.create_document(stakeholder_id, payload)
        assistant_service.index_document(document, UPLOAD_ROOT)
        return document
    except Exception as error:
        raise translate_domain_error(error) from error


@app.post("/api/stakeholders/{stakeholder_id}/documents/upload", response_model=DocumentLink, status_code=status.HTTP_201_CREATED)
async def upload_stakeholder_document(
    stakeholder_id: str,
    request: Request,
    file_name: str = Query(min_length=1, max_length=255),
    title: str = Query(min_length=2, max_length=240),
    document_type: str = Query(default="Other"),
    description: str = Query(default="", max_length=2000),
    owner: str = Query(default="Capco Account Team", max_length=160),
    owner_employee_id: Optional[str] = Query(default=None, max_length=120),
    sharepoint_url: Optional[str] = Query(default=None, max_length=2000),
    tags: str = Query(default="", max_length=1000),
):
    stored_name, size, content_type = await save_uploaded_document(request, file_name)
    try:
        payload = DocumentLinkCreate(
            title=title,
            sharepoint_url=sharepoint_url or None,
            file_name=Path(file_name).name,
            stored_name=stored_name,
            content_type=content_type,
            file_size=size,
            document_type=document_type,
            description=description,
            owner=owner,
            owner_employee_id=owner_employee_id,
            tags=[value.strip() for value in tags.split(",") if value.strip()],
        )
        document = repository.create_document(stakeholder_id, payload)
        assistant_service.index_document(document, UPLOAD_ROOT)
        return document
    except Exception as error:
        (UPLOAD_ROOT / stored_name).unlink(missing_ok=True)
        raise translate_domain_error(error) from error


@app.get("/api/meetings/{meeting_id}/documents", response_model=list[DocumentLink])
def meeting_documents(meeting_id: str):
    try:
        if meeting_id not in repository.meetings and not pod_store.event_exists(meeting_id):
            raise NotFoundError("Meeting not found")
        return repository.list_meeting_documents(meeting_id)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/meetings/{meeting_id}/brief")
def meeting_brief(meeting_id: str):
    try:
        return pod_store.generate_meeting_brief(meeting_id)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.post("/api/meetings/{meeting_id}/documents/upload", response_model=DocumentLink, status_code=status.HTTP_201_CREATED)
async def upload_meeting_document(
    meeting_id: str,
    request: Request,
    file_name: str = Query(min_length=1, max_length=255),
    title: str = Query(min_length=2, max_length=240),
    document_type: str = Query(default="Meeting Brief"),
    description: str = Query(default="", max_length=2000),
    owner: str = Query(default="Capco Account Team", max_length=160),
    owner_employee_id: Optional[str] = Query(default=None, max_length=120),
    sharepoint_url: Optional[str] = Query(default=None, max_length=2000),
    tags: str = Query(default="", max_length=1000),
):
    if meeting_id not in repository.meetings and not pod_store.event_exists(meeting_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    stored_name, size, content_type = await save_uploaded_document(request, file_name)
    try:
        payload = DocumentLinkCreate(
            title=title,
            sharepoint_url=sharepoint_url or None,
            file_name=Path(file_name).name,
            stored_name=stored_name,
            content_type=content_type,
            file_size=size,
            document_type=document_type,
            description=description,
            owner=owner,
            owner_employee_id=owner_employee_id,
            tags=[value.strip() for value in tags.split(",") if value.strip()],
        )
        document = repository.create_meeting_document(meeting_id, payload)
        assistant_service.index_document(document, UPLOAD_ROOT)
        return document
    except Exception as error:
        (UPLOAD_ROOT / stored_name).unlink(missing_ok=True)
        raise translate_domain_error(error) from error


@app.patch("/api/documents/{document_id}", response_model=DocumentLink)
def update_document(document_id: str, payload: DocumentLinkUpdate):
    try:
        return repository.update_document(document_id, payload)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/documents/{document_id}/download")
def download_document(document_id: str):
    try:
        document = repository.get_document(document_id)
        if not document.stored_name or not document.file_name:
            raise NotFoundError("This document does not have a local uploaded copy")
        target = (UPLOAD_ROOT / document.stored_name).resolve()
        if target.parent != UPLOAD_ROOT.resolve() or not target.is_file():
            raise NotFoundError("The uploaded document file is not available")
        return FileResponse(
            target,
            media_type="application/octet-stream",
            filename=document.file_name,
            headers={"X-Content-Type-Options": "nosniff"},
        )
    except Exception as error:
        raise translate_domain_error(error) from error


@app.delete("/api/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str):
    try:
        document = repository.get_document(document_id)
        repository.delete_document(document_id)
        if document.stored_name:
            target = (UPLOAD_ROOT / document.stored_name).resolve()
            if target.parent == UPLOAD_ROOT.resolve():
                target.unlink(missing_ok=True)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/opportunities", response_model=list[Opportunity])
def list_opportunities(stakeholder_id: Optional[str] = None, stage: Optional[str] = None):
    try:
        return repository.list_opportunities(stakeholder_id, stage)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/stakeholders/{stakeholder_id}/opportunities", response_model=list[Opportunity])
def stakeholder_opportunities(stakeholder_id: str, stage: Optional[str] = None):
    try:
        return repository.list_opportunities(stakeholder_id, stage)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/opportunities/{opportunity_id}", response_model=Opportunity)
def get_opportunity(opportunity_id: str):
    try:
        return repository.get_opportunity(opportunity_id)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.post("/api/opportunities", response_model=Opportunity, status_code=status.HTTP_201_CREATED)
def create_opportunity(payload: OpportunityCreate):
    try:
        return repository.create_opportunity(payload)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.patch("/api/opportunities/{opportunity_id}", response_model=Opportunity)
def update_opportunity(opportunity_id: str, payload: OpportunityUpdate):
    try:
        return repository.update_opportunity(opportunity_id, payload)
    except Exception as error:
        raise translate_domain_error(error) from error


@app.get("/api/pods/{pod}/coverage")
def coverage(pod: str):
    try:
        return repository.coverage(pod)
    except Exception as error:
        raise translate_domain_error(error) from error
