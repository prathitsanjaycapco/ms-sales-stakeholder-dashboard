import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle, ArrowRight, BriefcaseBusiness, CalendarDays, CheckCircle2,
  ChevronLeft, ChevronRight, CircleDollarSign, ExternalLink, Flag,
  Layers3, RefreshCw, Search, Sparkles, TrendingUp, UsersRound, X,
} from "lucide-react";
import { api } from "./api";

const PODS = ["All", "ISG", "Wealth Management", "MSIM"];
const POD_LABELS = { All: "ALL PODS", ISG: "ISG", "Wealth Management": "WEALTH", MSIM: "MSIM" };
const ACTIVITY_LABELS = {
  meeting: "Client meeting", event: "Account event", task: "Deliverable",
  milestone: "Milestone", engagement_milestone: "Milestone", assignment: "Project focus",
};

const money = (value) => value === null || value === undefined
  ? "Unavailable"
  : new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 }).format(value);
const dateFromIso = (value) => new Date(`${value}T12:00:00`);
const isoDate = (value) => {
  const date = new Date(value);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
};
const mondayFor = (value = new Date()) => {
  const date = new Date(value);
  date.setHours(12, 0, 0, 0);
  date.setDate(date.getDate() - ((date.getDay() + 6) % 7));
  return isoDate(date);
};
const addDays = (value, count) => {
  const date = dateFromIso(value);
  date.setDate(date.getDate() + count);
  return isoDate(date);
};
const shortDate = (value) => value ? dateFromIso(value).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "Not scheduled";
const dayName = (value) => dateFromIso(value).toLocaleDateString("en-US", { weekday: "short" });
const initials = (name = "") => name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
const healthLabel = { GREEN: "On track", AMBER: "Watch", RED: "At risk" };

function SectionHeading({ eyebrow, title, note, action }) {
  return <header className="weekly-section-heading">
    <div><span>{eyebrow}</span><h2>{title}</h2>{note && <p>{note}</p>}</div>
    {action}
  </header>;
}

function WeeklyHero({ meta, weekStart, setWeekStart, viewMode, setViewMode, selectedPod, setSelectedPod }) {
  const currentWeek = mondayFor();
  const label = meta ? `${shortDate(meta.weekStart)} - ${shortDate(meta.weekEnd)}` : `${shortDate(weekStart)} - ${shortDate(addDays(weekStart, 6))}`;
  return <section className="weekly-hero">
    <div className="weekly-hero-copy">
      <span>ACCOUNT LEADERSHIP / WEEKLY OPERATING RHYTHM</span>
      <h1>Executive Weekly Operating View</h1>
      <p>What the Capco team is doing, what needs leadership attention, and what is coming next.</p>
    </div>
    <div className="weekly-controls">
      <div className="weekly-range-control">
        <button onClick={() => setWeekStart(addDays(weekStart, -7))} aria-label="Previous week"><ChevronLeft /></button>
        <div><small>OPERATING WEEK</small><strong>{label}</strong></div>
        <button onClick={() => setWeekStart(addDays(weekStart, 7))} aria-label="Next week"><ChevronRight /></button>
        <button className="this-week" disabled={weekStart === currentWeek} onClick={() => setWeekStart(currentWeek)}>THIS WEEK</button>
      </div>
      <div className="weekly-view-toggle" aria-label="View range">
        <button className={viewMode === "week" ? "active" : ""} onClick={() => setViewMode("week")}>WEEK</button>
        <button className={viewMode === "outlook" ? "active" : ""} onClick={() => setViewMode("outlook")}>4-WEEK OUTLOOK</button>
      </div>
      <div className="weekly-pod-filter">{PODS.map((item) => <button key={item} className={selectedPod === item ? "active" : ""} onClick={() => setSelectedPod(item)}>{POD_LABELS[item]}</button>)}</div>
    </div>
  </section>;
}

function Pulse({ data }) {
  const items = [
    [UsersRound, "Capco team", data.activeEmployees, "active this week", "blue"],
    [CalendarDays, "This week", data.importantEvents, "important events", "cyan"],
    [AlertTriangle, "Needs attention", data.attentionItems, "leadership actions", data.attentionItems ? "red" : "green"],
    [BriefcaseBusiness, "Active projects", data.activeProjects, "delivery engagements", "navy"],
    [CircleDollarSign, "Pipeline", money(data.pipeline), "active opportunity value", "violet"],
    [Flag, "Upcoming milestones", data.upcomingMilestones, "this operating week", "amber"],
  ];
  return <section className="weekly-pulse">{items.map(([Icon, label, value, detail, tone]) => <article className={`weekly-pulse-card ${tone}`} key={label}>
    <span><Icon /></span><small>{label}</small><strong>{value}</strong><p>{detail}</p>
  </article>)}</section>;
}

function ActivityChip({ item, onOpen }) {
  return <button className={`weekly-activity-chip ${item.sourceType}`} onClick={(event) => { event.stopPropagation(); onOpen(item); }} title={item.title}>
    <span>{ACTIVITY_LABELS[item.sourceType] || item.type}</span>{item.title}<ArrowRight />
  </button>;
}

function TeamThisWeek({ rows, onEmployee, onItem }) {
  const [grouping, setGrouping] = useState("pod");
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState(false);
  const filtered = useMemo(() => rows.filter((row) => {
    const text = [row.name, row.title, row.primaryProject, ...row.pods, ...row.capabilities, ...row.activities.map((item) => item.title)].join(" ").toLowerCase();
    return text.includes(query.trim().toLowerCase());
  }), [rows, query]);
  const groups = useMemo(() => {
    const values = {};
    filtered.forEach((row) => {
      const key = grouping === "pod" ? (row.pods[0] || "Account") : grouping === "project" ? row.primaryProject : "Capco account team";
      (values[key] ||= []).push(row);
    });
    return Object.entries(values).sort(([a], [b]) => a.localeCompare(b)).map(([name, people]) => [name, people.sort((a, b) => a.name.localeCompare(b.name))]);
  }, [filtered, grouping]);
  let shown = 0;
  return <section className="weekly-card weekly-team-card">
    <SectionHeading eyebrow="People first" title="What the Capco team is doing this week" note={`${rows.length} canonical employees with linked assignments and account activity`} action={<div className="weekly-team-tools">
      <div className="weekly-segmented">{[["pod", "BY POD"], ["project", "BY PROJECT"], ["person", "BY PERSON"]].map(([value, label]) => <button key={value} className={grouping === value ? "active" : ""} onClick={() => setGrouping(value)}>{label}</button>)}</div>
      <label><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find a person or focus" /></label>
    </div>} />
    <div className="weekly-team-list">
      {groups.map(([group, people]) => {
        const visible = people.filter(() => expanded || shown++ < 12);
        if (!visible.length) return null;
        return <div className="weekly-team-group" key={group}>
          <h3>{group}<span>{people.length}</span></h3>
          {visible.map((person) => <div className="weekly-person-row" role="button" tabIndex="0" key={person.id} onClick={() => onEmployee(person)} onKeyDown={(event) => { if (event.key === "Enter") onEmployee(person); }}>
            <span className="weekly-avatar">{initials(person.name)}</span>
            <span className="weekly-person-name"><b>{person.name}</b><small>{person.title || person.role} · {person.location}</small></span>
            <span className="weekly-person-pods">{person.pods.map((item) => <i key={item}>{POD_LABELS[item] || item}</i>)}</span>
            <span className="weekly-person-focus"><small>PRIMARY FOCUS</small><b>{person.primaryProject}</b><em>{person.allocationPercent}% allocated</em></span>
            <span className="weekly-person-activity">{person.activities.slice(0, 2).map((item) => <ActivityChip key={`${item.sourceType}-${item.id}`} item={item} onOpen={onItem} />)}</span>
            <ChevronRight className="weekly-row-arrow" />
          </div>)}
        </div>;
      })}
      {!filtered.length && <div className="weekly-empty"><Search />No team activity matches this search.</div>}
    </div>
    {filtered.length > 12 && <button className="weekly-show-more" onClick={() => setExpanded((value) => !value)}>{expanded ? "Show priority rows" : `Show all ${filtered.length} people`}<ArrowRight /></button>}
  </section>;
}

function Attention({ rows, onOpen }) {
  return <section className="weekly-card weekly-attention-card">
    <SectionHeading eyebrow="Leadership queue" title="Needs attention" note="Five items maximum, ordered for action" />
    <div className="weekly-attention-list">{rows.length ? rows.slice(0, 5).map((item) => <button key={item.id} className={item.severity.toLowerCase()} onClick={() => onOpen(item)}>
      <span className="weekly-severity"><i />{item.severity}</span>
      <span className="weekly-attention-copy"><b>{item.title}</b><small>{item.pod} · {item.context}</small></span>
      <span className="weekly-attention-fact"><small>OWNER</small><b>{item.owner}</b></span>
      <span className="weekly-attention-fact"><small>IMPACT</small><b>{item.impact ? money(item.impact) : "Operational"}</b></span>
      <span className="weekly-next-action"><small>NEXT ACTION{item.dueDate ? ` · ${shortDate(item.dueDate)}` : ""}</small><b>{item.nextAction}</b></span>
      <ArrowRight />
    </button>) : <div className="weekly-empty positive"><CheckCircle2 />No items meet the weekly leadership-attention rules.</div>}</div>
  </section>;
}

function WeeklyCalendar({ meta, rows, onItem }) {
  const days = Array.from({ length: 7 }, (_, index) => addDays(meta.weekStart, index));
  return <section className="weekly-card weekly-calendar-card">
    <SectionHeading eyebrow="Account rhythm" title="Weekly account calendar" note="Important client meetings, workshops, milestones, and delivery deadlines" />
    <div className="weekly-calendar-grid">{days.map((day) => {
      const items = rows.filter((item) => item.date === day);
      const visibleItems = items.slice(0, 4);
      return <div className={`weekly-calendar-day ${day === isoDate(new Date()) ? "today" : ""}`} key={day}>
        <header><span>{dayName(day)}</span><b>{dateFromIso(day).getDate()}</b></header>
        <div>{visibleItems.map((item) => <button key={`${item.sourceType}-${item.id}`} className={`${item.isClient ? "client" : ""} ${item.importance?.toLowerCase() || ""}`} onClick={() => onItem(item)}>
          <small>{item.allDay ? ACTIVITY_LABELS[item.sourceType] || item.type : new Date(item.start).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}</small>
          <b>{item.title}</b><span>{item.pod}{item.employees?.length ? ` · ${item.employees.slice(0, 2).join(", ")}` : ""}</span>
        </button>)}{items.length > visibleItems.length && <button className="weekly-calendar-more" onClick={() => onItem({ type: "calendar day", title: `${items.length - visibleItems.length} more priority items`, date: day, context: items.slice(4).map((item) => item.title).join(" · ") })}>+{items.length - visibleItems.length} more linked items</button>}</div>
        {!items.length && <p>No priority events</p>}
      </div>;
    })}</div>
  </section>;
}

function PodSummary({ rows, onPod, onProject }) {
  return <section className="weekly-card weekly-pod-summary">
    <SectionHeading eyebrow="Pod pulse" title="This week by pod" note="The operating facts that matter now" />
    <div>{rows.map((row) => <article key={row.pod}>
      <button className="weekly-pod-title" onClick={() => onPod(row.pod)}><span>{row.pod}</span><ArrowRight /></button>
      <button className="weekly-pod-focus" onClick={() => row.primaryEngagementId && onProject(row.primaryEngagementId)}><small>PRIMARY FOCUS</small><b>{row.primaryFocus}</b></button>
      <dl><div><dt>People</dt><dd>{row.employeeCount}</dd></div><div><dt>Client meetings</dt><dd>{row.clientMeetings}</dd></div><div><dt>Milestones</dt><dd>{row.keyMilestones}</dd></div><div className={row.criticalIssues ? "alert" : ""}><dt>Critical</dt><dd>{row.criticalIssues}</dd></div></dl>
    </article>)}</div>
  </section>;
}

function FourWeekOutlook({ rows, onItem }) {
  return <section className="weekly-card weekly-outlook-card" id="four-week-outlook">
    <SectionHeading eyebrow="Forward look" title="Next 4 weeks" note="Dated decisions, milestones, client moments, and staffing changes" />
    <div className="weekly-outlook-grid">{rows.map((week, index) => <article key={week.weekStart}>
      <header><span>WEEK {index + 1}</span><b>{shortDate(week.weekStart)} - {shortDate(week.weekEnd)}</b></header>
      <div>{week.items.length ? week.items.map((item) => <button key={`${item.type}-${item.id}`} onClick={() => onItem(item)}>
        <span className={`weekly-outlook-icon ${item.type}`}><Flag /></span><span><small>{shortDate(item.date)} · {item.pod}</small><b>{item.title}</b></span><ArrowRight />
      </button>) : <p>Nothing priority-linked yet.</p>}</div>
    </article>)}</div>
  </section>;
}

function Projects({ rows, onProject, onEmployee }) {
  return <section className="weekly-card weekly-projects-card">
    <SectionHeading eyebrow="Delivery" title="High-level projects" note="Health, next commitment, and the people accountable" />
    <div className="weekly-project-list">{rows.map((project) => <button key={project.id} className={`weekly-project-row ${project.health.toLowerCase()}`} onClick={() => onProject(project.id)}>
      <span className="weekly-project-health"><i />{healthLabel[project.health]}</span>
      <span className="weekly-project-name"><b>{project.name}</b><small>{project.pod} · {project.businessUnit}</small><em>Client: {project.executiveSponsor}</em></span>
      <span className="weekly-project-milestone"><small>NEXT COMMITMENT</small><b>{project.nextMilestone?.title || "No dated milestone"}</b><em>{project.nextMilestone ? shortDate(project.nextMilestone.date) : ""}</em></span>
      <span className="weekly-project-team" aria-label={`${project.teamSize} team members`}><small>{project.teamSize} Capco</small>{project.team.slice(0, 3).map((person) => <span role="button" tabIndex="0" title={`${person.name} · ${person.role}`} key={person.id} onClick={(event) => { event.stopPropagation(); onEmployee(person); }} onKeyDown={(event) => { if (event.key === "Enter") { event.stopPropagation(); onEmployee(person); } }}>{initials(person.name)}</span>)}{project.teamSize > 3 && <i>+{project.teamSize - 3}</i>}</span>
      <span className="weekly-project-value"><small>VALUE</small><b>{money(project.commercialValue)}</b></span><ArrowRight />
    </button>)}</div>
  </section>;
}

function Sales({ data, onOpportunity }) {
  return <section className="weekly-card weekly-sales-card">
    <SectionHeading eyebrow="Commercial context" title="Sales activity" note="Only near-term opportunities and leadership decisions" />
    <div className="weekly-sales-pulse"><div><small>PIPELINE</small><b>{money(data.pipeline)}</b></div><div><small>WEIGHTED</small><b>{money(data.weightedPipeline)}</b></div><div><small>NEAR TERM</small><b>{data.nearTermOpportunities}</b></div><div><small>PROPOSAL / DECISION</small><b>{data.upcomingProposalsDecisions}</b></div></div>
    <div className="weekly-sales-list">{data.opportunities.slice(0, 5).map((item) => <button key={item.id} onClick={() => onOpportunity(item.id)}>
      <span><small>{item.stage} · {item.pod}</small><b>{item.name}</b></span><span><small>NEXT STEP</small><b>{item.nextStep}</b></span><strong>{money(item.value)}</strong><ArrowRight />
    </button>)}</div>
    {!data.opportunities.length && <div className="weekly-empty">No near-term commercial decisions in this view.</div>}
  </section>;
}

function Recommendations({ rows, onOpen }) {
  if (!rows.length) return null;
  return <section className="weekly-card weekly-recommendations-card">
    <SectionHeading eyebrow="Evidence-linked" title="Leadership recommendations" note="A short action list derived from persisted account signals" />
    <div>{rows.slice(0, 3).map((item, index) => <button key={item.id} onClick={() => onOpen(item)}><span><Sparkles /></span><em>{index + 1}</em><b>{item.recommendation}</b><small>{item.suggestedAction}</small><ArrowRight /></button>)}</div>
  </section>;
}

function Changes({ rows }) {
  return <section className="weekly-card weekly-changes-card">
    <SectionHeading eyebrow="Since last week" title="What changed" note="A concise narrative from persisted account events" />
    <div>{rows.length ? rows.map((item) => <article key={item.id}><span><TrendingUp /></span><div><small>{item.kind} · {item.pod} · {shortDate(item.event_date)}</small><b>{item.headline}</b><p>{item.detail}</p></div></article>) : <div className="weekly-empty">No material account changes were recorded for this period.</div>}</div>
  </section>;
}

function ContextDrawer({ detail, onClose, onEmployeeProfile, onEngagement, onStakeholder, onOpportunity, onItem }) {
  if (!detail) return null;
  const isEmployee = detail.type === "employee";
  const data = detail.data;
  const title = isEmployee ? data.name : data.title || data.recommendation || "Linked account item";
  return <><button className="weekly-drawer-backdrop" onClick={onClose} aria-label="Close detail" /><aside className="weekly-detail-drawer">
    <header><div><span>{isEmployee ? "CAPCO EMPLOYEE / THIS WEEK" : detail.type.toUpperCase()}</span><h2>{title}</h2></div><button onClick={onClose}><X /></button></header>
    <div className="weekly-drawer-content">
      {isEmployee ? <>
        <div className="weekly-profile-lead"><span>{initials(data.name)}</span><div><b>{data.title || data.role}</b><p>{data.location} · {data.level}</p></div></div>
        <div className="weekly-profile-tags">{data.capabilities.map((item) => <span key={item}>{item}</span>)}</div>
        <h3>Current assignments</h3>
        {data.assignments.map((item) => <button className="weekly-drawer-link" key={item.id} onClick={() => onEngagement(item.engagementId)}><span><b>{item.engagement}</b><small>{item.role} · {item.allocationPercent}% allocated</small></span><ExternalLink /></button>)}
        <h3>This week's account activity</h3>
        {data.activities.map((item) => <button className="weekly-drawer-link" key={`${item.sourceType}-${item.id}`} onClick={() => onItem(item)}><span><b>{item.title}</b><small>{ACTIVITY_LABELS[item.sourceType] || item.type} · {shortDate(item.date)}</small></span><ArrowRight /></button>)}
        {!data.activities.length && <p className="weekly-drawer-note">No discrete activity is linked for this week; assignment coverage remains active.</p>}
        {!!data.nextFewWeeks.length && <><h3>Next few weeks</h3>{data.nextFewWeeks.slice(0, 5).map((item) => <button className="weekly-drawer-link" key={`${item.sourceType}-${item.id}`} onClick={() => onItem(item)}><span><b>{item.title}</b><small>{shortDate(item.date)} · {item.pod}</small></span><ArrowRight /></button>)}</>}
        {!!data.stakeholders?.length && <><h3>Connected client stakeholders</h3>{data.stakeholders.map((item) => <button className="weekly-drawer-link" key={item.id} onClick={() => onStakeholder(item)}><span><b>{item.name}</b><small>Open stakeholder context</small></span><ExternalLink /></button>)}</>}
        {!!data.opportunities?.length && <><h3>Supported opportunities</h3>{data.opportunities.map((item) => <button className="weekly-drawer-link" key={item.id} onClick={() => onOpportunity(item.id)}><span><b>{item.name}</b><small>{item.stage} · {money(item.value)}</small></span><ExternalLink /></button>)}</>}
      </> : detail.type === "recommendation" ? <><span className="weekly-drawer-badge">{data.priority} · {data.category}</span><h3>Why it is surfaced</h3><p>{data.why}</p><h3>Recommended action</h3><p>{data.suggestedAction}</p></> : <>
        {data.context && <p>{data.context}</p>}{data.pod && <span className="weekly-drawer-badge">{data.pod}{data.severity ? ` · ${data.severity}` : ""}</span>}
        {data.owner && <><h3>Owner</h3><p>{data.owner}</p></>}{data.nextAction && <><h3>Next action</h3><p>{data.nextAction}</p></>}
        {data.date && <><h3>Date</h3><p>{shortDate(data.date)}</p></>}
      </>}
    </div>
    <footer>
      <span>Canonical account data</span>
      {isEmployee && <button onClick={() => onEmployeeProfile(data.id)}>Open full account profile <ExternalLink /></button>}
      {!isEmployee && data.engagementId && <button onClick={() => onEngagement(data.engagementId)}>Open engagement <ExternalLink /></button>}
      {!isEmployee && data.stakeholderId && !data.engagementId && <button onClick={() => onStakeholder({ id: data.stakeholderId })}>Open stakeholder <ExternalLink /></button>}
    </footer>
  </aside></>;
}

export default function ExecutiveView({ pod = "All", onOpenPod, onOpenStakeholder, onOpenEmployee, onOpenEngagement, onOpenMeeting, onOpenOpportunity }) {
  const [weekStart, setWeekStart] = useState(() => mondayFor());
  const [selectedPod, setSelectedPod] = useState(pod || "All");
  const [viewMode, setViewMode] = useState("week");
  const [state, setState] = useState({ status: "loading", data: null, error: "" });
  const [detail, setDetail] = useState(null);
  const requestId = useRef(0);

  useEffect(() => setSelectedPod(pod || "All"), [pod]);
  const load = () => {
    const id = ++requestId.current;
    setState((current) => ({ status: "loading", data: current.data, error: "" }));
    api.getExecutiveWeekly({ weekStart, pod: selectedPod, outlookWeeks: 4 })
      .then((data) => { if (id === requestId.current) setState({ status: "ready", data, error: "" }); })
      .catch((error) => { if (id === requestId.current) setState({ status: "error", data: null, error: error.message || "The weekly account view could not be loaded." }); });
  };
  useEffect(load, [weekStart, selectedPod]);

  const openItem = (item) => {
    if (item.sourceType === "meeting" && onOpenMeeting) return onOpenMeeting(item.sourceId);
    if (item.opportunityId && !item.engagementId && onOpenOpportunity) return onOpenOpportunity(item.opportunityId);
    if (item.engagementId && onOpenEngagement) return onOpenEngagement(item.engagementId);
    if (item.employeeId) {
      const person = state.data?.teamActivity.find((row) => row.id === item.employeeId);
      if (person) return setDetail({ type: "employee", data: person });
    }
    setDetail({ type: item.type || item.sourceType || "account item", data: item });
  };
  const openAttention = (item) => item.engagementId ? onOpenEngagement(item.engagementId) : item.ownerEmployeeId ? onOpenEmployee(item.ownerEmployeeId) : setDetail({ type: "attention", data: item });
  const openProject = (id) => id && onOpenEngagement(id);
  const openOpportunity = (id) => id && onOpenOpportunity ? onOpenOpportunity(id) : setDetail({ type: "opportunity", data: { title: "Opportunity", id } });

  if (state.status === "loading" && !state.data) return <div className="weekly-state"><span /><h1>Loading the weekly operating view</h1><p>Resolving people, assignments, meetings, milestones, and commercial context...</p></div>;
  if (state.status === "error") return <div className="weekly-state error"><AlertTriangle /><h1>Executive analytics unavailable</h1><p>{state.error}</p><button onClick={load}><RefreshCw /> Retry connection</button></div>;
  const data = state.data;

  return <div className={`executive-weekly-view ${state.status === "loading" ? "refreshing" : ""}`}>
    <WeeklyHero meta={data.meta} weekStart={weekStart} setWeekStart={setWeekStart} viewMode={viewMode} setViewMode={setViewMode} selectedPod={selectedPod} setSelectedPod={setSelectedPod} />
    <main className="weekly-content">
      <Pulse data={data.pulse} />
      {viewMode === "week" ? <>
        <div className="weekly-primary-grid"><TeamThisWeek rows={data.teamActivity} onEmployee={(person) => setDetail({ type: "employee", data: person })} onItem={openItem} /><Attention rows={data.attentionItems} onOpen={openAttention} /></div>
        <div className="weekly-calendar-layout"><WeeklyCalendar meta={data.meta} rows={data.weeklyCalendar} onItem={openItem} /><PodSummary rows={data.podSummaries} onPod={onOpenPod} onProject={openProject} /></div>
      </> : <FourWeekOutlook rows={data.upcomingWeeks} onItem={openItem} />}
      {viewMode === "week" && <FourWeekOutlook rows={data.upcomingWeeks} onItem={openItem} />}
      <div className="weekly-bottom-grid"><Projects rows={data.projects} onProject={openProject} onEmployee={(person) => {
        const full = data.teamActivity.find((item) => item.id === person.id);
        if (full) setDetail({ type: "employee", data: full }); else onOpenEmployee(person.id);
      }} /><Sales data={data.salesSummary} onOpportunity={openOpportunity} /></div>
      <Recommendations rows={data.recommendations} onOpen={(item) => setDetail({ type: "recommendation", data: item })} />
      <Changes rows={data.changes} />
      <footer className="weekly-lineage"><Layers3 /><span>Generated from normalized SQL records for employees, assignments, engagements, events, milestones, risks, and opportunities.</span><b>Week of {shortDate(data.meta.weekStart)}</b></footer>
    </main>
    <ContextDrawer detail={detail} onClose={() => setDetail(null)} onEmployeeProfile={onOpenEmployee} onEngagement={onOpenEngagement} onStakeholder={onOpenStakeholder} onOpportunity={openOpportunity} onItem={openItem} />
  </div>;
}
