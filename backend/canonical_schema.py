from __future__ import annotations

from sqlalchemy import (
    JSON, Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Index,
    ForeignKeyConstraint, Integer, MetaData, Numeric, String, Table, Text, UniqueConstraint, func,
)


metadata = MetaData()

accounts = Table(
    "accounts", metadata,
    Column("id", String(80), primary_key=True),
    Column("name", String(200), nullable=False, unique=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

pods = Table(
    "pods", metadata,
    Column("id", String(80), primary_key=True),
    Column("account_id", String(80), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
    Column("name", String(120), nullable=False),
    Column("head_stakeholder_id", String(180)),
    UniqueConstraint("account_id", "name", name="uq_pods_account_name"),
)

divisions = Table(
    "divisions", metadata,
    Column("id", String(160), primary_key=True),
    Column("pod_id", String(80), ForeignKey("pods.id", ondelete="RESTRICT"), nullable=False),
    Column("name", String(120), nullable=False),
    Column("color", String(20), nullable=False),
    Column("head_stakeholder_id", String(180)),
    UniqueConstraint("pod_id", "name", name="uq_divisions_pod_name"),
)

business_units = Table(
    "business_units", metadata,
    Column("id", String(220), primary_key=True),
    Column("division_id", String(160), ForeignKey("divisions.id", ondelete="RESTRICT"), nullable=False),
    Column("name", String(160), nullable=False),
    Column("sort_order", Integer, nullable=False, default=0),
    UniqueConstraint("division_id", "name", name="uq_business_units_division_name"),
)

stakeholders = Table(
    "stakeholders", metadata,
    Column("id", String(180), primary_key=True),
    Column("name", String(160), nullable=False),
    Column("title", String(160), nullable=False),
    Column("level", String(80), nullable=False),
    Column("location", String(160), nullable=False),
    Column("country_code", String(2), nullable=False, default="US"),
    Column("biography", Text, nullable=False, default=""),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("created_by", String(180)),
    Column("updated_by", String(180)),
    Column("source_system", String(80), nullable=False, default="manual"),
    Column("source_record_id", String(240)),
    Column("last_synced_at", DateTime(timezone=True)),
    UniqueConstraint("source_system", "source_record_id", name="uq_stakeholder_source_record"),
)

stakeholder_assignments = Table(
    "stakeholder_assignments", metadata,
    Column("id", String(220), primary_key=True),
    Column("stakeholder_id", String(180), ForeignKey("stakeholders.id", ondelete="CASCADE"), nullable=False),
    Column("pod_id", String(80), ForeignKey("pods.id", ondelete="RESTRICT"), nullable=False),
    Column("division_id", String(160), ForeignKey("divisions.id", ondelete="RESTRICT")),
    Column("business_unit_id", String(220), ForeignKey("business_units.id", ondelete="RESTRICT")),
    Column("team_type", String(30), nullable=False),
    Column("organizational_role", String(160), nullable=False),
    Column("manager_stakeholder_id", String(180), ForeignKey("stakeholders.id", ondelete="RESTRICT")),
    Column("is_primary_technology", Boolean, nullable=False, default=False),
    Column("is_buyer", Boolean, nullable=False, default=False),
    Column("is_influencer", Boolean, nullable=False, default=True),
    Column("is_budget_holder", Boolean, nullable=False, default=False),
    Column("relationship_strength", String(30), nullable=False, default="Developing"),
    Column("capco_contingents", Integer, nullable=False, default=0),
    Column("capco_owner", String(160)),
    Column("budget_amount", Numeric(14, 2)),
    Column("tags", JSON, nullable=False, default=list),
    Column("effective_from", Date, nullable=False),
    Column("effective_to", Date),
    Column("is_current", Boolean, nullable=False, default=True),
    CheckConstraint("team_type IN ('Business', 'Technology')", name="ck_assignment_team_type"),
    CheckConstraint("relationship_strength IN ('Strong', 'Medium', 'Developing', 'Unknown')", name="ck_assignment_relationship"),
    CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_assignment_dates"),
    CheckConstraint("organizational_role = 'Pod Head' OR division_id IS NOT NULL", name="ck_assignment_division_scope"),
    CheckConstraint("manager_stakeholder_id IS NOT NULL OR organizational_role = 'Pod Head'", name="ck_assignment_manager_required"),
    CheckConstraint("organizational_role != 'Pod Head' OR (division_id IS NULL AND business_unit_id IS NULL AND manager_stakeholder_id IS NULL)", name="ck_assignment_pod_head_scope"),
)
Index("idx_assignments_scope", stakeholder_assignments.c.pod_id, stakeholder_assignments.c.division_id, stakeholder_assignments.c.business_unit_id, stakeholder_assignments.c.is_current)
Index("idx_assignments_manager", stakeholder_assignments.c.manager_stakeholder_id, stakeholder_assignments.c.is_current)
Index("uq_current_stakeholder_assignment", stakeholder_assignments.c.stakeholder_id, unique=True, sqlite_where=stakeholder_assignments.c.is_current.is_(True), postgresql_where=stakeholder_assignments.c.is_current.is_(True))
Index("uq_current_primary_technology", stakeholder_assignments.c.business_unit_id, unique=True, sqlite_where=stakeholder_assignments.c.is_current.is_(True) & stakeholder_assignments.c.is_primary_technology.is_(True), postgresql_where=stakeholder_assignments.c.is_current.is_(True) & stakeholder_assignments.c.is_primary_technology.is_(True))

enterprise_functions = Table(
    "enterprise_functions", metadata,
    Column("id", String(220), primary_key=True),
    Column("pod_id", String(80), ForeignKey("pods.id", ondelete="RESTRICT"), nullable=False),
    Column("name", String(160), nullable=False),
    Column("lead_stakeholder_id", String(180), ForeignKey("stakeholders.id", ondelete="RESTRICT"), nullable=False),
    UniqueConstraint("pod_id", "name", name="uq_enterprise_function_pod_name"),
)

# Added after both tables are declared to avoid a Python declaration cycle.
pods.append_constraint(ForeignKeyConstraint([pods.c.head_stakeholder_id], [stakeholders.c.id], ondelete="RESTRICT", name="fk_pod_head"))

meetings = Table(
    "meetings", metadata,
    Column("id", String(180), primary_key=True),
    Column("subject", String(200), nullable=False),
    Column("meeting_date", DateTime(timezone=True), nullable=False),
    Column("summary", Text, nullable=False, default=""),
    Column("organizer", String(160), nullable=False),
    Column("outcome", String(240), nullable=False),
    Column("next_steps", JSON, nullable=False, default=list),
    Column("tags", JSON, nullable=False, default=list),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("created_by", String(180)),
    Column("updated_by", String(180)),
    Column("source_system", String(80), nullable=False, default="manual"),
    Column("source_record_id", String(240)),
    Column("last_synced_at", DateTime(timezone=True)),
)
Index("idx_meetings_date", meetings.c.meeting_date)
Index("uq_meeting_source_record", meetings.c.source_system, meetings.c.source_record_id, unique=True)

meeting_stakeholders = Table(
    "meeting_stakeholders", metadata,
    Column("meeting_id", String(180), ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True),
    Column("stakeholder_id", String(180), ForeignKey("stakeholders.id", ondelete="RESTRICT"), primary_key=True),
)
Index("idx_meeting_stakeholders_person", meeting_stakeholders.c.stakeholder_id, meeting_stakeholders.c.meeting_id)

meeting_employees = Table(
    "meeting_employees", metadata,
    Column("meeting_id", String(180), ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True),
    # Cross-domain FK to capco_employees is attached to combined PostgreSQL metadata.
    Column("employee_id", String(120), primary_key=True),
    Column("attendee_role", String(120), nullable=False, default="Account team"),
    Column("is_organizer", Boolean, nullable=False, default=False),
)
Index("idx_meeting_employees_person", meeting_employees.c.employee_id, meeting_employees.c.meeting_id)

notes = Table(
    "notes", metadata,
    Column("id", String(180), primary_key=True),
    Column("stakeholder_id", String(180), ForeignKey("stakeholders.id", ondelete="CASCADE"), nullable=False),
    Column("body", Text, nullable=False),
    Column("category", String(30), nullable=False, default="General"),
    Column("author", String(160), nullable=False),
    Column("author_employee_id", String(120)),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("created_by", String(180)),
    Column("updated_by", String(180)),
)
Index("idx_notes_stakeholder", notes.c.stakeholder_id, notes.c.updated_at)

opportunities = Table(
    "opportunities", metadata,
    Column("id", String(180), primary_key=True),
    Column("pod_id", String(80), ForeignKey("pods.id", ondelete="RESTRICT"), nullable=False),
    Column("business_unit_id", String(220), ForeignKey("business_units.id", ondelete="RESTRICT")),
    Column("name", String(200), nullable=False),
    Column("description", Text, nullable=False, default=""),
    Column("estimated_value", Numeric(14, 2), nullable=False, default=0),
    Column("probability", Integer, nullable=False, default=20),
    Column("stage", String(30), nullable=False, default="Discovery"),
    Column("owner", String(160), nullable=False),
    Column("target_close_date", Date),
    Column("tags", JSON, nullable=False, default=list),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("created_by", String(180)),
    Column("updated_by", String(180)),
    Column("source_system", String(80), nullable=False, default="manual"),
    Column("source_record_id", String(240)),
    Column("last_synced_at", DateTime(timezone=True)),
    CheckConstraint("probability BETWEEN 0 AND 100", name="ck_opportunity_probability"),
    CheckConstraint("stage IN ('Discovery', 'Qualification', 'Proposal', 'Negotiation', 'Closed Won', 'Closed Lost')", name="ck_opportunity_stage"),
)
Index("idx_opportunities_scope", opportunities.c.pod_id, opportunities.c.business_unit_id, opportunities.c.stage)
Index("uq_opportunity_source_record", opportunities.c.source_system, opportunities.c.source_record_id, unique=True)

opportunity_stakeholders = Table(
    "opportunity_stakeholders", metadata,
    Column("opportunity_id", String(180), ForeignKey("opportunities.id", ondelete="CASCADE"), primary_key=True),
    Column("stakeholder_id", String(180), ForeignKey("stakeholders.id", ondelete="RESTRICT"), primary_key=True),
    Column("role", String(80)),
)
Index("idx_opportunity_stakeholders_person", opportunity_stakeholders.c.stakeholder_id, opportunity_stakeholders.c.opportunity_id)

opportunity_employees = Table(
    "opportunity_employees", metadata,
    Column("opportunity_id", String(180), ForeignKey("opportunities.id", ondelete="CASCADE"), primary_key=True),
    # Cross-domain FK to capco_employees is attached to combined PostgreSQL metadata.
    Column("employee_id", String(120), primary_key=True),
    Column("owner_role", String(80), nullable=False, default="Owner"),
    Column("is_primary", Boolean, nullable=False, default=False),
)
Index("idx_opportunity_employees_person", opportunity_employees.c.employee_id, opportunity_employees.c.opportunity_id)

meeting_opportunities = Table(
    "meeting_opportunities", metadata,
    Column("meeting_id", String(180), ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True),
    Column("opportunity_id", String(180), ForeignKey("opportunities.id", ondelete="CASCADE"), primary_key=True),
    Column("relationship_type", String(80), nullable=False, default="Discussion"),
)
Index("idx_meeting_opportunities_opportunity", meeting_opportunities.c.opportunity_id, meeting_opportunities.c.meeting_id)

stakeholder_employee_relationships = Table(
    "stakeholder_employee_relationships", metadata,
    Column("id", String(180), primary_key=True),
    Column("stakeholder_id", String(180), ForeignKey("stakeholders.id", ondelete="CASCADE"), nullable=False),
    # Cross-domain FK to capco_employees is attached to combined PostgreSQL metadata.
    Column("employee_id", String(120), nullable=False),
    Column("relationship_role", String(80), nullable=False, default="Relationship owner"),
    Column("is_primary", Boolean, nullable=False, default=False),
    Column("effective_from", Date, nullable=False),
    Column("effective_to", Date),
    Column("is_current", Boolean, nullable=False, default=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_stakeholder_employee_relationship_dates"),
)
Index("idx_stakeholder_employee_relationship_person", stakeholder_employee_relationships.c.employee_id, stakeholder_employee_relationships.c.is_current)
Index("idx_stakeholder_employee_relationship_stakeholder", stakeholder_employee_relationships.c.stakeholder_id, stakeholder_employee_relationships.c.is_current)
Index(
    "uq_current_primary_stakeholder_employee_relationship",
    stakeholder_employee_relationships.c.stakeholder_id,
    unique=True,
    sqlite_where=stakeholder_employee_relationships.c.is_current.is_(True) & stakeholder_employee_relationships.c.is_primary.is_(True),
    postgresql_where=stakeholder_employee_relationships.c.is_current.is_(True) & stakeholder_employee_relationships.c.is_primary.is_(True),
)

assignment_history = Table(
    "assignment_history", metadata,
    Column("id", String(180), primary_key=True),
    Column("stakeholder_id", String(180), ForeignKey("stakeholders.id", ondelete="CASCADE"), nullable=False),
    Column("change_type", String(40), nullable=False),
    Column("previous_value", Text),
    Column("new_value", Text),
    Column("reason", String(240), nullable=False),
    Column("effective_at", DateTime(timezone=True), nullable=False),
    Column("changed_by", String(180)),
)
Index("idx_assignment_history_person", assignment_history.c.stakeholder_id, assignment_history.c.effective_at)

documents = Table(
    "stakeholder_documents", metadata,
    Column("id", String(180), primary_key=True),
    Column("stakeholder_id", String(180), ForeignKey("stakeholders.id", ondelete="CASCADE")),
    Column("meeting_id", String(180), ForeignKey("meetings.id", ondelete="CASCADE")),
    Column("title", String(240), nullable=False),
    Column("url", Text), Column("sharepoint_url", Text), Column("file_name", String(255)),
    Column("stored_name", String(255)), Column("content_type", String(255)),
    Column("file_size", Integer), Column("download_url", Text),
    Column("document_type", String(40), nullable=False, default="Other"),
    Column("description", Text, nullable=False, default=""),
    Column("owner", String(160), nullable=False), Column("owner_employee_id", String(120)), Column("tags", JSON, nullable=False, default=list),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("created_by", String(180)),
    Column("updated_by", String(180)),
    CheckConstraint("stakeholder_id IS NOT NULL OR meeting_id IS NOT NULL", name="ck_document_owner"),
)
Index("idx_documents_stakeholder", documents.c.stakeholder_id, documents.c.updated_at)
Index("idx_documents_meeting", documents.c.meeting_id, documents.c.updated_at)

application_state = Table(
    "application_state", metadata,
    Column("key", String(180), primary_key=True),
    Column("value", JSON, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

audit_events = Table(
    "audit_events", metadata,
    Column("id", String(180), primary_key=True),
    Column("occurred_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("actor_subject", String(240), nullable=False),
    Column("actor_employee_id", String(120)),
    Column("action", String(80), nullable=False),
    Column("entity_type", String(80), nullable=False),
    Column("entity_id", String(180), nullable=False),
    Column("changes", JSON, nullable=False, default=dict),
    Column("request_id", String(180)),
)
Index("idx_audit_entity_time", audit_events.c.entity_type, audit_events.c.entity_id, audit_events.c.occurred_at)

idempotency_records = Table(
    "idempotency_records", metadata,
    Column("id", String(180), primary_key=True),
    Column("actor_subject", String(240), nullable=False),
    Column("idempotency_key", String(180), nullable=False),
    Column("method", String(12), nullable=False),
    Column("path", String(500), nullable=False),
    Column("request_hash", String(64), nullable=False),
    Column("response_status", Integer, nullable=False),
    Column("response_body", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("actor_subject", "idempotency_key", name="uq_idempotency_actor_key"),
)
Index("idx_idempotency_expiry", idempotency_records.c.expires_at)


# The account assistant keeps retrieval artifacts beside the canonical account
# data.  Document chunks reference the governed document row instead of
# creating a second document catalogue, while conversations are private to the
# authenticated application subject that created them.
assistant_document_indexes = Table(
    "assistant_document_indexes", metadata,
    Column("document_id", String(180), ForeignKey("stakeholder_documents.id", ondelete="CASCADE"), primary_key=True),
    Column("status", String(30), nullable=False),
    Column("content_hash", String(64)),
    Column("chunk_count", Integer, nullable=False, default=0),
    Column("indexed_at", DateTime(timezone=True)),
    Column("error_code", String(80)),
    CheckConstraint(
        "status IN ('ready', 'metadata_only', 'unsupported', 'failed')",
        name="ck_assistant_document_index_status",
    ),
)

assistant_document_chunks = Table(
    "assistant_document_chunks", metadata,
    Column("id", String(180), primary_key=True),
    Column("document_id", String(180), ForeignKey("stakeholder_documents.id", ondelete="CASCADE"), nullable=False),
    Column("chunk_index", Integer, nullable=False),
    Column("content", Text, nullable=False),
    Column("char_start", Integer, nullable=False),
    Column("char_end", Integer, nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("document_id", "chunk_index", name="uq_assistant_document_chunk_position"),
    CheckConstraint("char_start >= 0 AND char_end >= char_start", name="ck_assistant_document_chunk_range"),
)
Index("idx_assistant_chunks_document", assistant_document_chunks.c.document_id, assistant_document_chunks.c.chunk_index)

assistant_conversations = Table(
    "assistant_conversations", metadata,
    Column("id", String(180), primary_key=True),
    Column("actor_subject", String(240), nullable=False),
    Column("title", String(240), nullable=False),
    Column("context_pod", String(120)),
    Column("context_section", String(120)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
Index("idx_assistant_conversations_actor", assistant_conversations.c.actor_subject, assistant_conversations.c.updated_at)

assistant_messages = Table(
    "assistant_messages", metadata,
    Column("id", String(180), primary_key=True),
    Column("conversation_id", String(180), ForeignKey("assistant_conversations.id", ondelete="CASCADE"), nullable=False),
    Column("role", String(20), nullable=False),
    Column("content", Text, nullable=False),
    Column("citations", JSON, nullable=False, default=list),
    Column("provider", String(40)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("role IN ('user', 'assistant')", name="ck_assistant_message_role"),
)
Index("idx_assistant_messages_conversation", assistant_messages.c.conversation_id, assistant_messages.c.created_at)
Index("idx_audit_actor_time", audit_events.c.actor_subject, audit_events.c.occurred_at)
