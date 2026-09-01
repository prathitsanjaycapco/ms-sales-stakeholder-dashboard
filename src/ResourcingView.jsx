import React, { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle, ArrowRight, BriefcaseBusiness, CalendarClock, Check,
  CheckCircle2, ChevronRight, CircleDot, Clock3, Columns3, Filter,
  List, RefreshCw, Search, ShieldAlert, SlidersHorizontal, UserRound,
  UsersRound, X, Plus, Save, ArrowUpDown,
} from "lucide-react";
import { api } from "./api";
import "./resourcingAuthoring.css";
import "./resourcingPagination.css";
import { parseBackendDate } from "./dateUtils";

const TABS = ["Overview", "Open Roles", "Candidates", "Onboarding"];
const PIPELINE = [
  ["CAPCO_REVIEW", "Capco Review"], ["SUBMITTED_TO_MS", "Submitted to MS"],
  ["MS_REVIEW", "MS Review"], ["INTERVIEW", "Interview"], ["OFFER", "Offer"],
];
const STAGE_LABELS = {
  IDENTIFIED: "Identified", CAPCO_REVIEW: "Capco Review", SUBMITTED_TO_MS: "Submitted to MS",
  MS_REVIEW: "MS Review", INTERVIEW_SCHEDULED: "Interview Scheduled", INTERVIEWING: "Interviewing",
  OFFER: "Offer / Rate", SELECTED: "Selected", REJECTED: "Rejected", WITHDRAWN: "Withdrawn",
};
const STEP_STATUS = { COMPLETE: "Complete", IN_PROGRESS: "In progress", BLOCKED: "Blocked", NOT_STARTED: "Not started", NOT_APPLICABLE: "N/A" };
const dateLabel = (value) => value ? new Date(`${String(value).slice(0, 10)}T12:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "TBD";
const longDate = (value) => value ? new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "Not recorded";
const initials = (name = "") => name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
const candidateColumn = (stage) => stage === "IDENTIFIED" ? "CAPCO_REVIEW" : stage === "INTERVIEW_SCHEDULED" || stage === "INTERVIEWING" ? "INTERVIEW" : stage === "SELECTED" ? "OFFER" : stage;

function StatusBadge({ value }) {
  return <span className={`res-status ${String(value || "").toLowerCase()}`}>{String(value || "Unknown").replaceAll("_", " ")}</span>;
}

const countDetail = (value, populated, empty) => Number(value || 0) > 0 ? populated : empty;

function ResourcingHeader({ pod, tab, setTab, refreshing, onRefresh }) {
  return <>
    <section className="res-hero">
      <div><span>ACCOUNT DELIVERY / TALENT LIFECYCLE</span><h1>Resourcing &amp; Onboarding</h1><p>Resource demand through candidate selection, onboarding, start, and project deployment.</p></div>
      <div className="res-hero-context"><small>ACTIVE SCOPE</small><strong>{pod === "All" ? "All Morgan Stanley pods" : pod}</strong><button onClick={onRefresh} disabled={refreshing}><RefreshCw />{refreshing ? "Refreshing" : "Refresh data"}</button></div>
    </section>
    <nav className="res-tabs" aria-label="Resourcing sections">{TABS.map((item) => <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>{item}</button>)}</nav>
  </>;
}

function Pulse({ metrics, onNavigate }) {
  const rows = [
    ["Open demand", metrics.open_demand, countDetail(metrics.critical_roles, `${metrics.critical_roles} critical`, "No critical roles"), "Open Roles", BriefcaseBusiness],
    ["Candidates", metrics.candidates, countDetail(metrics.with_ms, `${metrics.with_ms} with MS`, "None with MS"), "Candidates", UsersRound],
    ["Offers", metrics.offers, countDetail(metrics.pending_offers, `${metrics.pending_offers} pending`, "No pending offers"), "Candidates", CircleDot],
    ["Onboarding", metrics.onboarding, countDetail(metrics.blocked, `${metrics.blocked} blocked`, "No blockers"), "Onboarding", ShieldAlert],
    ["Starting <30d", metrics.starting_30_days, countDetail(metrics.starting_at_risk, `${metrics.starting_at_risk} at risk`, "No starts at risk"), "Onboarding", CalendarClock],
  ];
  return <section className="res-pulse">{rows.map(([label, value, detail, tab, Icon]) => <button key={label} onClick={() => onNavigate(tab)}><span><Icon /></span><small>{label}</small><strong>{value}</strong><em>{detail}</em><ChevronRight /></button>)}</section>;
}

function SecondaryMetric({ label, value, suffix = "", emptyText, risk = false }) {
  const available = value !== null && value !== undefined;
  return <article className={`${risk ? "risk" : ""} ${available ? "" : "empty"}`}><span><small>{label}</small>{!available && <em>{emptyText}</em>}</span><strong>{available ? `${value}${suffix}` : "—"}</strong></article>;
}

function Funnel({ rows }) {
  const maximum = Math.max(...rows.map((item) => item.count), 1);
  return <section className="res-card res-funnel"><header><div><span>END-TO-END FLOW</span><h2>Resource pipeline</h2></div><small>Live counts by current lifecycle state</small></header><div>{rows.map((item, index) => <React.Fragment key={item.stage}><article><span style={{ width: `${Math.max(22, item.count / maximum * 100)}%` }} /><strong>{item.count}</strong><small>{item.stage}</small></article>{index < rows.length - 1 && <ArrowRight />}</React.Fragment>)}</div></section>;
}

function CriticalAndStarting({ critical, starting, onOpen }) {
  return <div className="res-two-col">
    <section className="res-card res-critical"><header><div><span>LEADERSHIP QUEUE</span><h2>Critical / blocked</h2></div><b>{critical.length}</b></header><div>{critical.length ? critical.map((item) => <button key={`${item.type}-${item.id}`} onClick={() => onOpen(item)}><AlertTriangle /><span><strong>{item.headline}</strong><small>{item.detail || "Needs attention"}</small></span><em>{item.age_days}d</em><ChevronRight /></button>) : <p className="res-empty"><CheckCircle2 />No critical resourcing items.</p>}</div></section>
    <section className="res-card res-starting"><header><div><span>FORWARD LOOK</span><h2>Starting soon</h2></div><small>Next 30 days</small></header><div>{starting.length ? starting.map((item) => <button key={item.id} onClick={() => onOpen({ type: "ONBOARDING", id: item.id })}><time>{dateLabel(item.expected_start_date)}</time><span><strong>{item.name}</strong><small>{item.pod_id} · {item.business_unit} · {item.role}</small></span><StatusBadge value={item.risk === "START_AT_RISK" ? "At risk" : item.next_step?.step_label || "On track"} /><ChevronRight /></button>) : <p className="res-empty"><CalendarClock />No starts scheduled in the next 30 days.</p>}</div></section>
  </div>;
}

function DemandAndOwnership({ data }) {
  const metrics = data.metrics;
  return <div className="res-two-col compact">
    <section className="res-card res-demand"><header><div><span>CAPABILITY NEED</span><h2>Open resource demand</h2></div><small>Remaining headcount</small></header><div>{data.open_demand.length ? data.open_demand.map((item) => <div key={item.role}><span>{item.role}</span><i /><strong>{item.count}</strong></div>) : <p className="res-empty">No open capability demand.</p>}</div></section>
    <section className="res-card res-ownership"><header><div><span>NEXT ACTION</span><h2>Onboarding ownership</h2></div><small>{metrics.onboarding} active records</small></header><div><article className="ms"><small>Waiting on Morgan Stanley</small><strong>{metrics.waiting_on_ms}</strong></article><article className="capco"><small>Waiting on Capco</small><strong>{metrics.waiting_on_capco}</strong></article><article className="progress"><small>Progressing</small><strong>{metrics.progressing}</strong></article></div></section>
  </div>;
}

function Bottlenecks({ rows }) {
  return <section className="res-card res-bottlenecks"><header><div><span>SLA &amp; AGING</span><h2>Bottleneck analytics</h2></div><small>Calculated from stage timestamps</small></header><div>{rows.length ? rows.map((row) => <article key={row.stage}><div><strong>{row.stage}</strong><small>{row.waiting} currently waiting</small></div><span><i style={{ width: `${Math.min(100, row.average_days / Math.max(row.target_days, 1) * 62)}%` }} /></span><b className={row.status === "OVER_TARGET" ? "risk" : ""}>{row.average_days}d</b><em>Target {row.target_days}d</em></article>) : <p className="res-empty">Stage timing appears after candidates begin moving through the lifecycle.</p>}</div></section>;
}

function Overview({ data, setTab, onOpen }) {
  const m = data.metrics;
  return <div className="res-overview">
    <Pulse metrics={m} onNavigate={setTab} />
    <section className="res-secondary-metrics"><SecondaryMetric label="Avg time to fill" value={m.avg_time_to_fill} suffix=" days" emptyText="Available after a role is filled"/><SecondaryMetric label="Avg onboarding" value={m.avg_onboarding_days} suffix=" days" emptyText="Available after a completed start"/><SecondaryMetric label="Roles >30d" value={m.roles_over_30_days}/><SecondaryMetric label="Blocked" value={m.blocked} risk={m.blocked > 0}/></section>
    <Funnel rows={data.funnel} />
    <CriticalAndStarting critical={data.critical_items} starting={data.starting_soon} onOpen={onOpen} />
    <DemandAndOwnership data={data} />
    <Bottlenecks rows={data.analytics} />
  </div>;
}

function FilterBar({ query, setQuery, quick, setQuick, filters, setFilters, options, context, currentEmployeeId }) {
  const choose = (key) => (event) => setFilters({ ...filters, [key]: event.target.value });
  return <section className="res-filter-bar">
    <label className="res-search"><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={`Search ${context.toLowerCase()}…`} />{query && <button onClick={() => setQuery("")}><X /></button>}</label>
    <label><Filter />Priority<select value={filters.priority} onChange={(event) => setFilters({ ...filters, priority: event.target.value })}><option>All</option>{options.priorities.map((item) => <option key={item}>{item}</option>)}</select></label>
    <label>Business unit<select value={filters.unit} onChange={(event) => setFilters({ ...filters, unit: event.target.value })}><option>All</option>{options.units.map((item) => <option key={item}>{item}</option>)}</select></label>
    <div className="res-quick-filters"><SlidersHorizontal />{["Critical", "Blocked", "Waiting on MS", "Starting <30 Days", ">30 Days Open", "No Candidates"].map((item) => <button key={item} className={quick === item ? "active" : ""} onClick={() => setQuick(quick === item ? "" : item)}>{item}</button>)}</div>
    <details className="res-advanced-filters"><summary><SlidersHorizontal />More filters</summary><div><label>Division<select value={filters.division} onChange={choose("division")}><option>All</option>{options.divisions.map((item) => <option key={item}>{item}</option>)}</select></label><label>Project<select value={filters.project} onChange={choose("project")}><option>All</option>{options.projects.map((item) => <option key={item}>{item}</option>)}</select></label><label>Role<select value={filters.role} onChange={choose("role")}><option>All</option>{options.roles.map((item) => <option key={item}>{item}</option>)}</select></label><label>Skill<select value={filters.skill} onChange={choose("skill")}><option>All</option>{options.skills.map((item) => <option key={item}>{item}</option>)}</select></label><label>Location<select value={filters.location} onChange={choose("location")}><option>All</option>{options.locations.map((item) => <option key={item}>{item}</option>)}</select></label><label>Stage<select value={filters.stage} onChange={choose("stage")}><option>All</option>{options.stages.map((item) => <option key={item}>{item}</option>)}</select></label><label>Responsible<select value={filters.party} onChange={choose("party")}><option>All</option><option value="CAPCO">Capco</option><option value="MORGAN_STANLEY">Morgan Stanley</option></select></label><label>Target from<input type="date" value={filters.startFrom} onChange={choose("startFrom")} /></label><label>Target to<input type="date" value={filters.startTo} onChange={choose("startTo")} /></label><label>Minimum age<input min="0" type="number" value={filters.minAge} onChange={choose("minAge")} /></label>{currentEmployeeId && <button type="button" className={filters.mine === "yes" ? "active" : ""} onClick={() => setFilters({ ...filters, mine: filters.mine === "yes" ? "" : "yes" })}>My roles</button>}<button type="button" onClick={() => setFilters({ priority: "All", unit: "All", division: "All", project: "All", role: "All", skill: "All", location: "All", stage: "All", party: "All", startFrom: "", startTo: "", minAge: "", mine: "" })}>Clear advanced filters</button></div></details>
  </section>;
}

function OpenRoles({ rows, onOpen }) {
  return <section className="res-role-list">{rows.length ? rows.map((role) => <button className="res-role-card" key={role.id} onClick={() => onOpen(role)}>
    <span className={`res-priority ${role.priority.toLowerCase()}`}>{role.priority}</span><div className="res-role-main"><span>{role.pod_id} / {role.division} / {role.business_unit}</span><h3>{role.title}</h3><p>{role.project_name}</p><div className="res-skill-list">{role.required_skills.map((skill) => <i key={skill}>{skill}</i>)}</div></div>
    <div className="res-role-stat"><small>HEADCOUNT</small><strong>{role.filled_headcount} / {role.requested_headcount}</strong><em>{role.remaining_headcount} remaining</em></div>
    <div className="res-role-stat"><small>PIPELINE</small><strong>{role.candidate_count}</strong><em>candidates</em></div>
    <div className="res-role-stat"><small>TARGET START</small><strong>{dateLabel(role.target_start_date)}</strong><em>{role.location}</em></div>
    <div className={`res-role-stat ${role.age_days > 30 ? "risk" : ""}`}><small>ROLE AGE</small><strong>{role.age_days}d</strong><em>{role.owner_name}</em></div><ChevronRight />
  </button>) : <div className="res-empty large"><BriefcaseBusiness /><h3>No open roles match these filters</h3><p>Clear the quick filter or broaden the search.</p></div>}</section>;
}

function CandidateKanban({ rows, onOpen }) {
  return <section className="res-kanban">{PIPELINE.map(([stage, label]) => { const column = rows.filter((item) => candidateColumn(item.stage) === stage); return <article key={stage}><header><span>{label}</span><b>{column.length}</b></header><div>{column.map((candidate) => <button key={candidate.id} onClick={() => onOpen(candidate)} className={candidate.overdue ? "overdue" : ""}><div><span className="res-avatar">{initials(candidate.name)}</span><p><strong>{candidate.name}</strong><small>{candidate.role}</small></p></div><span className="res-match"><b>{candidate.match_score}%</b> match</span><small>{candidate.pod_id} · {candidate.business_unit}</small><footer><span>{candidate.stage_age_days} days in stage</span>{candidate.overdue ? <em>OVERDUE</em> : <ChevronRight />}</footer></button>)}</div>{!column.length && <p>No candidates</p>}</article>; })}</section>;
}

function CandidateArchive({ rows, onOpen }) {
  if (!rows.length) return null;
  return <section className="res-candidate-archive"><header><span>Closed candidates</span><b>{rows.length}</b><small>Rejected or withdrawn; retained for history and auditability</small></header><div>{rows.map((candidate) => <button key={candidate.id} onClick={() => onOpen(candidate)}><span className="res-avatar">{initials(candidate.name)}</span><span><b>{candidate.name}</b><small>{candidate.role} · {candidate.business_unit}</small></span><StatusBadge value={candidate.stage} /><ChevronRight /></button>)}</div></section>;
}

function StepIcon({ status }) {
  if (status === "COMPLETE") return <span className="step-icon complete"><Check /></span>;
  if (status === "BLOCKED") return <span className="step-icon blocked"><AlertTriangle /></span>;
  if (status === "IN_PROGRESS") return <span className="step-icon progress"><CircleDot /></span>;
  return <span className="step-icon pending">—</span>;
}

function OnboardingPipeline({ rows, onOpen }) {
  return <section className="res-onboarding-grid">{rows.map((record) => <button className={`res-onboarding-card ${record.blocked_steps ? "blocked" : ""}`} key={record.id} onClick={() => onOpen(record)}>
    <header><span className="res-avatar">{initials(record.name)}</span><div><h3>{record.name}</h3><p>{record.pod_id} / {record.business_unit} · {record.role}</p></div><StatusBadge value={record.risk === "START_AT_RISK" ? "Start at risk" : record.overall_status} /></header>
    <div className="res-progress-label"><span><b>{record.completed_steps}</b> / {record.total_steps} steps complete</span><strong>{Math.round(record.completed_steps / Math.max(record.total_steps, 1) * 100)}%</strong></div><span className="res-progress"><i style={{ width: `${record.completed_steps / Math.max(record.total_steps, 1) * 100}%` }} /></span>
    <div className="res-step-preview">{record.steps.slice(Math.max(0, record.completed_steps - 1), Math.min(record.total_steps, record.completed_steps + 3)).map((step) => <span key={step.id}><StepIcon status={step.status} /><b>{step.step_label}</b><em>{step.responsible_party === "MORGAN_STANLEY" ? "MS" : "Capco"}</em></span>)}</div>
    {record.blocker && <div className="res-blocker"><AlertTriangle /><span><small>BLOCKER</small><strong>{record.blocker}</strong></span></div>}
    <footer><span><small>EXPECTED START</small><b>{dateLabel(record.expected_start_date)}</b></span><span><small>NEXT OWNER</small><b>{record.owner_name || "Unassigned"}</b></span><ChevronRight /></footer>
  </button>)}</section>;
}

function OnboardingTable({ rows, onOpen }) {
  const stepLabels = rows[0]?.steps.map((step) => step.step_label) || [];
  return <div className="res-onboarding-table"><table><thead><tr><th>#</th><th>Resource</th><th>Pod / Business unit</th><th>Role</th>{stepLabels.map((label) => <th key={label} title={label}>{label.replace("Profile Worker", "PW").replace("Fingerprint Appointment Complete", "Fingerprint Appt").replace("Attestation / MSID Activation", "MSID")}</th>)}<th>Expected start</th><th>Status</th><th>Owner</th><th>Blocker</th></tr></thead><tbody>{rows.map((record, index) => <tr key={record.id} onClick={() => onOpen(record)}><td>{index + 1}</td><td><b>{record.name}</b></td><td>{record.pod_id}<small>{record.business_unit}</small></td><td>{record.role}</td>{record.steps.map((step) => <td key={step.id} title={`${step.step_label}: ${STEP_STATUS[step.status]}`}><StepIcon status={step.status} /></td>)}<td>{dateLabel(record.expected_start_date)}</td><td><StatusBadge value={record.overall_status} /></td><td>{record.owner_name || "—"}</td><td className="table-blocker">{record.blocker || "—"}</td></tr>)}</tbody></table></div>;
}

function PageControls({ total, page, setPage, pageSize = 20 }) {
  const pages = Math.max(1, Math.ceil(total / pageSize)); if (pages <= 1) return null;
  return <nav className="res-pagination" aria-label="Result pages"><button disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page + 1} of {pages} / {total} records</span><button disabled={page >= pages - 1} onClick={() => setPage(page + 1)}>Next</button></nav>;
}

function AuthoringModal({ title, onClose, children }) {
  return <div className="res-drawer-backdrop res-modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className="res-authoring-modal" role="dialog" aria-modal="true" aria-label={title}><header><div><span>RESOURCING WORKFLOW</span><h2>{title}</h2></div><button type="button" onClick={onClose} aria-label="Close"><X /></button></header>{children}</section></div>;
}

function RoleForm({ role, options, onClose, onSaved }) {
  const defaultProject = options.engagements?.[0];
  const [form, setForm] = useState(role ? { ...role, required_skills: (role.required_skills || []).join(", "), preferred_skills: (role.preferred_skills || []).join(", ") } : {
    engagement_id: defaultProject?.id || "", title: "", role: "", description: "", requested_headcount: 1,
    level: options.levels?.[0] || "Consultant", location: options.locations?.[0] || "New York", required_skills: "", preferred_skills: "",
    target_start_date: new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10), priority: "MEDIUM", status: "OPEN",
    request_owner_capco_employee_id: options.employees?.[0]?.id || "", client_stakeholder_id: options.stakeholders?.[0]?.id || "",
  });
  const [saving, setSaving] = useState(false); const [error, setError] = useState("");
  const set = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  const submit = async (event) => { event.preventDefault(); setSaving(true); setError(""); try {
    const project = options.engagements.find((item) => item.id === form.engagement_id) || defaultProject;
    const payload = { ...form, requested_headcount: Number(form.requested_headcount), required_skills: form.required_skills.split(",").map((value) => value.trim()).filter(Boolean), preferred_skills: form.preferred_skills.split(",").map((value) => value.trim()).filter(Boolean) };
    ["id", "project_name", "division", "business_unit", "owner_name", "client_name", "candidate_count", "filled_headcount", "remaining_headcount", "age_days", "created_at", "updated_at", "closed_at", "current_pipeline_stage", "candidates"].forEach((key) => delete payload[key]);
    if (!role) Object.assign(payload, { pod_id: project.pod_id, division_id: project.division_id, business_unit_id: project.business_unit_id });
    else { delete payload.engagement_id; delete payload.pod_id; delete payload.division_id; delete payload.business_unit_id; payload.expected_updated_at = role.updated_at; }
    onSaved(role ? await api.updateResourceRequirement(role.id, payload) : await api.createResourceRequirement(payload));
  } catch (requestError) { setError(requestError.message); } finally { setSaving(false); } };
  return <AuthoringModal title={role ? "Edit resource requirement" : "Create resource requirement"} onClose={onClose}><form className="res-authoring-form" onSubmit={submit}>
    {!role && <label className="wide">Project<select required value={form.engagement_id} onChange={(event) => set("engagement_id", event.target.value)}>{options.engagements.map((item) => <option key={item.id} value={item.id}>{item.pod_id} / {item.business_unit} / {item.name}</option>)}</select></label>}
    <label className="wide">Requirement title<input required value={form.title} onChange={(event) => set("title", event.target.value)} /></label><label>Role<input required value={form.role} onChange={(event) => set("role", event.target.value)} /></label><label>Headcount<input required min="1" type="number" value={form.requested_headcount} onChange={(event) => set("requested_headcount", event.target.value)} /></label>
    <label>Level<input required value={form.level} onChange={(event) => set("level", event.target.value)} /></label><label>Location<input required value={form.location} onChange={(event) => set("location", event.target.value)} /></label><label>Target start<input required type="date" value={String(form.target_start_date).slice(0, 10)} onChange={(event) => set("target_start_date", event.target.value)} /></label><label>Priority<select value={form.priority} onChange={(event) => set("priority", event.target.value)}>{options.priorities.map((item) => <option key={item}>{item}</option>)}</select></label>
    <label className="wide">Required skills<input value={form.required_skills} onChange={(event) => set("required_skills", event.target.value)} placeholder="Python, AWS, Data Engineering" /></label><label className="wide">Preferred skills<input value={form.preferred_skills} onChange={(event) => set("preferred_skills", event.target.value)} /></label>
    <label>Capco owner<select required value={form.request_owner_capco_employee_id} onChange={(event) => set("request_owner_capco_employee_id", event.target.value)}>{options.employees.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>MS stakeholder<select required value={form.client_stakeholder_id} onChange={(event) => set("client_stakeholder_id", event.target.value)}>{options.stakeholders.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
    <label className="wide">Description<textarea rows="3" value={form.description} onChange={(event) => set("description", event.target.value)} /></label>{error && <p className="form-error wide" role="alert">{error}</p>}<footer><button type="button" onClick={onClose}>Cancel</button><button className="primary" disabled={saving}><Save />{saving ? "Saving..." : role ? "Save changes" : "Create role"}</button></footer>
  </form></AuthoringModal>;
}

function CandidateForm({ options, requirements, onClose, onSaved }) {
  const firstRequirement = requirements[0];
  const [form, setForm] = useState({ resource_requirement_id: firstRequirement?.id || "", candidate_type: "EXTERNAL", first_name: "", last_name: "", email: "", level: firstRequirement?.level || "Consultant", location: firstRequirement?.location || "New York", skills: "", stage: "IDENTIFIED", capco_reviewer_id: firstRequirement?.request_owner_capco_employee_id || options.employees?.[0]?.id || "", ms_reviewer_stakeholder_id: firstRequirement?.client_stakeholder_id || "", expected_start_date: "", match_score: 70 });
  const [saving, setSaving] = useState(false); const [error, setError] = useState(""); const set = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  const requirementChanged = (id) => { const item = requirements.find((row) => row.id === id); setForm((current) => ({ ...current, resource_requirement_id: id, level: item?.level || current.level, location: item?.location || current.location, capco_reviewer_id: item?.request_owner_capco_employee_id || current.capco_reviewer_id, ms_reviewer_stakeholder_id: item?.client_stakeholder_id || current.ms_reviewer_stakeholder_id })); };
  const submit = async (event) => { event.preventDefault(); setSaving(true); setError(""); try { const payload = { ...form, skills: form.skills.split(",").map((value) => value.trim()).filter(Boolean), match_score: Number(form.match_score), expected_start_date: form.expected_start_date || null, email: form.email || null, ms_reviewer_stakeholder_id: form.ms_reviewer_stakeholder_id || null }; onSaved(await api.createCandidate(payload)); } catch (requestError) { setError(requestError.message); } finally { setSaving(false); } };
  return <AuthoringModal title="Add candidate" onClose={onClose}><form className="res-authoring-form" onSubmit={submit}><label className="wide">Resource requirement<select required value={form.resource_requirement_id} onChange={(event) => requirementChanged(event.target.value)}>{requirements.map((item) => <option key={item.id} value={item.id}>{item.pod_id} / {item.title}</option>)}</select></label><label>First name<input required value={form.first_name} onChange={(event) => set("first_name", event.target.value)} /></label><label>Last name<input required value={form.last_name} onChange={(event) => set("last_name", event.target.value)} /></label><label>Email<input type="email" value={form.email} onChange={(event) => set("email", event.target.value)} /></label><label>Candidate type<select value={form.candidate_type} onChange={(event) => set("candidate_type", event.target.value)}><option value="EXTERNAL">External</option><option value="INTERNAL_CAPCO">Internal Capco</option></select></label><label>Level<input required value={form.level} onChange={(event) => set("level", event.target.value)} /></label><label>Location<input required value={form.location} onChange={(event) => set("location", event.target.value)} /></label><label className="wide">Skills<input value={form.skills} onChange={(event) => set("skills", event.target.value)} placeholder="Python, AWS" /></label><label>Match score<input type="number" min="0" max="100" value={form.match_score} onChange={(event) => set("match_score", event.target.value)} /></label><label>Expected start<input type="date" value={form.expected_start_date} onChange={(event) => set("expected_start_date", event.target.value)} /></label><label>Capco reviewer<select value={form.capco_reviewer_id} onChange={(event) => set("capco_reviewer_id", event.target.value)}>{options.employees.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>MS reviewer<select value={form.ms_reviewer_stakeholder_id} onChange={(event) => set("ms_reviewer_stakeholder_id", event.target.value)}><option value="">Unassigned</option>{options.stakeholders.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>{error && <p className="form-error wide" role="alert">{error}</p>}<footer><button type="button" onClick={onClose}>Cancel</button><button className="primary" disabled={saving}><Save />{saving ? "Saving..." : "Add candidate"}</button></footer></form></AuthoringModal>;
}

function CandidateActionForm({ mode, candidates, options, canManageCommercial, onClose, onSaved }) {
  const [candidateId, setCandidateId] = useState(candidates[0]?.id || "");
  const [form, setForm] = useState(mode === "interview" ? { interview_round: 1, scheduled_at: "", interview_type: "Video", ms_interviewer_stakeholder_ids: [], capco_attendee_ids: [], status: "SCHEDULED", feedback: "", recommendation: "" } : { proposed_rate: "", agreed_rate: "", rate_currency: "USD", offer_status: "OFFER_PENDING", notes: "" });
  const [saving, setSaving] = useState(false); const [error, setError] = useState(""); const set = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  const [existingOffer, setExistingOffer] = useState(null);
  useEffect(() => { if (mode !== "offer" || !candidateId || !canManageCommercial) return; let active = true; setExistingOffer(null); api.getOffer(candidateId).then((offer) => { if (active) { setExistingOffer(offer); setForm({ proposed_rate: offer.proposed_rate ?? "", agreed_rate: offer.agreed_rate ?? "", rate_currency: offer.rate_currency || "USD", offer_status: offer.offer_status, notes: offer.notes || "" }); } }).catch(() => {}); return () => { active = false; }; }, [mode, candidateId, canManageCommercial]);
  const submit = async (event) => { event.preventDefault(); setSaving(true); setError(""); try { let payload;
    if (mode === "interview") payload = { ...form, interview_round: Number(form.interview_round), scheduled_at: new Date(form.scheduled_at).toISOString(), recommendation: form.recommendation || null };
    else payload = { ...form, proposed_rate: form.proposed_rate === "" ? null : Number(form.proposed_rate), agreed_rate: form.agreed_rate === "" ? null : Number(form.agreed_rate) };
    await (mode === "interview" ? api.createInterview(candidateId, payload) : existingOffer ? api.updateOffer(candidateId, { ...payload, expected_updated_at: existingOffer.updated_at }) : api.createOffer(candidateId, payload)); onSaved();
  } catch (requestError) { setError(requestError.message); } finally { setSaving(false); } };
  return <AuthoringModal title={mode === "interview" ? "Schedule interview" : "Create or update offer"} onClose={onClose}><form className="res-authoring-form" onSubmit={submit}><label className="wide">Candidate<select value={candidateId} onChange={(event) => setCandidateId(event.target.value)}>{candidates.map((item) => <option key={item.id} value={item.id}>{item.name} / {item.requirement_title}</option>)}</select></label>{mode === "interview" ? <><label>Round<input min="1" type="number" value={form.interview_round} onChange={(event) => set("interview_round", event.target.value)} /></label><label>Date and time<input required type="datetime-local" value={form.scheduled_at} onChange={(event) => set("scheduled_at", event.target.value)} /></label><label>Format<select value={form.interview_type} onChange={(event) => set("interview_type", event.target.value)}><option>Video</option><option>In person</option><option>Phone</option></select></label><label>Status<select value={form.status} onChange={(event) => set("status", event.target.value)}><option>SCHEDULED</option><option>COMPLETED</option><option>CANCELLED</option></select></label><label>MS interviewer<select value={form.ms_interviewer_stakeholder_ids[0] || ""} onChange={(event) => set("ms_interviewer_stakeholder_ids", event.target.value ? [event.target.value] : [])}><option value="">Unassigned</option>{options.stakeholders.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>Capco attendee<select value={form.capco_attendee_ids[0] || ""} onChange={(event) => set("capco_attendee_ids", event.target.value ? [event.target.value] : [])}><option value="">Unassigned</option>{options.employees.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label className="wide">Feedback<textarea rows="3" value={form.feedback} onChange={(event) => set("feedback", event.target.value)} /></label></> : canManageCommercial ? <><label>Proposed rate<input type="number" min="0" step="0.01" value={form.proposed_rate} onChange={(event) => set("proposed_rate", event.target.value)} /></label><label>Agreed rate<input type="number" min="0" step="0.01" value={form.agreed_rate} onChange={(event) => set("agreed_rate", event.target.value)} /></label><label>Currency<input maxLength="3" value={form.rate_currency} onChange={(event) => set("rate_currency", event.target.value.toUpperCase())} /></label><label>Status<select value={form.offer_status} onChange={(event) => set("offer_status", event.target.value)}><option>OFFER_PENDING</option><option>RATE_NEGOTIATION</option><option>OFFER_ACCEPTED</option><option>OFFER_DECLINED</option></select></label><label className="wide">Notes<textarea rows="3" value={form.notes} onChange={(event) => set("notes", event.target.value)} /></label></> : <p className="form-error wide">Commercial offer access is restricted to Account Managers and Account Admins.</p>}{error && <p className="form-error wide" role="alert">{error}</p>}<footer><button type="button" onClick={onClose}>Cancel</button><button className="primary" disabled={saving || (mode === "offer" && !canManageCommercial)}><Save />{saving ? "Saving..." : "Save"}</button></footer></form></AuthoringModal>;
}

function CandidateOwnershipForm({ candidates, options, onClose, onSaved }) {
  const first = candidates[0]; const [candidateId, setCandidateId] = useState(first?.id || ""); const current = candidates.find((item) => item.id === candidateId) || first;
  const [capco, setCapco] = useState(first?.capco_reviewer_id || ""); const [ms, setMs] = useState(first?.ms_reviewer_stakeholder_id || ""); const [start, setStart] = useState(first?.expected_start_date ? String(first.expected_start_date).slice(0, 10) : ""); const [saving, setSaving] = useState(false); const [error, setError] = useState("");
  const chooseCandidate = (id) => { const item = candidates.find((row) => row.id === id); setCandidateId(id); setCapco(item?.capco_reviewer_id || ""); setMs(item?.ms_reviewer_stakeholder_id || ""); setStart(item?.expected_start_date ? String(item.expected_start_date).slice(0, 10) : ""); };
  const submit = async (event) => { event.preventDefault(); setSaving(true); setError(""); try { await api.updateCandidate(candidateId, { capco_reviewer_id: capco, ms_reviewer_stakeholder_id: ms || null, expected_start_date: start || null, expected_updated_at: current.updated_at, note: "Candidate ownership reassigned." }); onSaved(); } catch (requestError) { setError(requestError.message); } finally { setSaving(false); } };
  return <AuthoringModal title="Reassign candidate ownership" onClose={onClose}><form className="res-authoring-form" onSubmit={submit}><label className="wide">Candidate<select value={candidateId} onChange={(event) => chooseCandidate(event.target.value)}>{candidates.map((item) => <option key={item.id} value={item.id}>{item.name} / {item.requirement_title}</option>)}</select></label><label>Capco reviewer<select required value={capco} onChange={(event) => setCapco(event.target.value)}>{options.employees.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>MS reviewer<select value={ms} onChange={(event) => setMs(event.target.value)}><option value="">Unassigned</option>{options.stakeholders.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>Expected start<input type="date" value={start} onChange={(event) => setStart(event.target.value)} /></label>{error && <p className="form-error wide">{error}</p>}<footer><button type="button" onClick={onClose}>Cancel</button><button className="primary" disabled={saving}><Save />{saving ? "Saving..." : "Save ownership"}</button></footer></form></AuthoringModal>;
}

function RoleDrawer({ role, onClose, onCandidate }) {
  return <Drawer onClose={onClose} label="RESOURCE REQUIREMENT" title={role.title}><div className="res-drawer-context"><span>{role.pod_id} / {role.division} / {role.business_unit}</span><strong>{role.project_name}</strong></div><dl className="res-detail-grid"><div><dt>Requested</dt><dd>{role.requested_headcount}</dd></div><div><dt>Filled</dt><dd>{role.filled_headcount}</dd></div><div><dt>Remaining</dt><dd>{role.remaining_headcount}</dd></div><div><dt>Role age</dt><dd>{role.age_days} days</dd></div><div><dt>Level</dt><dd>{role.level}</dd></div><div><dt>Location</dt><dd>{role.location}</dd></div><div><dt>Target start</dt><dd>{dateLabel(role.target_start_date)}</dd></div><div><dt>Priority</dt><dd><StatusBadge value={role.priority} /></dd></div></dl><h3>Required skills</h3><div className="res-skill-list">{role.required_skills.map((skill) => <i key={skill}>{skill}</i>)}</div><h3>Ownership</h3><dl className="res-lines"><dt>Capco owner</dt><dd>{role.owner_name}</dd><dt>Client stakeholder</dt><dd>{role.client_name}</dd></dl><h3>Candidate pipeline</h3><div className="res-drawer-list">{role.candidates?.length ? role.candidates.map((candidate) => <button key={candidate.id} onClick={() => onCandidate(candidate)}><span className="res-avatar">{initials(candidate.name)}</span><span><b>{candidate.name}</b><small>{STAGE_LABELS[candidate.stage]}</small></span><em>{candidate.match_score}%</em><ChevronRight /></button>) : <p>No active candidates.</p>}</div></Drawer>;
}

function Drawer({ onClose, label, title, children }) {
  return <div className="res-drawer-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><aside className="res-drawer" role="dialog" aria-modal="true" aria-label={title}><header><div><span>{label}</span><h2>{title}</h2></div><button onClick={onClose} aria-label="Close"><X /></button></header><div>{children}</div></aside></div>;
}

function CandidateDrawer({ candidate, canWrite, onClose, onSaved }) {
  const [tab, setTab] = useState("Overview");
  const [draftStage, setDraftStage] = useState(candidate.stage);
  const [saving, setSaving] = useState(false);
  const tabs = ["Overview", "Timeline", "Interviews", "Offer", "Onboarding"];
  const saveStage = async () => {
    if (!canWrite || draftStage === candidate.stage) return;
    if (!window.confirm(`Move ${candidate.name} to ${STAGE_LABELS[draftStage]}? This updates the canonical pipeline.`)) return;
    setSaving(true); try { onSaved(await api.updateCandidate(candidate.id, { stage: draftStage, note: "Stage updated from the candidate pipeline." })); } finally { setSaving(false); }
  };
  return <Drawer onClose={onClose} label="CANDIDATE" title={candidate.name}><div className="res-drawer-context"><span>{candidate.level} · {candidate.location}</span><strong>{candidate.requirement_title}</strong><small>{candidate.pod_id} / {candidate.business_unit} · {candidate.project_name}</small></div><nav className="res-drawer-tabs">{tabs.map((item) => <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>{item}</button>)}</nav>
    {tab === "Overview" && <><div className="res-stage-editor"><label>Current stage<select disabled={!canWrite} value={draftStage} onChange={(event) => setDraftStage(event.target.value)}>{Object.entries(STAGE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><button disabled={saving || draftStage === candidate.stage} onClick={saveStage}>{saving ? "Saving…" : "Save stage"}</button></div><dl className="res-detail-grid"><div><dt>Skill match</dt><dd>{candidate.match_score}%</dd></div><div><dt>Days in stage</dt><dd>{candidate.stage_age_days}</dd></div><div><dt>Candidate type</dt><dd>{candidate.candidate_type.replaceAll("_", " ")}</dd></div><div><dt>Expected start</dt><dd>{dateLabel(candidate.expected_start_date)}</dd></div></dl><h3>Skills</h3><div className="res-skill-list">{candidate.skills.map((skill) => <i key={skill}>{skill}</i>)}</div><h3>Next action</h3><div className="res-next-action"><ArrowRight /><span><strong>{candidate.stage === "MS_REVIEW" ? "Morgan Stanley candidate decision" : candidate.stage === "OFFER" ? "Rate agreement / candidate acceptance" : "Advance candidate pipeline"}</strong><small>Owner · {candidate.stage === "MS_REVIEW" ? candidate.ms_owner_name : candidate.owner_name}</small></span></div></>}
    {tab === "Timeline" && <div className="res-timeline">{candidate.timeline.map((item) => <article key={item.id}><i /><time>{longDate(item.entered_at)}</time><div><strong>{STAGE_LABELS[item.stage] || item.stage}</strong><small>{item.note || "Lifecycle stage entered"}</small></div></article>)}</div>}
    {tab === "Interviews" && <div className="res-interviews">{candidate.interviews.length ? candidate.interviews.map((item) => <article key={item.id}><CalendarClock /><div><strong>Round {item.interview_round} · {item.interview_type}</strong><small>{longDate(item.scheduled_at)} · {item.status}</small><p>{item.feedback || "Feedback pending."}</p>{item.recommendation && <StatusBadge value={item.recommendation} />}</div></article>) : <p className="res-empty">No interviews scheduled.</p>}</div>}
    {tab === "Offer" && (candidate.offer ? <div className="res-offer"><StatusBadge value={candidate.offer.offer_status} /><dl className="res-lines"><dt>Offer date</dt><dd>{dateLabel(candidate.offer.offer_date)}</dd><dt>Accepted date</dt><dd>{dateLabel(candidate.offer.accepted_date)}</dd><dt>Currency</dt><dd>{candidate.offer.rate_currency}</dd></dl><p>Sensitive rate details are intentionally excluded from this operating summary.</p></div> : <p className="res-empty">No offer record has been created.</p>)}
    {tab === "Onboarding" && (candidate.onboarding ? <OnboardingSummary record={candidate.onboarding} onOpen={() => {}} /> : <p className="res-empty">Onboarding begins automatically when the offer is accepted and the candidate is selected.</p>)}
  </Drawer>;
}

function OnboardingSummary({ record }) {
  return <div className="res-onboarding-summary"><div className="res-progress-label"><span>{record.completed_steps} / {record.total_steps} steps complete</span><strong>{Math.round(record.completed_steps / record.total_steps * 100)}%</strong></div><span className="res-progress"><i style={{ width: `${record.completed_steps / record.total_steps * 100}%` }} /></span><dl className="res-lines"><dt>Expected start</dt><dd>{dateLabel(record.expected_start_date)}</dd><dt>Risk status</dt><dd><StatusBadge value={record.risk} /></dd><dt>Remaining steps</dt><dd>{record.risk_explanation.remaining_steps}</dd><dt>Historical duration</dt><dd>{record.risk_explanation.historical_average_remaining_days} days</dd></dl></div>;
}

function LegacyOnboardingDrawer({ record, canWrite, onClose, onSaved }) {
  const [saving, setSaving] = useState("");
  const updateStep = async (step, status) => {
    if (!canWrite) return;
    if (status === "BLOCKED" && !window.confirm(`Mark ${step.step_label} as blocked?`)) return;
    setSaving(step.id); try { onSaved(await api.updateOnboardingStep(record.id, step.id, { status, ...(status === "BLOCKED" ? { blocker_reason: step.blocker_reason || "Operational blocker requires resolution" } : {}) })); } finally { setSaving(""); }
  };
  return <Drawer onClose={onClose} label="MORGAN STANLEY ONBOARDING" title={record.name}><div className="res-drawer-context"><span>{record.pod_id} / {record.business_unit}</span><strong>{record.role}</strong><small>{record.project_name}</small></div><OnboardingSummary record={record} />
    {record.blocker && <div className="res-blocker drawer"><AlertTriangle /><span><small>ACTIVE BLOCKER</small><strong>{record.blocker}</strong><p>{record.steps.find((step) => step.status === "BLOCKED")?.notes}</p></span></div>}
    <h3>Workflow steps</h3><div className="res-step-list">{record.steps.map((step) => <article key={step.id}><StepIcon status={step.status} /><div><strong>{step.step_label}</strong><small>{step.responsible_party === "MORGAN_STANLEY" ? "Morgan Stanley" : "Capco"} · {step.owner_name || "Owner not assigned"}</small>{step.blocker_reason && <p>{step.blocker_reason} · {step.days_blocked} days blocked</p>}</div><select aria-label={`Status for ${step.step_label}`} disabled={!canWrite || saving === step.id} value={step.status} onChange={(event) => updateStep(step, event.target.value)}>{Object.entries(STEP_STATUS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></article>)}</div>
  </Drawer>;
}

function OnboardingDrawer({ record, canWrite, options, onClose, onSaved }) {
  const [drafts, setDrafts] = useState(() => Object.fromEntries(record.steps.map((step) => [step.id, { status: step.status, responsible_party: step.responsible_party, owner_id: step.owner_id || "", blocker_reason: step.blocker_reason || "", notes: step.notes || "", target_completion_date: step.target_completion_date ? String(step.target_completion_date).slice(0, 10) : "" }])));
  const [saving, setSaving] = useState(""); const [starting, setStarting] = useState(false); const [error, setError] = useState("");
  const setDraft = (id, key, value) => setDrafts((current) => ({ ...current, [id]: { ...current[id], [key]: value, ...(key === "responsible_party" ? { owner_id: "" } : {}) } }));
  const saveStep = async (step) => { setSaving(step.id); setError(""); try { const draft = drafts[step.id]; onSaved(await api.updateOnboardingStep(record.id, step.id, { ...draft, owner_id: draft.owner_id || null, target_completion_date: draft.target_completion_date || null, blocker_reason: draft.status === "BLOCKED" ? draft.blocker_reason || "Operational blocker requires resolution" : null, expected_updated_at: step.updated_at })); } catch (requestError) { setError(requestError.message); } finally { setSaving(""); } };
  const start = async () => { if (!window.confirm(`Confirm ${record.name} has started? This creates the employee assignment and completes onboarding.`)) return; setStarting(true); setError(""); try { const result = await api.startOnboardingCandidate(record.id); onSaved(result.onboarding); } catch (requestError) { setError(requestError.message); } finally { setStarting(false); } };
  return <Drawer onClose={onClose} label="MORGAN STANLEY ONBOARDING" title={record.name}><div className="res-drawer-context"><span>{record.pod_id} / {record.business_unit}</span><strong>{record.role}</strong><small>{record.project_name}</small></div><OnboardingSummary record={record} />{record.ready_to_start && canWrite && <button className="res-start-action" disabled={starting} onClick={start}><CheckCircle2 />{starting ? "Starting..." : "Confirm start & create assignment"}</button>}{record.blocker && <div className="res-blocker drawer"><AlertTriangle /><span><small>ACTIVE BLOCKER</small><strong>{record.blocker}</strong></span></div>}{error && <p className="form-error" role="alert">{error}</p>}<h3>Workflow steps</h3><div className="res-step-edit-list">{record.steps.map((step) => { const draft = drafts[step.id]; const owners = draft.responsible_party === "CAPCO" ? options.employees : options.stakeholders; return <article key={step.id}><StepIcon status={draft.status} /><div className="step-editor-main"><strong>{step.step_label}</strong><div><label>Responsible<select disabled={!canWrite} value={draft.responsible_party} onChange={(event) => setDraft(step.id, "responsible_party", event.target.value)}><option value="CAPCO">Capco</option><option value="MORGAN_STANLEY">Morgan Stanley</option></select></label><label>Owner<select disabled={!canWrite} value={draft.owner_id} onChange={(event) => setDraft(step.id, "owner_id", event.target.value)}><option value="">Unassigned</option>{owners.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>Status<select disabled={!canWrite} value={draft.status} onChange={(event) => setDraft(step.id, "status", event.target.value)}>{Object.entries(STEP_STATUS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Target<input disabled={!canWrite} type="date" value={draft.target_completion_date} onChange={(event) => setDraft(step.id, "target_completion_date", event.target.value)} /></label></div>{draft.status === "BLOCKED" && <div className="step-blocker-editor"><input disabled={!canWrite} value={draft.blocker_reason} onChange={(event) => setDraft(step.id, "blocker_reason", event.target.value)} placeholder="Blocker reason" /><textarea disabled={!canWrite} value={draft.notes} onChange={(event) => setDraft(step.id, "notes", event.target.value)} placeholder="Resolution notes and next action" /></div>}</div>{canWrite && <button className="step-save" disabled={saving === step.id} onClick={() => saveStep(step)}><Save />{saving === step.id ? "Saving" : "Save"}</button>}</article>; })}</div>{record.blocker_history?.length > 0 && <><h3>Blocker history</h3><div className="res-timeline">{record.blocker_history.map((item) => <article key={item.id}><i /><time>{longDate(item.occurred_at)}</time><div><strong>{item.headline}</strong><small>{item.detail}</small></div></article>)}</div></>}</Drawer>;
}

export default function ResourcingView({ pod = "All", canWrite = true, canManageCommercial = false, currentEmployeeId = "" }) {
  const queryTab = new URLSearchParams(window.location.search).get("resourcingTab");
  const [tab, setTabState] = useState(TABS.includes(queryTab) ? queryTab : "Overview");
  const [state, setState] = useState("loading");
  const [data, setData] = useState({ overview: null, roles: [], candidates: [], onboarding: [], options: { engagements: [], employees: [], stakeholders: [], priorities: ["CRITICAL", "HIGH", "MEDIUM", "LOW"], levels: [], locations: [] } });
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const [query, setQuery] = useState("");
  const [quick, setQuick] = useState("");
  const [filters, setFilters] = useState({ priority: "All", unit: "All", division: "All", project: "All", role: "All", skill: "All", location: "All", stage: "All", party: "All", startFrom: "", startTo: "", minAge: "", mine: "" });
  const [onboardingMode, setOnboardingMode] = useState("Pipeline");
  const [drawer, setDrawer] = useState(null);
  const [authoring, setAuthoring] = useState(null);
  const [sort, setSort] = useState({ key: "", direction: 1 });
  const [page, setPage] = useState(0); const pageSize = 20;
  const setTab = (value) => { setTabState(value); setQuery(""); setQuick(""); setPage(0); };
  const load = () => {
    let active = true; setState("loading"); setError("");
    Promise.all([api.getResourcingOverview(pod), api.getResourceRequirements(pod), api.getCandidates(pod), api.getOnboarding(pod), api.getResourcingOptions ? api.getResourcingOptions(pod) : Promise.resolve(data.options)])
      .then(([overview, roles, candidates, onboarding, options]) => { if (active) { setData({ overview, roles, candidates, onboarding, options }); setState("ready"); } })
      .catch((requestError) => { if (active) { setState("error"); setError(requestError.message || "Resourcing data could not be loaded."); } });
    return () => { active = false; };
  };
  useEffect(load, [pod, reload]);
  useEffect(() => { const params = new URLSearchParams(window.location.search); params.set("resourcingTab", tab); window.history.replaceState({}, "", `${window.location.pathname}?${params}${window.location.hash}`); }, [tab]);
  const options = useMemo(() => ({ priorities: [...new Set(data.roles.map((item) => item.priority))].sort(), units: [...new Set(data.roles.map((item) => item.business_unit))].sort(), divisions: [...new Set(data.roles.map((item) => item.division))].sort(), projects: [...new Set(data.roles.map((item) => item.project_name))].sort(), roles: [...new Set(data.roles.map((item) => item.role))].sort(), skills: [...new Set(data.roles.flatMap((item) => item.required_skills || []))].sort(), locations: [...new Set(data.roles.map((item) => item.location))].sort(), stages: [...new Set(data.candidates.map((item) => item.stage))].sort() }), [data.roles, data.candidates]);
  const filterText = (row) => [row.name, row.title, row.role, row.project_name, row.business_unit, row.location, ...(row.required_skills || row.skills || [])].filter(Boolean).join(" ").toLowerCase().includes(query.trim().toLowerCase());
  const matchesAdvanced = (row) => (filters.unit === "All" || row.business_unit === filters.unit) && (filters.division === "All" || row.division === filters.division) && (filters.project === "All" || row.project_name === filters.project) && (filters.role === "All" || row.role === filters.role) && (filters.location === "All" || row.location === filters.location) && (filters.stage === "All" || row.stage === filters.stage || row.overall_status === filters.stage) && (filters.party === "All" || row.responsible_party === filters.party) && (filters.skill === "All" || [...(row.required_skills || []), ...(row.skills || [])].includes(filters.skill)) && (!filters.startFrom || String(row.target_start_date || row.expected_start_date || "") >= filters.startFrom) && (!filters.startTo || String(row.target_start_date || row.expected_start_date || "") <= filters.startTo) && (!filters.minAge || Number(row.age_days || row.stage_age_days || 0) >= Number(filters.minAge)) && (filters.mine !== "yes" || row.request_owner_capco_employee_id === currentEmployeeId || row.capco_reviewer_id === currentEmployeeId);
  const sortRows = (rows) => !sort.key ? rows : [...rows].sort((left, right) => String(left[sort.key] ?? "").localeCompare(String(right[sort.key] ?? ""), undefined, { numeric: true }) * sort.direction);
  const isStartingSoon = (value) => { const days=Math.floor((parseBackendDate(value).getTime()-Date.now())/86400000); return Number.isFinite(days)&&days>=0&&days<30; };
  const roles = useMemo(() => sortRows(data.roles.filter((row) => filterText(row) && matchesAdvanced(row) && (filters.priority === "All" || row.priority === filters.priority) && (!quick || quick === "Critical" && row.priority === "CRITICAL" || quick === ">30 Days Open" && row.age_days > 30 || quick === "No Candidates" && row.candidate_count === 0 || quick === "Starting <30 Days" && isStartingSoon(row.target_start_date)))), [data.roles, query, filters, quick, sort]);
  const candidateRows = useMemo(() => sortRows(data.candidates.filter((row) => filterText(row) && matchesAdvanced(row) && !["REJECTED", "WITHDRAWN"].includes(row.stage) && (!quick || quick === "Waiting on MS" && ["SUBMITTED_TO_MS", "MS_REVIEW"].includes(row.stage)))), [data.candidates, query, filters, quick, sort]);
  const onboardingRows = useMemo(() => sortRows(data.onboarding.filter((row) => filterText(row) && matchesAdvanced(row) && (!quick || quick === "Blocked" && row.blocked_steps || quick === "Waiting on MS" && row.responsible_party === "MORGAN_STANLEY" || quick === "Starting <30 Days" && row.expected_start_date && isStartingSoon(row.expected_start_date)))), [data.onboarding, query, filters, quick, sort]);
  const visibleRows = tab === "Open Roles" ? roles : tab === "Candidates" ? candidateRows : onboardingRows;
  const pagedRows = visibleRows.slice(page * pageSize, (page + 1) * pageSize);
  useEffect(() => setPage(0), [query, quick, filters, sort]);
  const openDetail = async (type, summary, loader) => { try { setError(""); setDrawer({ type, data: await loader() }); } catch (requestError) { setError(requestError.message||"The full record could not be loaded. Retry from the list."); setDrawer(null); } };
  const openRole = (role) => openDetail("role", role, () => api.getResourceRequirement(role.id));
  const openCandidate = (candidate) => openDetail("candidate", candidate, () => api.getCandidate(candidate.id));
  const openOnboarding = (record) => openDetail("onboarding", record, () => api.getOnboardingRecord(record.id));
  const openCritical = (item) => item.type === "ROLE" ? openRole({ id: item.id }) : openOnboarding({ id: item.id });
  const handleSaved = (record) => { setDrawer({ type: record.steps ? "onboarding" : "candidate", data: record }); setReload((value) => value + 1); };
  const handleAuthored = () => { setAuthoring(null); setReload((value) => value + 1); };
  return <div className="resourcing-view"><ResourcingHeader pod={pod} tab={tab} setTab={setTab} refreshing={state === "loading"} onRefresh={() => setReload((value) => value + 1)} />
    <main className="res-content">{state === "loading" && !data.overview ? <div className="res-state"><span /><h2>Loading the connected staffing lifecycle</h2><p>Resolving demand, candidates, offers, onboarding, and project assignments…</p></div> : state === "error" ? <div className="res-state error"><AlertTriangle /><h2>Resourcing data unavailable</h2><p>{error}</p><button onClick={() => setReload((value) => value + 1)}>Retry</button></div> : <>
      {tab === "Overview" && <Overview data={data.overview} setTab={setTab} onOpen={openCritical} />}
      {tab !== "Overview" && <><div className="res-authoring-toolbar">{canWrite && tab === "Open Roles" && <button className="primary" onClick={() => setAuthoring({ type: "role" })}><Plus />New role</button>}{canWrite && tab === "Candidates" && <><button className="primary" onClick={() => setAuthoring({ type: "candidate" })}><Plus />Add candidate</button><button onClick={() => setAuthoring({ type: "ownership" })}><UserRound />Reassign owner</button><button onClick={() => setAuthoring({ type: "interview" })}><CalendarClock />Schedule interview</button>{canManageCommercial && <button onClick={() => setAuthoring({ type: "offer" })}><CircleDot />Manage offer</button>}</>}<label><ArrowUpDown />Sort<select value={sort.key} onChange={(event) => setSort({ ...sort, key: event.target.value })}><option value="">Default</option><option value="name">Name</option><option value="role">Role</option><option value="project_name">Project</option><option value="target_start_date">Target start</option><option value="expected_start_date">Expected start</option><option value="age_days">Age</option><option value="priority">Priority</option><option value="owner_name">Owner</option><option value="status">Status</option></select><button type="button" onClick={() => setSort({ ...sort, direction: sort.direction * -1 })}>{sort.direction === 1 ? "A-Z" : "Z-A"}</button></label></div><FilterBar query={query} setQuery={setQuery} quick={quick} setQuick={setQuick} filters={filters} setFilters={setFilters} options={options} context={tab} currentEmployeeId={currentEmployeeId} /></>}
      {tab === "Open Roles" && <OpenRoles rows={pagedRows} onOpen={openRole} />}
      {tab === "Candidates" && <><CandidateKanban rows={pagedRows} onOpen={openCandidate} /><CandidateArchive rows={data.candidates.filter((row) => ["REJECTED", "WITHDRAWN"].includes(row.stage) && filterText(row))} onOpen={openCandidate} /></>}
      {tab === "Onboarding" && <><div className="res-view-toggle"><button className={onboardingMode === "Pipeline" ? "active" : ""} onClick={() => setOnboardingMode("Pipeline")}><Columns3 />Pipeline view</button><button className={onboardingMode === "Table" ? "active" : ""} onClick={() => setOnboardingMode("Table")}><List />Table view</button><span>{onboardingRows.length} active records</span></div>{onboardingMode === "Pipeline" ? <OnboardingPipeline rows={pagedRows} onOpen={openOnboarding} /> : <OnboardingTable rows={pagedRows} onOpen={openOnboarding} />}</>}
      {tab !== "Overview" && <PageControls total={visibleRows.length} page={page} setPage={setPage} pageSize={pageSize} />}
    </>}</main>
    {drawer?.type === "role" && <RoleDrawer role={drawer.data} onClose={() => setDrawer(null)} onCandidate={(candidate) => openCandidate(candidate)} />}
    {drawer?.type === "role" && canWrite && <button className="res-floating-edit" onClick={() => { setAuthoring({ type: "role", role: drawer.data }); setDrawer(null); }}><Save />Edit requirement</button>}
    {drawer?.type === "candidate" && <CandidateDrawer candidate={drawer.data} canWrite={canWrite} onClose={() => setDrawer(null)} onSaved={handleSaved} />}
    {drawer?.type === "onboarding" && <OnboardingDrawer record={drawer.data} canWrite={canWrite} options={data.options} onClose={() => setDrawer(null)} onSaved={handleSaved} />}
    {authoring?.type === "role" && <RoleForm role={authoring.role} options={data.options} onClose={() => setAuthoring(null)} onSaved={handleAuthored} />}
    {authoring?.type === "candidate" && <CandidateForm options={data.options} requirements={data.roles.filter((item) => !["FILLED", "CANCELLED"].includes(item.status))} onClose={() => setAuthoring(null)} onSaved={handleAuthored} />}
    {["interview", "offer"].includes(authoring?.type) && <CandidateActionForm mode={authoring.type} candidates={data.candidates.filter((item) => !["REJECTED", "WITHDRAWN"].includes(item.stage))} options={data.options} canManageCommercial={canManageCommercial} onClose={() => setAuthoring(null)} onSaved={handleAuthored} />}
    {authoring?.type === "ownership" && <CandidateOwnershipForm candidates={data.candidates.filter((item) => !["REJECTED", "WITHDRAWN"].includes(item.stage))} options={data.options} onClose={() => setAuthoring(null)} onSaved={handleAuthored} />}
  </div>;
}
