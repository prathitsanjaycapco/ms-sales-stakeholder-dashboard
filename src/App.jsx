import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle, Bell, BriefcaseBusiness, Building2, CalendarDays, ChevronDown, CircleDollarSign,
  Crosshair, FileChartColumn, Filter, Flag, Flame, Focus, Grid2X2,
  Download, ExternalLink, FileText, Hand, Layers3, List, Map as MapIcon, Maximize2, Menu, MousePointer2, Network,
  NotebookPen, Pencil, Plus, RotateCcw, Search, Settings, ShieldCheck,
  Sparkles, Tag, Trash2, UserRound, UsersRound, X, ZoomIn, ZoomOut,
  PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen,
} from "lucide-react";
import { api } from "./api";
import { adaptBackendMap, adaptBackendStakeholder } from "./mapAdapter";
import { formatBackendDate } from "./dateUtils";
import DataManagement from "./DataManagement";
import PodView from "./PodView";
import ExecutiveView from "./ExecutiveView";
import AccountAssistant from "./AccountAssistant";
import ResourcingView from "./ResourcingView";
import SearchableSelect from "./SearchableSelect";
import OperationsCenter from "./OperationsCenter";
import NotificationCenter from "./NotificationCenter";
import {
  DEFAULT_FILTERS, filterStakeholderRows, flattenCoverage, matchesStakeholderRow,
  normalizeFilterOptions, rankInfluenceRows,
} from "./stakeholderViews";
import {
  loadWorkspacePreferences, resetWorkspacePreferences,
  resolveInitialPod, saveWorkspacePreferences,
} from "./workspacePreferences";
import { useDialogAccessibility } from "./useDialogAccessibility";

const viewItems = [
  { name: "Map View", icon: MapIcon },
  { name: "List View", icon: List },
  { name: "Heat Map", icon: Flame },
  { name: "Influence Map", icon: Network },
];
const drawerTabs = ["Overview", "Meetings", "Team", "Notes", "Documents", "Opportunities", "Staffing", "Bio"];
const emptyMap = { title: "Stakeholder Map", people: [], roots: [], podHead: null, divisions: [], enterprise: [], diagnostics: { canonicalCount: 0, renderedCount: 0, missingManagers: [], duplicateReports: [], cycles: [] } };
const initials = (name = "") => name.split(" ").filter(Boolean).map((part) => part[0]).slice(0, 2).join("");
function flattenPeople(data) {
  return (data.people || []).map((person) => ({
    person,
    division: person.division,
    unit: person.businessUnit,
    teamType: person.teamType,
  }));
}

const sectionKeys = {
  "Executive View": "executive", "Pod View": "pod", "Stakeholder Map": "stakeholders",
  "Resourcing & Onboarding": "resourcing", "Account Data": "data", Settings: "settings",
};
const sectionNames = {
  ...Object.fromEntries(Object.entries(sectionKeys).map(([name, key]) => [key, name])),
  meetings: "Account Data",
  opportunities: "Account Data",
};
function initialRoute(preferences) {
  const query = new URLSearchParams(window.location.search);
  const stakeholder = query.get("stakeholder");
  const meeting = query.get("meeting");
  const opportunity = query.get("opportunity");
  const requestedSection = sectionNames[query.get("section")] || "Executive View";
  const section = stakeholder ? "Stakeholder Map" : meeting || opportunity ? "Account Data" : requestedSection;
  return {
    pod: resolveInitialPod(window.location.search, preferences, section),
    section,
    stakeholder,
    meeting,
    opportunity,
    employee: query.get("employee"),
    engagement: query.get("engagement"),
    division: query.get("division") || "All",
    businessUnit: query.get("businessUnit") || "All",
  };
}

function CountryFlag({ country, location }) {
  const code = country === "UK" ? "GB" : country;
  if (!code || !location || location === "Not recorded") return null;
  let artwork;
  if (code === "US") artwork = <><rect width="18" height="12" fill="#fff" />{[0, 2, 4, 6, 8, 10].map((y) => <rect key={y} y={y} width="18" height="1" fill="#c8343f" />)}<rect width="8" height="6.5" fill="#28559a" /><circle cx="2" cy="2" r=".45" fill="#fff" /><circle cx="5" cy="2" r=".45" fill="#fff" /><circle cx="3.5" cy="4.4" r=".45" fill="#fff" /></>;
  else if (code === "CA") artwork = <><rect width="18" height="12" fill="#fff" /><rect width="4" height="12" fill="#d52b3a" /><rect x="14" width="4" height="12" fill="#d52b3a" /><path d="M9 2.2 10 4.5l1.4-.7-.5 2 1.2.5-2.1 1.4.3 2H7.7l.3-2-2.1-1.4 1.2-.5-.5-2 1.4.7z" fill="#d52b3a" /></>;
  else if (code === "SG") artwork = <><rect width="18" height="6" fill="#ef3340" /><rect y="6" width="18" height="6" fill="#fff" /><circle cx="5" cy="3" r="2" fill="#fff" /><circle cx="5.8" cy="3" r="1.6" fill="#ef3340" /><circle cx="8.1" cy="1.8" r=".35" fill="#fff" /><circle cx="8.7" cy="3" r=".35" fill="#fff" /><circle cx="8.1" cy="4.2" r=".35" fill="#fff" /></>;
  else if (code === "GB") artwork = <><rect width="18" height="12" fill="#24478f" /><path d="M0 0 18 12M18 0 0 12" stroke="#fff" strokeWidth="3" /><path d="M0 0 18 12M18 0 0 12" stroke="#cf3341" strokeWidth="1.2" /><path d="M9 0v12M0 6h18" stroke="#fff" strokeWidth="3.6" /><path d="M9 0v12M0 6h18" stroke="#cf3341" strokeWidth="2" /></>;
  else if (code === "IN") artwork = <><rect width="18" height="4" fill="#f08b32" /><rect y="4" width="18" height="4" fill="#fff" /><rect y="8" width="18" height="4" fill="#18854b" /><circle cx="9" cy="6" r="1.25" fill="none" stroke="#2856a3" strokeWidth=".55" /><circle cx="9" cy="6" r=".3" fill="#2856a3" /></>;
  else if (code === "JP") artwork = <><rect width="18" height="12" fill="#fff" /><circle cx="9" cy="6" r="3" fill="#bc002d" /></>;
  else if (code === "DE") artwork = <><rect width="18" height="4" fill="#1b1b1b" /><rect y="4" width="18" height="4" fill="#dd2535" /><rect y="8" width="18" height="4" fill="#f3c746" /></>;
  else if (code === "HK") artwork = <><rect width="18" height="12" fill="#de2910" />{[0, 72, 144, 216, 288].map((angle) => <ellipse key={angle} cx="9" cy="4.2" rx="1" ry="2.2" fill="#fff" transform={`rotate(${angle} 9 6)`} />)}<circle cx="9" cy="6" r=".6" fill="#de2910" /></>;
  else artwork = <rect width="18" height="12" fill="#dce4eb" />;
  return <span className="country-flag" title={location} aria-label={`Location: ${location}`}><svg viewBox="0 0 18 12" role="img" aria-hidden="true">{artwork}</svg></span>;
}

function PersonTooltip({ stakeholder, context }) {
  return (
    <span className="person-tooltip" role="tooltip">
      <span className="tooltip-name">{stakeholder.name}</span>
      <span>{stakeholder.title}</span>
      <span className="tooltip-rule" />
      <span><b>Division</b>{context.division || "Pod leadership"}</span>
      <span><b>Business unit</b>{context.unit || "Not applicable"}</span>
      <span><b>Team</b>{context.teamType}</span>
      <span><b>Location</b>{stakeholder.location}</span>
      <span><b>Level</b>{stakeholder.level}</span>
      <span><b>Role</b>{stakeholder.buyer ? "Buyer" : stakeholder.influencer ? "Influencer" : "Stakeholder"}</span>
      <span><b>Budget holder</b>{stakeholder.budgetHolder ? "Yes" : "No"}</span>
      <span><b>Last / next</b>{stakeholder.lastMeeting} / {stakeholder.nextMeeting}</span>
      <span><b>Capco contacts</b>{stakeholder.capcoContacts}</span>
      <span className="tooltip-tags">{stakeholder.tags.slice(0, 3).join(" · ")}</span>
    </span>
  );
}

function StakeholderNode({ stakeholder, context, onSelect, muted = false, selected = false, variant = "standard" }) {
  return (
    <button
      className={`stakeholder-node ${variant} ${muted && !selected ? "muted" : ""} ${selected ? "selected" : ""}`}
      data-stakeholder-id={stakeholder.id}
      onClick={(event) => { event.stopPropagation(); onSelect(stakeholder, context); }}
      aria-label={`Open ${stakeholder.name}`}
    >
      <span className="node-avatar-wrap">
        <span className="node-avatar">{initials(stakeholder.name)}</span>
        {stakeholder.capcoContacts > 0 && <sup>{stakeholder.capcoContacts}</sup>}
        <CountryFlag country={stakeholder.country} location={stakeholder.location} />
      </span>
      <span className="node-copy"><strong>{stakeholder.name}</strong><small>{stakeholder.title}</small></span>
      <PersonTooltip stakeholder={stakeholder} context={context} />
    </button>
  );
}

function OrgBranch({ stakeholder, context, onSelect, matches, selectedId, enterprise, depth = 0 }) {
  const reports = stakeholder.reports || [];
  const nodeContext = stakeholder.context || context;
  return <div className="org-branch">
    <StakeholderNode
      stakeholder={stakeholder}
      context={nodeContext}
      onSelect={onSelect}
      muted={!matches(stakeholder, nodeContext)}
      selected={stakeholder.id === selectedId}
      variant={depth === 0 ? (enterprise ? "enterprise-lead" : "manager") : reports.length ? "manager" : "standard"}
    />
    {!!reports.length && <div className="children-wrap"><div className="org-level">
      {reports.map((report) => <OrgBranch key={report.id} stakeholder={report} context={context} onSelect={onSelect} matches={matches} selectedId={selectedId} enterprise={enterprise} depth={depth + 1} />)}
    </div></div>}
  </div>;
}

function TreeChart({ stakeholder, context, onSelect, matches, selectedId, enterprise = false }) {
  return <div className={`org-tree ${enterprise ? "enterprise-tree" : ""}`}>
    <OrgBranch stakeholder={stakeholder} context={context} onSelect={onSelect} matches={matches} selectedId={selectedId} enterprise={enterprise} />
  </div>;
}

function BusinessUnit({ businessUnit, division, onSelect, matches, selectedId }) {
  const businessContext = { division: division.name, unit: businessUnit.name, teamType: "Business" };
  const technologyContext = { ...businessContext, teamType: "Technology" };
  const renderRoots = (roots, context) => (
    <div className="unit-org-forest business-team-forest">
      {roots.map((stakeholder) => (
        <div className="unit-org-root" key={stakeholder.id}>
          <TreeChart stakeholder={stakeholder} context={context} onSelect={onSelect} matches={matches} selectedId={selectedId} />
        </div>
      ))}
    </div>
  );
  return (
    <article className="business-unit" style={{ "--lane-accent": division.color }}>
      <header className="unit-heading">
        <strong>{businessUnit.name}</strong>
        <span>Business organization</span>
        <span>Technology manager</span>
      </header>
      <div className="unit-content">
        <section className="business-org" aria-label={`${businessUnit.name} business reporting structure`}>
          {renderRoots(businessUnit.businessRoots, businessContext)}
        </section>
        <section className="technology-primary" aria-label={`${businessUnit.name} primary technology manager`}>
          <span className="primary-eyebrow">Primary technology manager</span>
          {businessUnit.primaryTechnology && <StakeholderNode stakeholder={businessUnit.primaryTechnology} context={technologyContext} onSelect={onSelect} muted={!matches(businessUnit.primaryTechnology, technologyContext)} selected={businessUnit.primaryTechnology.id === selectedId} variant="technology" />}
        </section>
      </div>
    </article>
  );
}

function PodHierarchyHeader({ podHead, divisions, laneWidth, onSelect, matches, selectedId }) {
  if (!podHead) return null;
  const context = { division: null, unit: null, teamType: "Business" };
  const divisionCount = Math.max(1, divisions.length);
  return <div className="pod-hierarchy" style={{ "--division-count": divisionCount, width: `${divisionCount * laneWidth + (divisionCount - 1) * 12}px` }}>
    <div className="pod-head-card">
      <span>Pod head</span>
      <StakeholderNode stakeholder={podHead} context={context} onSelect={onSelect} muted={!matches(podHead, context)} selected={podHead.id === selectedId} variant="pod-head" />
    </div>
    <div className="pod-division-connectors" aria-hidden="true">
      {divisions.map((division) => <i key={division.id} data-division-connector={division.id} />)}
    </div>
  </div>;
}

function DivisionLane({ division, onSelect, matches, unitVisible, selectedId }) {
  const context = { division: division.name, unit: "Division Leadership", teamType: "Business" };
  return (
    <section className="division-lane" style={{ "--lane-accent": division.color }}>
      <div className="division-heading">
        <span className="division-title"><UsersRound /> {division.name.toUpperCase()}</span>
        {division.head
          ? <StakeholderNode stakeholder={division.head} context={context} onSelect={onSelect} muted={!matches(division.head, context)} selected={division.head.id===selectedId} variant="division-head" />
          : <span className="division-head-vacancy">Division manager not assigned</span>}
      </div>
      <div className="division-units">
        {division.units.filter((businessUnit) => unitVisible(businessUnit, division)).map((businessUnit) => (
          <BusinessUnit key={businessUnit.id} businessUnit={businessUnit} division={division} onSelect={onSelect} matches={matches} selectedId={selectedId} />
        ))}
      </div>
    </section>
  );
}

function EnterpriseFunctions({ groups, onSelect, matches, selectedId }) {
  return (
    <section className="enterprise-functions">
      <div className="enterprise-title"><span>Enterprise Functions</span></div>
      <div className="enterprise-grid">
        {groups.map((group) => {
          const context = { division: "Enterprise Functions", unit: group.name, teamType: "Business" };
          return (
            <article key={group.id}>
              <h3><BriefcaseBusiness /> {group.name} <small>{group.memberCount} team member{group.memberCount === 1 ? "" : "s"}</small></h3>
              <div className="enterprise-org">
                {group.roots.map((stakeholder) => <div className="enterprise-root" key={stakeholder.id}>
                  <TreeChart stakeholder={stakeholder} context={context} onSelect={onSelect} matches={matches} selectedId={selectedId} enterprise />
                </div>)}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function MiniMap({ data, zoom, offset }) {
  return (
    <div className="minimap" aria-label="Map overview">
      <div className="mini-lanes">
        {data.divisions.map((division) => (
          <span key={division.id} style={{ borderColor: division.color, height: `${28 + division.units.length * 11}px` }}>
            {division.units.map((item) => <i key={item.id} style={{ background: division.color }} />)}
          </span>
        ))}
      </div>
      {!!data.enterprise.length && <span className="mini-enterprise" />}
      <i className="mini-viewport" style={{ transform: `translate(${Math.max(0, -offset.x / 18)}px, ${Math.max(0, -offset.y / 18)}px)`, width: `${Math.max(38, 82 / zoom)}px`, height: `${Math.max(22, 45 / zoom)}px` }} />
    </div>
  );
}

function MapCanvas({ data, query, filters, onSelect, editMode, panelMode, selectedId, focusRequest }) {
  const viewportRef = useRef(null);
  const worldRef = useRef(null);
  const defaultZoom = 1;
  const [zoom, setZoom] = useState(defaultZoom);
  const [offset, setOffset] = useState({ x: 18, y: 14 });
  const [drag, setDrag] = useState(null);
  const [tool, setTool] = useState("select");
  const minZoom = 0.65;
  const maxZoom = 1.5;

  const matches = (stakeholder, context) => {
    return matchesStakeholderRow({ person: stakeholder, ...context }, query, filters);
  };
  const hasActivePersonFilter = query || ["teamType", "location", "level", "influence", "budget", "relationship", "owner", "recency", "opportunities", "tags"].some((key) => filters[key] !== "All");
  const treeMatches = (stakeholder, context) => matches(stakeholder, stakeholder.context || context) || (stakeholder.reports || []).some((report) => treeMatches(report, context));
  const unitVisible = (businessUnit, division) => {
    if (filters.division !== "All" && filters.division !== division.name) return false;
    if (filters.unit !== "All" && filters.unit !== businessUnit.name) return false;
    if (!hasActivePersonFilter) return true;
    const businessContext = { division: division.name, unit: businessUnit.name, teamType: "Business" };
    const technologyContext = { ...businessContext, teamType: "Technology" };
    return businessUnit.businessRoots.some((root) => treeMatches(root, businessContext))
      || (businessUnit.primaryTechnology && matches(businessUnit.primaryTechnology, technologyContext));
  };
  const clampZoom = (value) => Math.min(maxZoom, Math.max(minZoom, value));
  const centeredOffset = (top = 17, scale = zoom) => {
    if (!viewportRef.current || !worldRef.current) return { x: 18, y: top };
    const configuredLaneWidth = Number.parseFloat(worldRef.current.style.getPropertyValue("--lane-width"));
    const worldWidth = viewportRef.current.clientWidth <= 900 && Number.isFinite(configuredLaneWidth)
      ? configuredLaneWidth
      : Math.max(worldRef.current.offsetWidth, worldRef.current.scrollWidth);
    return {
      x: Math.min(18, Math.round((viewportRef.current.clientWidth - worldWidth * scale) / 2)),
      y: top,
    };
  };
  const zoomFromCenter = (factor) => {
    if (!viewportRef.current) return;
    const next = clampZoom(zoom * factor);
    const point = { x: viewportRef.current.clientWidth / 2, y: viewportRef.current.clientHeight / 2 };
    const ratio = next / zoom;
    setOffset((current) => ({ x: point.x - (point.x - current.x) * ratio, y: point.y - (point.y - current.y) * ratio }));
    setZoom(next);
  };
  const fit = () => {
    if (!viewportRef.current || !worldRef.current) return;
    const next = Math.min((viewportRef.current.clientWidth - 34) / Math.max(worldRef.current.offsetWidth, worldRef.current.scrollWidth), (viewportRef.current.clientHeight - 34) / Math.max(worldRef.current.offsetHeight, worldRef.current.scrollHeight), 1);
    const fittedZoom = clampZoom(next);
    setZoom(fittedZoom);
    setOffset(centeredOffset(17, fittedZoom));
  };
  const reset = () => { setZoom(defaultZoom); setOffset(centeredOffset(14)); };
  useEffect(() => {
    setZoom(defaultZoom);
    setOffset({ x: 18, y: 14 });
  }, [defaultZoom]);
  useEffect(() => {
    if (!focusRequest?.id || !viewportRef.current || !worldRef.current) return undefined;
    const frame = requestAnimationFrame(() => {
      const node = worldRef.current?.querySelector(`[data-stakeholder-id="${focusRequest.id}"]`);
      if (!node || !viewportRef.current || !worldRef.current) return;
      const nodeRect = node.getBoundingClientRect();
      const worldRect = worldRef.current.getBoundingClientRect();
      const currentZoom = zoom || 1;
      const worldCenterX = (nodeRect.left + nodeRect.width / 2 - worldRect.left) / currentZoom;
      const worldCenterY = (nodeRect.top + nodeRect.height / 2 - worldRect.top) / currentZoom;
      const focusZoom = 1.35;
      setZoom(focusZoom);
      setOffset({
        x: viewportRef.current.clientWidth / 2 - worldCenterX * focusZoom,
        y: viewportRef.current.clientHeight * 0.34 - worldCenterY * focusZoom,
      });
    });
    return () => cancelAnimationFrame(frame);
  }, [focusRequest?.key, data]);
  const onWheel = (event) => {
    event.preventDefault();
    const rect = viewportRef.current.getBoundingClientRect();
    const pointer = { x: event.clientX - rect.left, y: event.clientY - rect.top };
    const next = clampZoom(zoom * (event.deltaY > 0 ? 0.92 : 1.08));
    const ratio = next / zoom;
    setOffset({ x: pointer.x - (pointer.x - offset.x) * ratio, y: pointer.y - (pointer.y - offset.y) * ratio });
    setZoom(next);
  };
  const pointerDown = (event) => {
    if (event.button !== 0 || event.target.closest("button, input, select")) return;
    setDrag({ x: event.clientX - offset.x, y: event.clientY - offset.y });
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const pointerMove = (event) => drag && setOffset({ x: event.clientX - drag.x, y: event.clientY - drag.y });
  const visibleDivisions = data.divisions.filter((division) => filters.division === "All" || filters.division === division.name);
  const branchSlots = (stakeholder) => {
    const reports = stakeholder?.reports || [];
    return reports.length ? reports.reduce((total, report) => total + branchSlots(report), 0) : 1;
  };
  const widestBusinessRow = Math.max(1, ...visibleDivisions.flatMap((division) => division.units
    .filter((businessUnit) => unitVisible(businessUnit, division))
    .map((businessUnit) => businessUnit.businessRoots.reduce((total, root) => total + branchSlots(root), 0))));
  const laneWidth = Math.max(552, 188 + widestBusinessRow * 172);
  useEffect(() => {
    const frame = requestAnimationFrame(() => setOffset(centeredOffset(14)));
    return () => cancelAnimationFrame(frame);
  }, [data.podHead?.id, laneWidth, visibleDivisions.length]);
  return (
    <div className={`map-viewport ${drag ? "dragging" : ""} ${editMode ? "edit-mode" : ""}`} ref={viewportRef} onWheel={onWheel} onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={() => setDrag(null)} onPointerCancel={() => setDrag(null)}>
      <div className="canvas-toolbar">
        <button className={tool === "select" ? "active" : ""} onClick={() => setTool("select")} title="Select"><MousePointer2 /></button>
        <button className={tool === "pan" ? "active" : ""} onClick={() => setTool("pan")} title="Pan"><Hand /></button>
        <button onClick={() => zoomFromCenter(1.12)} disabled={zoom >= maxZoom} title="Zoom in" aria-label="Zoom in"><ZoomIn /></button>
        <button onClick={() => zoomFromCenter(1 / 1.12)} disabled={zoom <= minZoom} title="Zoom out" aria-label="Zoom out"><ZoomOut /></button>
        <button onClick={fit} title="Fit to screen"><Focus /></button>
        <button onClick={reset} title="Reset view"><RotateCcw /></button>
        <span>{Math.round(zoom * 100)}%</span>
      </div>
      <div className="map-world" ref={worldRef} style={{ "--lane-width": `${laneWidth}px`, transform: `translate(${offset.x}px, ${offset.y}px) scale(${zoom})` }}>
        <PodHierarchyHeader podHead={data.podHead} divisions={visibleDivisions} laneWidth={laneWidth} onSelect={onSelect} matches={matches} selectedId={selectedId} />
        <div className="division-grid" style={{ "--division-count": Math.max(1, visibleDivisions.length), "--lane-width": `${laneWidth}px` }}>
          {visibleDivisions.map((division) => <DivisionLane key={division.id} division={division} onSelect={onSelect} matches={matches} unitVisible={unitVisible} selectedId={selectedId} />)}
        </div>
        {(filters.division === "All" || filters.division === "Enterprise Functions") && <EnterpriseFunctions groups={data.enterprise.filter((group) => filters.unit === "All" || filters.unit === group.name)} onSelect={onSelect} matches={matches} selectedId={selectedId} />}
        {!data.divisions.length && !data.enterprise.length && <p className="empty-note">No canonical stakeholders are available for this pod.</p>}
      </div>
      <MiniMap data={data} zoom={zoom} offset={offset} />
      <div className="canvas-hint">Drag to pan · Scroll to zoom</div>
    </div>
  );
}

const formatDate = (value, emptyValue = "Not scheduled") => formatBackendDate(value, { month: "short", day: "numeric", year: "numeric" }, emptyValue);
const formatMoney = (value) => value == null ? "Not recorded" : new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
const slug = (value = "") => String(value ?? "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

function resolveProfileMeetingDates(stakeholder, meetings, now = new Date()) {
  const currentTime = now.getTime();
  const timeline = (meetings || []).map((meeting) => ({
    value: meeting.meeting_date,
    time: new Date(meeting.meeting_date).getTime(),
  })).filter((meeting) => Number.isFinite(meeting.time)).sort((left, right) => left.time - right.time);
  const lastLinkedMeeting = timeline.filter((meeting) => meeting.time <= currentTime).at(-1)?.value;
  const nextLinkedMeeting = timeline.find((meeting) => meeting.time > currentTime)?.value;
  return {
    lastMeeting: stakeholder.last_meeting || stakeholder.last_meeting_at || lastLinkedMeeting || null,
    nextMeeting: stakeholder.next_meeting || stakeholder.next_meeting_at || nextLinkedMeeting || null,
  };
}

function ProfileForm({ stakeholder, onSave, onCancel, saving }) {
  const [draft, setDraft] = useState({
    name: stakeholder.name, title: stakeholder.title, level: stakeholder.level,
    organizational_role: stakeholder.organizational_role || "", location: stakeholder.location, country_code: stakeholder.country_code || "US",
    relationship_strength: stakeholder.relationship_strength, capco_owner: stakeholder.capco_owner || "",
    is_buyer: stakeholder.is_buyer, is_influencer: stakeholder.is_influencer,
    is_budget_holder: stakeholder.is_budget_holder, budget_amount: stakeholder.budget_amount ?? "",
    biography: stakeholder.biography || "", tags: (stakeholder.tags || []).join(", "),
  });
  const update = (key, value) => setDraft((current) => ({ ...current, [key]: value }));
  const submit = (event) => {
    event.preventDefault();
    onSave({ ...draft, budget_amount: draft.budget_amount === "" ? null : Number(draft.budget_amount), tags: draft.tags.split(",").map((item) => item.trim()).filter(Boolean) });
  };
  return <form className="drawer-form" onSubmit={submit}>
    <label>Full name<input required value={draft.name} onChange={(event) => update("name", event.target.value)} /></label>
    <label>Title<input required value={draft.title} onChange={(event) => update("title", event.target.value)} /></label>
    <label>Organizational role<input value={draft.organizational_role} onChange={(event) => update("organizational_role", event.target.value)} /></label>
    <div className="form-row"><label>Level<input value={draft.level} onChange={(event) => update("level", event.target.value)} /></label><label>Location<input value={draft.location} onChange={(event) => update("location", event.target.value)} /></label></div>
    <div className="form-row"><label>Country code<input maxLength="2" value={draft.country_code} onChange={(event) => update("country_code", event.target.value.toUpperCase())} /></label><label>Capco owner<input value={draft.capco_owner} onChange={(event) => update("capco_owner", event.target.value)} /></label></div>
    <label>Relationship<select value={draft.relationship_strength} onChange={(event) => update("relationship_strength", event.target.value)}><option>Strong</option><option>Medium</option><option>Developing</option><option>Unknown</option></select></label>
    <div className="form-row check-row"><label><input type="checkbox" checked={draft.is_buyer} onChange={(event) => update("is_buyer", event.target.checked)} /> Buyer</label><label><input type="checkbox" checked={draft.is_influencer} onChange={(event) => update("is_influencer", event.target.checked)} /> Influencer</label><label><input type="checkbox" checked={draft.is_budget_holder} onChange={(event) => update("is_budget_holder", event.target.checked)} /> Budget holder</label></div>
    <label>Budget amount<input type="number" min="0" value={draft.budget_amount} onChange={(event) => update("budget_amount", event.target.value)} /></label>
    <label>Biography<textarea rows="4" value={draft.biography} onChange={(event) => update("biography", event.target.value)} /></label>
    <label>Expertise tags <small>Comma separated</small><input value={draft.tags} onChange={(event) => update("tags", event.target.value)} /></label>
    <div className="form-actions"><button type="button" onClick={onCancel}>Cancel</button><button className="primary-action" disabled={saving}>{saving ? "Saving..." : "Save profile"}</button></div>
  </form>;
}

function LiveDrawerSection({ tab, profile, candidates, editMode, canWrite, confirmChanges, onRefresh, onChanged, onMapChanged }) {
  const { stakeholder, team, meetings, notes, documents = [], opportunities } = profile;
  const { lastMeeting, nextMeeting } = resolveProfileMeetingDates(stakeholder, meetings);
  const [panel, setPanel] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [meeting, setMeeting] = useState({ subject: "", meeting_date: new Date().toISOString().slice(0, 10), summary: "", outcome: "Follow-up required", tags: (stakeholder.tags || []).join(", ") });
  const [note, setNote] = useState({ body: "", category: "Relationship" });
  const [opportunity, setOpportunity] = useState({ name: "", estimated_value: "", probability: 30, stage: "Discovery", description: "", tags: (stakeholder.tags || []).join(", ") });
  const [document, setDocument] = useState({ title: "", file: null, sharepoint_url: "", document_type: "Account Plan", description: "", owner: stakeholder.capco_owner || "Capco Account Team", tags: (stakeholder.tags || []).join(", ") });
  const [managerId, setManagerId] = useState(team.manager?.id || "");
  const [editingNote, setEditingNote] = useState(null);
  const [editingDocument, setEditingDocument] = useState(null);
  useEffect(() => { setPanel(""); setError(""); setEditingNote(null); setEditingDocument(null); }, [tab, stakeholder.id]);

  if (tab === "Staffing") return <div className="drawer-tab-content"><div className="section-title"><h4>Resourcing responsibility</h4></div><div className="note-list">{profile.resourcing?.candidates?.length ? profile.resourcing.candidates.map((item) => <article key={item.id}><span>{item.pod_id} / {item.business_unit}</span><b>{item.name}</b><p>{item.requirement_title} / {item.stage}</p></article>) : <p className="empty-note">No candidate reviews are assigned.</p>}</div><div className="section-title"><h4>Linked onboarding</h4></div><div className="note-list">{profile.resourcing?.onboarding?.length ? profile.resourcing.onboarding.map((item) => <article key={item.id}><span>{formatDate(item.expected_start_date)}</span><b>{item.name}</b><p>{item.role} / {item.overall_status}</p></article>) : <p className="empty-note">No onboarding records are linked.</p>}</div></div>;

  const run = async (operation, message) => {
    if (!canWrite) { setError("Your current role cannot change account records."); return; }
    setSaving(true); setError("");
    try { await operation(); setPanel(""); setEditingNote(null); setEditingDocument(null); await onRefresh(); onMapChanged?.(stakeholder.id); onChanged(message); }
    catch (requestError) { setError(requestError.message); }
    finally { setSaving(false); }
  };
  const runOrganizationChange = (operation, message) => {
    if (confirmChanges && !window.confirm("Save this organization change to the canonical stakeholder map?")) return;
    run(operation, message);
  };
  const editProfile = (payload) => run(() => api.updateStakeholder(stakeholder.id, payload), "Profile saved");

  if (panel === "profile") return <div className="drawer-tab-content"><h4>Edit stakeholder profile</h4><ProfileForm stakeholder={stakeholder} onSave={editProfile} onCancel={() => setPanel("")} saving={saving} />{error && <div className="form-error">{error}</div>}</div>;

  if (tab === "Meetings") return <div className="drawer-tab-content"><div className="section-title"><h4>Meeting history</h4>{canWrite && <button onClick={() => setPanel(panel === "meeting" ? "" : "meeting")}><Plus /> Add</button>}</div>
    {panel === "meeting" && <form className="drawer-form compact-form" onSubmit={(event) => { event.preventDefault(); run(() => api.createPodMeeting(stakeholder.pod, { ...meeting, meeting_date: new Date(`${meeting.meeting_date}T14:00:00`).toISOString(), stakeholder_ids: [stakeholder.id], organizer: "Capco Account Team", capco_attendees: [stakeholder.capco_owner || "Priya Shah"], next_steps: [], tags: meeting.tags.split(",").map(value => value.trim()).filter(Boolean) }), "Meeting added to the profile and Pod View"); }}><label>Subject<input required value={meeting.subject} onChange={(event) => setMeeting({ ...meeting, subject: event.target.value })} /></label><label>Date<input required type="date" value={meeting.meeting_date} onChange={(event) => setMeeting({ ...meeting, meeting_date: event.target.value })} /></label><label>Summary<textarea rows="3" value={meeting.summary} onChange={(event) => setMeeting({ ...meeting, summary: event.target.value })} /></label><label>Outcome<input value={meeting.outcome} onChange={(event) => setMeeting({ ...meeting, outcome: event.target.value })} /></label><label>Tags <small>Comma separated</small><input value={meeting.tags} onChange={(event) => setMeeting({ ...meeting, tags: event.target.value })}/></label><div className="form-actions"><button type="button" onClick={() => setPanel("")}>Cancel</button><button className="primary-action" disabled={saving}>Save meeting</button></div></form>}
    {meetings.length ? <div className="activity">{meetings.map((item) => <React.Fragment key={item.id}><i /><span><b>{formatDate(item.meeting_date)} · {item.subject}</b>{item.summary || item.outcome}</span></React.Fragment>)}</div> : <p className="empty-note">No meetings recorded.</p>}{error && <div className="form-error">{error}</div>}</div>;

  if (tab === "Team") {
    const managerOptions = candidates.filter((item) => item.id !== stakeholder.id);
    const unitId = stakeholder.division && stakeholder.business_unit
      ? `${slug(stakeholder.pod)}-${slug(stakeholder.division)}-${slug(stakeholder.business_unit)}`
      : null;
    const governedManager = stakeholder.organizational_role === "Pod Head"
      || ["Division Head", "Business Unit Head", "Enterprise Function Lead"].includes(stakeholder.organizational_role)
      || team.is_primary_technology;
    return <div className="drawer-tab-content team-tab"><div className="section-title"><h4>Reporting structure</h4>{editMode && canWrite && <span className="edit-chip">Editing</span>}</div>
      <label>Manager</label>{editMode && canWrite && !governedManager ? <div className="inline-editor"><SearchableSelect ariaLabel="Manager" value={managerId} onChange={setManagerId} options={managerOptions.map((item) => ({ ...item, label: `${item.name} — ${item.title}` }))} placeholder="Select a manager" /><button className="primary-action" disabled={saving || !managerId || managerId === (team.manager?.id || "")} onClick={() => runOrganizationChange(() => api.updateReportingLine({ report_id: stakeholder.id, manager_id: managerId, reason: "Updated in stakeholder map" }), "Reporting line saved")}>Save</button></div> : <div className="team-manager">{team.manager ? `${team.manager.name} — ${team.manager.title}` : stakeholder.organizational_role === "Pod Head" ? "Top of pod hierarchy" : "Governed organization assignment"}</div>}
      {governedManager && stakeholder.organizational_role !== "Pod Head" && <p className="editing-hint">This reporting line is governed by the organization structure.</p>}
      <label>Direct reports <span>{team.direct_reports.length}</span></label>{team.direct_reports.length ? <div className="report-list">{team.direct_reports.map((report, index) => <div key={report.id}><i>{index === team.direct_reports.length - 1 ? "└" : "├"}</i><span><b>{report.name}</b><small>{report.title}</small></span></div>)}</div> : <p className="empty-note">No confirmed direct reports.</p>}
      {stakeholder.team_type === "Technology" && <div className="primary-tech-card"><b>{team.is_primary_technology ? "Primary technology stakeholder" : "Technology team member"}</b><p>{team.is_primary_technology ? "This person is the designated technology manager shown on the map." : "This person remains available in search, list view, profiles, and the primary manager's team, but is intentionally omitted from the visual map."}</p>{editMode && canWrite && !team.is_primary_technology && <button className="primary-action" disabled={saving} onClick={() => runOrganizationChange(() => api.updatePrimaryTechnology(unitId, { stakeholder_id: stakeholder.id, reason: "Updated in stakeholder map" }), "Primary technology owner updated")}>Make primary technology</button>}</div>}
      {!editMode && canWrite && <p className="editing-hint">Turn on <b>Edit map</b> to change reporting lines and technology ownership.</p>}{!canWrite && <p className="editing-hint"><ShieldCheck/> Organization data is read only for your current role.</p>}{error && <div className="form-error" role="alert">{error}</div>}</div>;
  }

  if (tab === "Notes") return <div className="drawer-tab-content"><div className="section-title"><h4>Relationship notes</h4>{canWrite && <button onClick={() => setPanel(panel === "note" ? "" : "note")}><Plus /> Add</button>}</div>
    {panel === "note" && <form className="drawer-form compact-form" onSubmit={(event) => { event.preventDefault(); run(() => api.createNote(stakeholder.id, { ...note, author: "Current User" }), "Note added"); }}><label>Category<select value={note.category} onChange={(event) => setNote({ ...note, category: event.target.value })}><option>Relationship</option><option>Opportunity</option><option>Meeting</option><option>General</option></select></label><label>Note<textarea required rows="4" value={note.body} onChange={(event) => setNote({ ...note, body: event.target.value })} /></label><div className="form-actions"><button type="button" onClick={() => setPanel("")}>Cancel</button><button className="primary-action" disabled={saving}>Save note</button></div></form>}
    <div className="note-list">{notes.map((item) => editingNote?.id === item.id ? <form key={item.id} className="drawer-form compact-form" onSubmit={(event) => { event.preventDefault(); run(() => api.updateNote(item.id, { body: editingNote.body, category: editingNote.category }), "Note updated"); }}><textarea required rows="4" value={editingNote.body} onChange={(event) => setEditingNote({ ...editingNote, body: event.target.value })} /><div className="form-actions"><button type="button" onClick={() => setEditingNote(null)}>Cancel</button><button className="primary-action" disabled={saving}>Update</button></div></form> : <article key={item.id}><span>{item.category} · {formatDate(item.updated_at)}</span><p>{item.body}</p>{canWrite && <div className="record-actions"><button onClick={() => setEditingNote(item)}><Pencil /> Edit</button><button className="danger-action" onClick={() => window.confirm("Delete this sensitive note? This cannot be undone.") && run(() => api.deleteNote(item.id), "Note deleted")}><Trash2 /> Delete</button></div>}</article>)}</div>{!notes.length && <p className="empty-note">No notes recorded.</p>}{error && <div className="form-error" role="alert">{error}</div>}</div>;

  if (tab === "Documents") return <div className="drawer-tab-content">
    <div className="section-title"><h4>Stakeholder documents</h4>{canWrite && <button onClick={() => setPanel(panel === "document" ? "" : "document")}><Plus /> Upload</button>}</div>
    <p className="editing-hint">Upload a local copy for download. Add a SharePoint link when a shared version also exists.</p>
    {panel === "document" && <form className="drawer-form compact-form" onSubmit={(event) => { event.preventDefault(); run(async () => {
      await api.uploadStakeholderDocument(stakeholder.id, document.file, { title: document.title, sharepoint_url: document.sharepoint_url, document_type: document.document_type, description: document.description, owner: document.owner, tags: document.tags });
      setDocument({ title: "", file: null, sharepoint_url: "", document_type: "Account Plan", description: "", owner: stakeholder.capco_owner || "Capco Account Team", tags: (stakeholder.tags || []).join(", ") });
    }, "Document uploaded"); }}>
      <label>Document title<input required value={document.title} onChange={(event) => setDocument({ ...document, title: event.target.value })} /></label>
      <label>Local file <small>Required · maximum 25 MB</small><input required type="file" onChange={(event) => setDocument({ ...document, file: event.target.files?.[0] || null })} /></label>
      <label>SharePoint link <small>Optional</small><input type="url" placeholder="https://...sharepoint.com/..." value={document.sharepoint_url} onChange={(event) => setDocument({ ...document, sharepoint_url: event.target.value })} /></label>
      <div className="form-row"><label>Type<select value={document.document_type} onChange={(event) => setDocument({ ...document, document_type: event.target.value })}>{["Proposal","Meeting Brief","Account Plan","Contract","Delivery","Research","Other"].map((value) => <option key={value}>{value}</option>)}</select></label><label>Owner<input value={document.owner} onChange={(event) => setDocument({ ...document, owner: event.target.value })} /></label></div>
      <label>Tags <small>Comma separated</small><input value={document.tags} onChange={(event) => setDocument({ ...document, tags: event.target.value })}/></label>
      <label>Description<textarea rows="3" value={document.description} onChange={(event) => setDocument({ ...document, description: event.target.value })} /></label>
      <div className="form-actions"><button type="button" onClick={() => setPanel("")}>Cancel</button><button className="primary-action" disabled={saving || !document.file}>{saving ? "Uploading..." : "Upload document"}</button></div>
    </form>}
    <div className="document-list">{documents.map((item) => editingDocument?.id === item.id ? <form key={item.id} className="drawer-form compact-form" onSubmit={(event) => { event.preventDefault(); run(() => api.updateDocument(item.id, { title: editingDocument.title, sharepoint_url: editingDocument.sharepoint_url || null, document_type: editingDocument.document_type, description: editingDocument.description, owner: editingDocument.owner, tags: editingDocument.tags || [] }), "Document updated"); }}>
      <label>Title<input required value={editingDocument.title} onChange={(event) => setEditingDocument({ ...editingDocument, title: event.target.value })} /></label>
      <label>SharePoint link <small>Optional</small><input type="url" value={editingDocument.sharepoint_url || ""} onChange={(event) => setEditingDocument({ ...editingDocument, sharepoint_url: event.target.value })} /></label>
      <div className="form-row"><label>Type<select value={editingDocument.document_type} onChange={(event) => setEditingDocument({ ...editingDocument, document_type: event.target.value })}>{["Proposal","Meeting Brief","Account Plan","Contract","Delivery","Research","Other"].map((value) => <option key={value}>{value}</option>)}</select></label><label>Owner<input value={editingDocument.owner} onChange={(event) => setEditingDocument({ ...editingDocument, owner: event.target.value })} /></label></div>
      <label>Tags <small>Comma separated</small><input value={Array.isArray(editingDocument.tags) ? editingDocument.tags.join(", ") : editingDocument.tags || ""} onChange={(event) => setEditingDocument({ ...editingDocument, tags: event.target.value.split(",").map(value => value.trim()).filter(Boolean) })}/></label>
      <label>Description<textarea rows="3" value={editingDocument.description} onChange={(event) => setEditingDocument({ ...editingDocument, description: event.target.value })} /></label>
      <div className="form-actions"><button type="button" onClick={() => setEditingDocument(null)}>Cancel</button><button className="primary-action" disabled={saving}>Save metadata</button></div>
    </form> : <article key={item.id}><FileText/><div><span>{item.document_type} · {formatDate(item.updated_at)}</span><b>{item.title}</b><p>{item.description || `Owned by ${item.owner}`}</p><small>{item.file_name ? `${item.file_name}${item.file_size ? ` · ${(item.file_size / 1024).toFixed(0)} KB` : ""}` : "Shared link only"}</small>{item.tags?.length>0&&<div className="drawer-tags">{item.tags.map(value=><span key={value}>{value}</span>)}</div>}</div><div className="document-actions">{item.stored_name && <a href={api.documentDownloadUrl(item.id)}><Download /> Download</a>}{(item.sharepoint_url || item.url) && <a href={item.sharepoint_url || item.url} target="_blank" rel="noreferrer"><ExternalLink /> SharePoint</a>}{canWrite && <><button onClick={() => setEditingDocument({ ...item, sharepoint_url: item.sharepoint_url || item.url || "" })}><Pencil /> Edit</button><button className="danger-action" onClick={() => window.confirm("Remove this document and its stored file? This cannot be undone.") && run(() => api.deleteDocument(item.id), "Document removed")}><Trash2 /> Remove</button></>}</div></article>)}</div>
    {!documents.length && <p className="empty-note">No documents uploaded for this stakeholder.</p>}{error && <div className="form-error">{error}</div>}
  </div>;

  if (tab === "Opportunities") return <div className="drawer-tab-content"><div className="section-title"><h4>Potential opportunities</h4>{canWrite && <button onClick={() => setPanel(panel === "opportunity" ? "" : "opportunity")}><Plus /> Add</button>}</div>
    {panel === "opportunity" && <form className="drawer-form compact-form" onSubmit={(event) => { event.preventDefault(); run(() => api.createOpportunity({ ...opportunity, estimated_value: Number(opportunity.estimated_value || 0), probability: Number(opportunity.probability), stakeholder_ids: [stakeholder.id], owner: "Capco Account Team", target_close_date: null, tags: opportunity.tags.split(",").map(value => value.trim()).filter(Boolean) }), "Opportunity added"); }}><label>Name<input required value={opportunity.name} onChange={(event) => setOpportunity({ ...opportunity, name: event.target.value })} /></label><div className="form-row"><label>Estimated value<input type="number" min="0" value={opportunity.estimated_value} onChange={(event) => setOpportunity({ ...opportunity, estimated_value: event.target.value })} /></label><label>Probability<input type="number" min="0" max="100" value={opportunity.probability} onChange={(event) => setOpportunity({ ...opportunity, probability: event.target.value })} /></label></div><label>Stage<select value={opportunity.stage} onChange={(event) => setOpportunity({ ...opportunity, stage: event.target.value })}><option>Discovery</option><option>Qualification</option><option>Proposal</option><option>Negotiation</option><option>Closed Won</option><option>Closed Lost</option></select></label><label>Description<textarea rows="3" value={opportunity.description} onChange={(event) => setOpportunity({ ...opportunity, description: event.target.value })} /></label><label>Tags <small>Comma separated</small><input value={opportunity.tags} onChange={(event) => setOpportunity({ ...opportunity, tags: event.target.value })}/></label><div className="form-actions"><button type="button" onClick={() => setPanel("")}>Cancel</button><button className="primary-action" disabled={saving}>Save opportunity</button></div></form>}
    {opportunities.map((item) => <div className="opportunity" key={item.id}><b>{item.name}</b><span>{item.stage} · {formatMoney(item.estimated_value)}</span><strong>{item.probability}%</strong></div>)}{!opportunities.length && <p className="empty-note">No active opportunities.</p>}{error && <div className="form-error">{error}</div>}</div>;

  if (tab === "Bio") return <div className="drawer-tab-content"><div className="section-title"><h4>Biography</h4>{canWrite && <button onClick={() => setPanel("profile")}><Pencil /> Edit</button>}</div><p>{stakeholder.biography || "No biography has been added."}</p><h4>Areas of expertise</h4><div className="drawer-tags">{(stakeholder.tags || []).map((tagName) => <span key={tagName}>{tagName}</span>)}</div></div>;

  return <div className="drawer-tab-content overview-tab"><dl><dt>Division</dt><dd>{stakeholder.division || "Pod leadership"}</dd><dt>Business unit</dt><dd>{stakeholder.business_unit || "Not applicable"}</dd><dt>Team</dt><dd>{stakeholder.team_type}</dd><dt>Location</dt><dd>{stakeholder.location || "Not recorded"}</dd><dt>Level</dt><dd>{stakeholder.level}</dd><dt>Last meeting</dt><dd>{formatDate(lastMeeting, "Not recorded")}</dd><dt>Next meeting</dt><dd>{formatDate(nextMeeting)}</dd><dt>Capco owner</dt><dd className="link-value">{stakeholder.capco_owner || "Unassigned"}</dd></dl><div className="drawer-divider" /><div className="section-title"><span>Stakeholder profile</span>{canWrite && <button onClick={() => setPanel("profile")}><Pencil /> Edit</button>}</div><div className="profile-fields"><span>Role</span><b>{stakeholder.is_buyer ? "Buyer" : stakeholder.is_influencer ? "Influencer" : "Stakeholder"}</b><span>Has budget</span><b>{stakeholder.is_budget_holder ? "Yes" : "No"}</b><span>Budget amount</span><b>{formatMoney(stakeholder.budget_amount)}</b><span>Relationship</span><b>{stakeholder.relationship_strength}</b></div><div className="drawer-divider" /><h4>Latest intelligence</h4><p>{notes[0]?.body || stakeholder.biography || "No relationship intelligence recorded."}</p></div>;
}

function LiveStakeholderDrawer({ selected, pod, editMode, canWrite, confirmChanges, requestedTab, onCollapse, onMapChanged }) {
  const [tab, setTab] = useState("Overview");
  const [profile, setProfile] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const selectedId = selected?.person.id;
  const loadProfile = async () => {
    if (!selected) return;
    setLoading(true); setError("");
    try {
      const nextProfile = await api.getStakeholderProfile(selected.person.id);
      if (nextProfile.stakeholder.id !== selected.person.id || nextProfile.stakeholder.pod !== pod) throw new Error("Canonical stakeholder linkage mismatch");
      const nextCandidates = await api.getStakeholders({ pod, limit: 500 });
      setProfile(nextProfile); setCandidates(nextCandidates);
    } catch (requestError) {
      setProfile(null);
      setCandidates([]);
      setError(requestError.message || "Database profile unavailable");
    }
    finally { setLoading(false); }
  };
  useEffect(() => { setTab("Overview"); setNotice(""); loadProfile(); }, [selectedId, pod]);
  useEffect(() => { if (requestedTab?.tab) setTab(requestedTab.tab); }, [requestedTab?.key]);
  useEffect(() => { if (!notice) return undefined; const timer = setTimeout(() => setNotice(""), 3200); return () => clearTimeout(timer); }, [notice]);
  if (!selected) return <aside className="stakeholder-drawer empty-drawer"><UsersRound /><h3>No stakeholder selected</h3><p>Select a node on the map to view relationship intelligence.</p></aside>;
  const person = profile?.stakeholder || selected.person;
  const tags = person.tags || selected.person.tags || [];
  return <aside className="stakeholder-drawer"><button className="drawer-close" onClick={onCollapse} aria-label="Collapse stakeholder drawer" title="Collapse stakeholder drawer"><PanelRightClose /></button><section className="drawer-profile"><div className="profile-avatar">{initials(person.name)}<sup>{selected.person.capcoContacts || 1}</sup></div><div><h2>{person.name}</h2>{(person.is_buyer ?? selected.person.buyer) && <span className="buyer-badge">Buyer / decision-maker</span>}<strong>{person.title}</strong><p>{person.division || selected.division || "Pod leadership"} · {person.business_unit || selected.unit || "Not applicable"}<br />{person.location || "Not recorded"}</p></div></section><div className="drawer-tags">{tags.slice(0, 4).map((tagName) => <span key={tagName}>{tagName}</span>)}</div>{editMode && canWrite && <div className="edit-mode-banner"><Pencil /> Map editing is on</div>}<nav className="drawer-tabs">{drawerTabs.map((item) => <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>{item}</button>)}</nav>{notice && <div className="save-notice" role="status" aria-live="polite">{notice}</div>}{loading && !profile && <div className="api-state"><span className="loading-dot" /> Loading stakeholder intelligence...</div>}{error && !loading && <div className="api-state error-state" role="alert"><b>Backend profile unavailable</b><span>{error}</span><button onClick={loadProfile}>Retry</button></div>}{profile && <LiveDrawerSection tab={tab} profile={profile} candidates={candidates} editMode={editMode} canWrite={canWrite} confirmChanges={confirmChanges} onRefresh={loadProfile} onChanged={setNotice} onMapChanged={onMapChanged} />}</aside>;
}

function ControlRail({ pod, setPod, view, setView, filters, setFilters, data, filterOptions, onAdd, onCollapse, canWrite }) {
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const allRows = flattenPeople(data);
  const options = normalizeFilterOptions(filterOptions, allRows);
  const selectFilter = (label, key, values) => (
    <label className="rail-filter"><span>{label}</span><select value={filters[key]} onChange={(event) => setFilters({ ...filters, [key]: event.target.value })}>{values.map((value) => <option key={value}>{value}</option>)}</select></label>
  );
  return (
    <aside className="control-rail">
      <button className="rail-collapse" onClick={onCollapse} aria-label="Collapse control rail" title="Collapse control rail"><PanelLeftClose /></button>
      <section><label className="rail-label">Pod selection</label><select className="pod-select" value={pod} onChange={(event) => setPod(event.target.value)}><option>All</option><option>ISG</option><option>Wealth Management</option><option>MSIM</option></select></section>
      <section><label className="rail-label">Views</label>{viewItems.map(({ name, icon: Icon }) => <button key={name} className={`view-button ${view === name ? "active" : ""}`} onClick={() => setView(name)}><Icon /> {name}</button>)}</section>
      <section className="filter-section"><label className="rail-label"><Filter /> Filters</label>
        {selectFilter("Division", "division", ["All", ...options.divisions])}
        {selectFilter("Business unit", "unit", ["All", ...options.business_units])}
        {selectFilter("Business / Technology", "teamType", ["All", ...options.team_types])}
        {selectFilter("Location", "location", ["All", ...options.locations])}
        {selectFilter("Level", "level", ["All", ...options.levels])}
        <button className="advanced-filter-toggle" aria-expanded={advancedOpen} onClick={() => setAdvancedOpen((current) => !current)}>
          Advanced filters <ChevronDown />
        </button>
        {advancedOpen && <div className="advanced-filter-fields">
          {selectFilter("Buyer / Influencer", "influence", ["All", "Buyer", "Influencer"])}
          {selectFilter("Budget holder", "budget", ["All", "Yes", "No"])}
          {selectFilter("Relationship strength", "relationship", ["All", ...options.relationship_strengths])}
          {selectFilter("Capco relationship owner", "owner", ["All", ...options.capco_owners])}
          {selectFilter("Meeting recency", "recency", ["All", "Last 30 days", "Last 90 days", "No recent meeting"])}
          {selectFilter("Opportunities", "opportunities", ["All", "Has opportunities"])}
          {selectFilter("Expertise / interest tags", "tags", ["All", ...options.tags])}
        </div>}
        <button className="clear-filters" onClick={() => setFilters(DEFAULT_FILTERS)}>Clear all filters</button>
      </section>
      <section className="legend-section"><label className="rail-label">Map indicators</label><span><i className="legend-tech" /> Primary technology</span><span><i className="legend-capco">2</i> Capco contacts</span><span><i className="legend-flag" /> Stakeholder location</span><small>Buyer and budget details appear in the profile and hover view.</small></section>
      {canWrite && <button className="rail-add" onClick={onAdd}><Plus /> Add person</button>}
    </aside>
  );
}

function SecondaryView({ type, rows, total, onSelect, pod, coverageState, filters, onRetryCoverage }) {
  const countCopy = `${rows.length} of ${total} stakeholders match the current search and filters`;
  if (type === "Heat Map") {
    if (coverageState.status === "loading" && !coverageState.data) return <div className="secondary-view secondary-state"><span className="map-skeleton"/><h2>Loading relationship coverage</h2><p>Resolving canonical business-unit scores…</p></div>;
    if (coverageState.status === "error") return <div className="secondary-view secondary-state error"><ShieldCheck/><h2>Relationship coverage unavailable</h2><p>{coverageState.error}</p><button onClick={onRetryCoverage}>Retry coverage</button></div>;
    const units = flattenCoverage(coverageState.data, filters);
    return <div className="secondary-view"><h2>Relationship coverage</h2><p>{pod} · canonical coverage by business unit · {countCopy}</p>{units.length ? <div className="coverage-grid">{units.map((unit) => <div key={unit.id}><b>{unit.name}</b><span>{unit.division} · {unit.known_stakeholders}/{unit.total_stakeholders} known</span><div className="coverage-score"><i style={{ width: `${unit.coverage_score}%` }}/></div><small>{unit.buyers} buyers · {unit.budget_holders} budget holders · {unit.open_opportunities} opportunities</small><strong className={unit.coverage.toLowerCase()}>{unit.coverage} · {unit.coverage_score}%</strong></div>)}</div> : <div className="secondary-empty"><Filter/>No business units match the organization filters.</div>}</div>;
  }
  if (type === "Influence Map") {
    const ranked = rankInfluenceRows(rows);
    return <div className="secondary-view"><h2>Influence map</h2><p>{countCopy} · ranked by canonical influence and relationship data</p>{ranked.length ? <div className="influence-view">{ranked.map((row) => <button key={row.person.id} onClick={() => onSelect(row.person, row)}><span>{initials(row.person.name)}</span><b>{row.person.name}</b><small>{[row.person.buyer && "Buyer", row.person.budgetHolder && "Budget holder", row.person.influencer && "Influencer"].filter(Boolean).join(" · ") || "Stakeholder"}</small><em>{row.person.relationship} · {row.person.opportunityCount || 0} opportunities</em></button>)}</div> : <div className="secondary-empty"><Network/>No stakeholders match the current search and filters.</div>}</div>;
  }
  return <div className="secondary-view"><h2>Stakeholder directory</h2><p>{pod} · {countCopy}</p>{rows.length ? <div className="list-table"><div><b>Name</b><b>Division</b><b>Business unit</b><b>Team</b><b>Relationship</b></div>{[...rows].sort((a, b) => a.person.name.localeCompare(b.person.name)).map((row) => <button key={`${row.person.id}-${row.unit}`} onClick={() => onSelect(row.person, row)}><span>{row.person.name}<small>{row.person.title}</small></span><span>{row.division}</span><span>{row.unit}</span><span>{row.teamType}</span><span>{row.person.relationship}</span></button>)}</div> : <div className="secondary-empty"><List/>No stakeholders match the current search and filters.</div>}</div>;
}

function SettingsView({ preferences, onChange, onReset, session }) {
  const [tab, setTab] = useState("Preferences");
  return <div className="secondary-view settings-view"><div className="settings-layout"><nav className="settings-tabs" aria-label="Settings sections"><button className={tab === "Preferences" ? "active" : ""} onClick={() => setTab("Preferences")}>Preferences &amp; access</button><button className={tab === "Trust" ? "active" : ""} onClick={() => setTab("Trust")}>Trust &amp; operations</button></nav>{tab === "Trust" ? <OperationsCenter session={session} /> : <div className="settings-card"><div className="session-summary"><ShieldCheck/><span><b>{session?.subject || "Loading identity…"}</b><small>{session?.roles?.join(" · ") || "Resolving application roles"}</small></span><em>{session?.permissions?.write ? "Can edit" : "Read only"}</em></div><label><span>Default pod<small>Used when a shared URL does not specify a pod.</small></span><select value={preferences.defaultPod} onChange={(event) => onChange({ defaultPod: event.target.value })}><option>All</option><option>ISG</option><option>Wealth Management</option><option>MSIM</option></select></label><label><span>Compact hover details<small>Keep stakeholder tooltips dense on large maps.</small></span><input type="checkbox" checked={preferences.compactTooltips} onChange={(event) => onChange({ compactTooltips: event.target.checked })} /></label><label><span>Confirm organization changes<small>Confirm reporting-line and technology-owner changes before saving.</small></span><input type="checkbox" checked={preferences.confirmChanges} onChange={(event) => onChange({ confirmChanges: event.target.checked })} /></label><button onClick={onReset}><RotateCcw /> Reset map preferences</button></div>}</div></div>;
}

function AccountEntityDialog({ detail, onClose, onStakeholder, onEmployee, onEngagement, onMeeting, onOpportunity, onResourcing }) {
  const dialogRef = useRef(null);
  const [tab, setTab] = useState("Overview");
  useDialogAccessibility(dialogRef, onClose);
  useEffect(() => setTab("Overview"), [detail?.type, detail?.data?.id, detail?.data?.engagement?.id]);
  if (!detail) return null;
  const employee = detail.type === "employee" ? detail.data : null;
  const engagement = detail.type === "engagement" ? detail.data : null;
  const project = engagement?.engagement;
  const title = employee?.name || project?.name || "Account record";
  const recordPod = employee?.assignments?.[0]?.pod_id || project?.pod_id;
  const currentRelationships = employee?.stakeholder_relationships?.filter((item) => item.is_current) || [];
  const projectRevenue = engagement?.revenue?.reduce((sum, item) => sum + Number(item.amount || 0), 0) || 0;
  const projectRisks = engagement?.risks || [];
  const projectMilestones = engagement?.milestones || [];
  const projectResourcing = engagement?.resourcing || { requirements: [], candidates: [], onboarding: [] };
  const tabs = employee ? ["Overview", "Engagements", "Staffing", "Relationships", "Activity"] : ["Overview", "People", "Delivery", "Commercial & staffing"];
  const open = (callback, ...args) => { onClose(); callback?.(...args); };
  const displayDate = (value) => formatBackendDate(value, { month: "short", day: "numeric", year: "numeric" });
  const displayMoney = (value) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 }).format(Number(value || 0));
  const empty = (copy) => <p className="entity-empty">{copy}</p>;

  return <div className="modal-backdrop entity-detail-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <section ref={dialogRef} className="entity-detail-dialog" role="dialog" aria-modal="true" aria-label={`${title} details`}>
      <header className="entity-detail-head">
        <div><span className="detail-kicker">{employee ? "CAPCO EMPLOYEE" : "CLIENT ENGAGEMENT"}</span><h2>{title}</h2><p>{employee ? `${employee.role} · ${employee.level} · ${employee.location}` : `${project.pod_id} · ${project.division} · ${project.business_unit}`}</p></div>
        <button data-dialog-initial-focus className="modal-close" onClick={onClose} aria-label="Close details"><X/></button>
      </header>
      <nav className="entity-detail-tabs" aria-label={`${title} detail sections`}>{tabs.map((item) => <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>{item}</button>)}</nav>
      <div className="entity-detail-body">
        {employee && tab === "Overview" && <>
          <div className="entity-metrics"><span><b>{employee.assignments.length}</b>Engagements</span><span><b>{currentRelationships.length}</b>Relationships</span><span><b>{employee.meetings.length}</b>Meetings</span><span><b>{employee.owned_opportunities.length}</b>Opportunities</span></div>
          <h3>Capabilities</h3><div className="drawer-tags">{employee.skills.length ? employee.skills.map((value) => <span key={value}>{value}</span>) : empty("No capabilities are recorded.")}</div>
          <h3>Current account position</h3><div className="entity-summary-grid"><span><small>Role</small><b>{employee.role}</b></span><span><small>Level</small><b>{employee.level}</b></span><span><small>Location</small><b>{employee.location}</b></span><span><small>Status</small><b>{employee.active ? "Active" : "Inactive"}</b></span></div>
        </>}
        {employee && tab === "Engagements" && <><h3>Engagement assignments</h3><div className="entity-records">{employee.assignments.length ? employee.assignments.map((item) => <button key={item.id} onClick={() => open(onEngagement, item.engagement_id)}><span><b>{item.engagement_name}</b><small>{item.pod_id} · {item.allocation_percent}% allocation · {item.billable ? "Billable" : "Non-billable"}</small></span><ExternalLink /></button>) : empty("No engagement assignments are linked.")}</div></>}
        {employee && tab === "Relationships" && <><h3>Current stakeholder relationships</h3><div className="entity-records">{currentRelationships.length ? currentRelationships.map((item) => <button key={item.id} onClick={() => open(onStakeholder, { id: item.stakeholder_id })}><span><b>{item.stakeholder_name}</b><small>{item.relationship_role}{item.is_primary ? " · Primary" : ""}</small></span><ExternalLink /></button>) : empty("No current stakeholder relationships are linked.")}</div></>}
        {employee && tab === "Staffing" && <><h3>Resourcing lifecycle</h3><div className="entity-records">{employee.resourcing?.length ? employee.resourcing.map((item) => <button key={`${item.candidate_id}-${item.requirement_id}`} onClick={() => open(onResourcing, item.pod_id)}><span><b>{item.requirement_title}</b><small>{item.role} / {item.stage}{item.overall_status ? ` / Onboarding ${item.overall_status}` : ""}</small></span><ExternalLink /></button>) : empty("No candidate, reviewer, or onboarding records are linked.")}</div></>}
        {employee && tab === "Activity" && <div className="entity-split">
          <section><h3>Recent meetings</h3><div className="entity-records">{employee.meetings.length ? employee.meetings.map((item) => <button key={item.id} onClick={() => open(onMeeting, item.id, recordPod)}><span><b>{item.subject}</b><small>{displayDate(item.meeting_date)} · {item.attendee_role}</small></span><ExternalLink /></button>) : empty("No meetings are linked.")}</div></section>
          <section><h3>Owned opportunities</h3><div className="entity-records">{employee.owned_opportunities.length ? employee.owned_opportunities.map((item) => <button key={item.id} onClick={() => open(onOpportunity, item.id, recordPod)}><span><b>{item.name}</b><small>{item.stage} · {displayMoney(item.estimated_value)} · {item.probability}%</small></span><ExternalLink /></button>) : empty("No opportunities are linked.")}</div></section>
        </div>}

        {engagement && tab === "Overview" && <>
          <div className="entity-metrics"><span className={`health-${project.health?.toLowerCase()}`}><b>{project.health}</b>Delivery health</span><span><b>{displayMoney(project.commercial_value)}</b>Commercial value</span><span><b>{engagement.team.length}</b>Capco team</span><span><b>{projectRisks.filter((item) => item.status !== "Resolved").length}</b>Open risks</span></div>
          <div className="entity-summary-grid"><span><small>Start</small><b>{displayDate(project.start_date)}</b></span><span><small>End</small><b>{displayDate(project.end_date)}</b></span><span><small>Renewal</small><b>{displayDate(project.renewal_date)}</b></span><span><small>Revenue recorded</small><b>{displayMoney(projectRevenue)}</b></span></div>
          <h3>Connected records</h3><div className="entity-link-grid"><button onClick={() => setTab("People")}><UsersRound/><b>{engagement.team.length + engagement.stakeholders.length}</b><span>People</span></button><button onClick={() => setTab("Delivery")}><Flag/><b>{projectMilestones.length}</b><span>Milestones</span></button><button onClick={() => setTab("Commercial & staffing")}><BriefcaseBusiness/><b>{projectResourcing.requirements.length}</b><span>Open roles</span></button><button onClick={() => setTab("Delivery")}><CalendarDays/><b>{engagement.meetings.length}</b><span>Meetings</span></button></div>
        </>}
        {engagement && tab === "People" && <div className="entity-split">
          <section><h3>Client stakeholders</h3><div className="entity-records">{engagement.stakeholders.length ? engagement.stakeholders.map((item) => <button key={item.id} onClick={() => open(onStakeholder, { id: item.id })}><span><b>{item.name}</b><small>{item.title} · {item.relationship_role}{item.is_primary ? " · Primary" : ""}</small></span><ExternalLink /></button>) : empty("No client stakeholders are linked.")}</div></section>
          <section><h3>Assigned Capco team</h3><div className="entity-records">{engagement.team.length ? engagement.team.map((item) => <button key={item.id} onClick={() => open(onEmployee, item.id)}><span><b>{item.name}</b><small>{item.role} · {item.level} · {item.allocation_percent}%</small></span><ExternalLink /></button>) : empty("No Capco employees are assigned.")}</div></section>
        </div>}
        {engagement && tab === "Delivery" && <div className="entity-split">
          <section><h3>Delivery milestones</h3><div className="entity-records">{projectMilestones.length ? projectMilestones.map((item) => <article key={item.id}><span><b>{item.title}</b><small>{displayDate(item.due_date)} · {item.status}</small></span></article>) : empty("No delivery milestones are linked.")}</div><h3>Linked meetings</h3><div className="entity-records">{engagement.meetings.length ? engagement.meetings.map((item) => <button key={item.id} onClick={() => open(onMeeting, item.id, project.pod_id)}><span><b>{item.subject}</b><small>{displayDate(item.meeting_date)}</small></span><ExternalLink /></button>) : empty("No meetings are linked through this engagement's opportunity.")}</div></section>
          <section><h3>Risks and critical items</h3><div className="entity-records">{projectRisks.length ? projectRisks.map((item) => <article key={item.id} className={`entity-risk ${item.severity?.toLowerCase()}`}><span><b>{item.title}</b><small>{item.severity} · {item.status} · {displayDate(item.due_date)}</small></span><p>{item.description}</p></article>) : empty("No critical items are linked.")}</div></section>
        </div>}
        {engagement && tab === "Commercial & staffing" && <div className="entity-split">
          <section><h3>Commercial connection</h3>{engagement.opportunity ? <div className="entity-records"><button onClick={() => open(onOpportunity, engagement.opportunity.id, project.pod_id)}><span><b>{engagement.opportunity.name}</b><small>{engagement.opportunity.stage} · {displayMoney(engagement.opportunity.estimated_value)} · {engagement.opportunity.probability}%</small></span><ExternalLink /></button></div> : empty("No canonical opportunity is linked.")}<h3>Recognized revenue</h3><div className="entity-records compact">{engagement.revenue?.length ? engagement.revenue.map((item) => <article key={item.id}><span><b>{displayMoney(item.amount)}</b><small>{displayDate(item.recognized_on)}</small></span></article>) : empty("No revenue records are linked.")}</div></section>
          <section><h3>Resource requirements</h3><div className="entity-records">{projectResourcing.requirements.length ? projectResourcing.requirements.map((item) => <button key={item.id} onClick={() => open(onResourcing, project.pod_id)}><span><b>{item.title}</b><small>{item.status} · {item.requested_headcount} requested · {displayDate(item.target_start_date)}</small></span><ExternalLink /></button>) : empty("No resource requirements are linked.")}</div>{(projectResourcing.candidates.length > 0 || projectResourcing.onboarding.length > 0) && <button className="entity-primary-link" onClick={() => open(onResourcing, project.pod_id)}>Open resourcing &amp; onboarding <ExternalLink/></button>}</section>
        </div>}
      </div>
    </section>
  </div>;
}

function AddStakeholderModal({ pod, data, onClose, onCreated }) {
  const dialogRef = useRef(null);
  useDialogAccessibility(dialogRef, onClose);
  const [form, setForm] = useState({ name: "", title: "", division: data.people[0]?.division || "Front Office", business_unit: data.people[0]?.businessUnit || "Equities", team_type: "Business", manager_id: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const divisions = [...new Set(data.people.map((person) => person.division).filter((value) => value && value !== "Enterprise Functions"))];
  const units = [...new Set(data.people.filter((person) => person.division === form.division).map((person) => person.businessUnit).filter(Boolean))];
  const managerOptions = data.people.map((person) => ({ ...person, label: `${person.name} — ${person.title} (${person.division || "Pod leadership"} / ${person.businessUnit || "Not applicable"})` }));
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  const submit = async (event) => {
    event.preventDefault(); setSaving(true); setError("");
    try { const record = await api.createStakeholder({ ...form, pod, manager_id: form.manager_id || null }); onCreated(record); onClose(); }
    catch (requestError) { setError(requestError.message); }
    finally { setSaving(false); }
  };
  return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><form ref={dialogRef} className="modal" role="dialog" aria-modal="true" aria-labelledby="add-stakeholder-title" onSubmit={submit}><button type="button" className="modal-close" onClick={onClose} aria-label="Close add stakeholder dialog"><X /></button><h2 id="add-stakeholder-title">Add stakeholder</h2><p>Create a new organizational assignment.</p><label>Full name<input data-dialog-initial-focus required value={form.name} onChange={(event) => update("name", event.target.value)} /></label><label>Title<input required value={form.title} onChange={(event) => update("title", event.target.value)} /></label><label>Division<select value={form.division} onChange={(event) => { const next = event.target.value; const nextUnits = [...new Set(data.people.filter((person) => person.division === next).map((person) => person.businessUnit).filter(Boolean))]; setForm({ ...form, division: next, business_unit: nextUnits[0] || "" }); }}>{divisions.map((item) => <option key={item}>{item}</option>)}</select></label><label>Business unit<select value={form.business_unit} onChange={(event) => update("business_unit", event.target.value)}>{units.map((item) => <option key={item}>{item}</option>)}</select></label><label>Team<select value={form.team_type} onChange={(event) => update("team_type", event.target.value)}><option>Business</option><option>Technology</option></select></label><label>Manager <small>Optional selection; defaults to the governed subdomain manager.</small><SearchableSelect ariaLabel="Manager for new stakeholder" value={form.manager_id} onChange={(value) => update("manager_id", value)} options={managerOptions} allowClear placeholder="Use governed default" /></label>{error && <div className="form-error" role="alert">{error}</div>}<button className="modal-submit" disabled={saving}>{saving ? "Saving…" : "Add person"}</button></form></div>;
}

function GlobalSearchDialog({ pod, onClose, onSelect }) {
  const dialogRef = useRef(null);
  useDialogAccessibility(dialogRef, onClose);
  const [value, setValue] = useState("");
  const [groups, setGroups] = useState({});
  const [state, setState] = useState("idle");
  useEffect(() => {
    if (value.trim().length < 2) { setGroups({}); setState("idle"); return undefined; }
    let active = true; setState("loading");
    const timer = setTimeout(() => api.search(value.trim(), pod).then((result) => {
      if (active) { setGroups(result.groups); setState("ready"); }
    }).catch(() => { if (active) setState("error"); }), 180);
    return () => { active = false; clearTimeout(timer); };
  }, [value, pod]);
  const count = Object.values(groups).reduce((total, rows) => total + rows.length, 0);
  return <div className="global-search-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section ref={dialogRef} className="global-search-dialog" role="dialog" aria-modal="true" aria-label="Search account data"><header><Search/><input data-dialog-initial-focus value={value} onChange={(event) => setValue(event.target.value)} placeholder="Search stakeholders, meetings, opportunities, projects…"/><button onClick={onClose} aria-label="Close search"><X/></button></header><div className="global-search-results" aria-live="polite">{state === "idle" && <p>Enter at least two characters to search the canonical account data.</p>}{state === "loading" && <p>Searching account records…</p>}{state === "error" && <p role="alert">Search is temporarily unavailable. Try again.</p>}{state === "ready" && !count && <p>No matching account records.</p>}{Object.entries(groups).map(([group, rows]) => rows.length ? <section key={group}><h3>{group}<span>{rows.length}</span></h3>{rows.map((item) => <button key={`${item.type}-${item.id}`} onClick={() => onSelect(item)}><span><b>{item.label}</b><small>{item.context}</small></span><em>{item.pod || "Account"}</em></button>)}</section> : null)}</div></section></div>;
}

function App() {
  const initialPreferences = useRef(loadWorkspacePreferences()).current;
  const route = useRef(initialRoute(initialPreferences)).current;
  const [preferences, setPreferences] = useState(initialPreferences);
  const [pod, setPod] = useState(route.pod);
  const [view, setView] = useState("Map View");
  const [topSection, setTopSection] = useState(route.section);
  const [drawerRequest, setDrawerRequest] = useState(null);
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState({ ...DEFAULT_FILTERS, division: route.division, unit: route.businessUnit });
  const [editMode, setEditMode] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [leftCollapsed, setLeftCollapsed] = useState(() => typeof window.matchMedia === "function" && window.matchMedia("(max-width: 850px)").matches);
  const [rightCollapsed, setRightCollapsed] = useState(true);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const mobileNavTriggerRef = useRef(null);
  const mobileNavRef = useRef(null);
  const mobileNavWasOpen = useRef(false);
  const [backendMap, setBackendMap] = useState(null);
  const [filterOptions, setFilterOptions] = useState(null);
  const [coverageState, setCoverageState] = useState({ status: "idle", data: null, error: "" });
  const [coverageReload, setCoverageReload] = useState(0);
  const [mapState, setMapState] = useState("loading");
  const [mapError, setMapError] = useState("");
  const [mapReload, setMapReload] = useState(0);
  const [searchOpen, setSearchOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [dataFocus, setDataFocus] = useState(() => route.meeting ? { type: "meeting", id: route.meeting } : route.opportunity ? { type: "opportunity", id: route.opportunity } : null);
  const [session, setSession] = useState(null);
  const [accountDetail, setAccountDetail] = useState(null);
  const [accountDetailError, setAccountDetailError] = useState("");
  const mapPod = pod === "All" ? null : pod;
  const data = backendMap?.pod === mapPod ? backendMap.data : emptyMap;
  const rows = useMemo(() => flattenPeople(data), [data]);
  const filteredRows = useMemo(() => filterStakeholderRows(rows, query, filters), [rows, query, filters]);
  const [selected, setSelected] = useState(null);
  const [mapFocusRequest, setMapFocusRequest] = useState(null);
  const [pendingPodStakeholder, setPendingPodStakeholder] = useState(null);
  useEffect(() => {
    if (!mobileNavOpen) {
      if (mobileNavWasOpen.current) mobileNavTriggerRef.current?.focus();
      mobileNavWasOpen.current = false;
      return undefined;
    }
    mobileNavWasOpen.current = true;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const focusable = () => [...(mobileNavRef.current?.querySelectorAll("button") || [])];
    const focusTimer = window.setTimeout(() => (focusable().find((item) => item.classList.contains("active")) || focusable()[0])?.focus(), 0);
    const onKeyDown = (event) => {
      if (event.key === "Escape") { event.preventDefault(); setMobileNavOpen(false); return; }
      if (event.key !== "Tab") return;
      const items = focusable();
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      window.clearTimeout(focusTimer);
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [mobileNavOpen]);
  useEffect(() => { api.getSession().then(setSession).catch(() => setSession(null)); }, []);
  useEffect(() => {
    if (route.employee) api.getEmployeeProfile(route.employee).then(data => setAccountDetail({ type: "employee", data })).catch(() => setAccountDetailError("The linked employee profile could not be loaded."));
    else if (route.engagement) api.getEngagement(route.engagement).then(data => setAccountDetail({ type: "engagement", data })).catch(() => setAccountDetailError("The linked engagement could not be loaded."));
  }, [route.employee, route.engagement]);
  useEffect(() => {
    let active = true;
    setBackendMap(null);
    if (!mapPod) { setMapState("scope-required"); setMapError(""); return () => { active = false; }; }
    setMapState("loading");
    setMapError("");
    api.getMap(mapPod).then((response) => {
      if (active) { setBackendMap({ pod: mapPod, data: adaptBackendMap(response) }); setMapState("ready"); }
    }).catch((requestError) => {
      if (active) { setBackendMap(null); setMapState("error"); setMapError(requestError.message || "Stakeholder data could not be loaded."); }
    });
    return () => { active = false; };
  }, [mapPod, mapReload]);
  useEffect(() => {
    let active = true;
    setFilterOptions(null);
    api.getFilterOptions(mapPod).then((response) => { if (active) setFilterOptions(response); }).catch(() => { if (active) setFilterOptions(null); });
    return () => { active = false; };
  }, [mapPod]);
  useEffect(() => {
    if (view !== "Heat Map" || !["Stakeholder Map"].includes(topSection)) return undefined;
    let active = true;
    setCoverageState({ status: "loading", data: null, error: "" });
    api.getCoverage(mapPod).then((response) => { if (active) setCoverageState({ status: "ready", data: response, error: "" }); }).catch((error) => { if (active) setCoverageState({ status: "error", data: null, error: error.message || "Coverage data could not be loaded." }); });
    return () => { active = false; };
  }, [mapPod, view, topSection, coverageReload]);
  const previousPod = useRef(pod);
  useEffect(() => {
    setSelected(null);
    setRightCollapsed(true);
    if (previousPod.current !== pod) setFilters(DEFAULT_FILTERS);
    previousPod.current = pod;
  }, [pod]);
  const select = (personRecord, context, options = {}) => {
    setSelected({ person: personRecord, division: context.division, unit: context.unit, teamType: context.teamType });
    setRightCollapsed(false);
    if (options.focus) setMapFocusRequest({ id: personRecord.id, key: Date.now() });
  };
  useEffect(() => {
    if (!pendingPodStakeholder || pendingPodStakeholder.record.pod !== pod) return;
    const { record } = pendingPodStakeholder;
    select(adaptBackendStakeholder(record), { division: record.division, unit: record.business_unit, teamType: record.team_type }, { focus: true });
    setDrawerRequest({ tab: "Overview", key: Date.now() });
    setPendingPodStakeholder(null);
  }, [pod, pendingPodStakeholder]);
  const panelMode = Number(leftCollapsed) + Number(rightCollapsed);
  const topItems = ["Executive View", "Pod View", "Stakeholder Map", "Resourcing & Onboarding", "Account Data", "Settings"];
  const openTopSection = (item) => {
    setMobileNavOpen(false);
    setTopSection(item);
    setDataFocus(null);
    setAccountDetail(null);
    setAccountDetailError("");
    if (item !== "Stakeholder Map") setSelected(null);
    if (item === "Pod View" || item === "Stakeholder Map") setView("Map View");
  };
  const workspaceEyebrow = topSection === "Stakeholder Map" ? `${(mapPod || "ALL PODS").toUpperCase()} / ORGANIZATIONAL INTELLIGENCE` : "PERSONAL WORKSPACE";
  const workspaceTitle = topSection === "Stakeholder Map" ? "Stakeholder Map" : "Settings";
  const workspaceSubtitle = topSection === "Stakeholder Map" ? "Reporting structure, relationship coverage, and technology ownership." : "Identity, access, and personal map preferences.";
  const isPodView = topSection === "Pod View";
  const isExecutiveView = topSection === "Executive View";
  const isResourcingView = topSection === "Resourcing & Onboarding";
  const isManageData = topSection === "Account Data";
  const showMapChrome = topSection === "Stakeholder Map";
  const isFullWidth = isPodView || isExecutiveView || isResourcingView || isManageData;
  const dataInitialSection = dataFocus?.type === "meeting" ? "Meetings" : dataFocus?.type === "opportunity" ? "Commercial pipeline" : "Critical items";
  const openDataRecord = (type, id, nextPod) => {
    if (!id) return;
    if (nextPod && nextPod !== "All") setPod(nextPod);
    setSelected(null);
    setAccountDetail(null);
    setAccountDetailError("");
    setDataFocus({ type, id });
    setTopSection("Account Data");
  };
  const openEmployeeDetail = async (id) => {
    setAccountDetailError("");
    try { setAccountDetail({ type: "employee", data: await api.getEmployeeProfile(id) }); }
    catch { setAccountDetailError("The selected employee profile could not be loaded."); }
  };
  const openEngagementDetail = async (id) => {
    setAccountDetailError("");
    try { setAccountDetail({ type: "engagement", data: await api.getEngagement(id) }); }
    catch { setAccountDetailError("The selected engagement could not be loaded."); }
  };
  const openResourcing = (nextPod) => {
    if (nextPod && nextPod !== "All") setPod(nextPod);
    setAccountDetail(null);
    setTopSection("Resourcing & Onboarding");
  };
  const openNotification = async (item) => {
    const route = item.route || {};
    if (route.type === "engagement") return openEngagementDetail(route.id);
    if (route.type === "opportunity") return openDataRecord("opportunity", route.id, item.pod);
    if (route.type === "stakeholder") return openPodStakeholder({ id: route.id });
    if (route.type === "resourcing") return openResourcing(item.pod || pod);
    setTopSection("Executive View");
  };
  const openPodStakeholder = async (podPerson) => {
    if (!podPerson?.id) return false;
    let record;
    try { record = await api.getStakeholder(podPerson.id); }
    catch { return false; }
    if (!record || record.id !== podPerson.id || (pod !== "All" && record.pod !== pod)) return false;
    if (pod === "All") {
      setPendingPodStakeholder({ record });
      setPod(record.pod);
      setTopSection("Stakeholder Map");
      setView("Map View");
      return true;
    }
    select(adaptBackendStakeholder(record), { division: record.division, unit: record.business_unit, teamType: record.team_type }, { focus: true });
    setTopSection("Stakeholder Map");
    setView("Map View");
    setDrawerRequest({ tab: "Overview", key: Date.now() });
    return true;
  };
  const openSearchResult = async (item) => {
    setSearchOpen(false);
    if (item.type === "stakeholder") {
      try {
        const record = await api.getStakeholder(item.id);
        setPendingPodStakeholder({ record }); setPod(record.pod); setTopSection("Stakeholder Map"); setView("Map View");
      } catch { setMapError("The selected stakeholder could not be loaded."); }
      return;
    }
    if (item.pod) setPod(item.pod);
    if (item.type === "pod") { setTopSection("Pod View"); return; }
    if (item.type === "executive") { setTopSection("Executive View"); return; }
    if (item.type === "meeting") { openDataRecord("meeting", item.id, item.pod); return; }
    if (item.type === "opportunity") { openDataRecord("opportunity", item.id, item.pod); return; }
    if (item.type === "business_unit") { setFilters({ ...DEFAULT_FILTERS, unit: item.label }); setTopSection("Stakeholder Map"); return; }
    if (item.type === "employee") { await openEmployeeDetail(item.id); return; }
    if (item.type === "engagement") { await openEngagementDetail(item.id); return; }
    if (item.type === "resource_requirement" || item.type === "candidate") { openResourcing(item.pod); return; }
    setTopSection("Executive View");
  };
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    params.set("section", sectionKeys[topSection]);
    params.set("pod", pod);
    if (topSection === "Stakeholder Map" && selected?.person.id) params.set("stakeholder", selected.person.id); else params.delete("stakeholder");
    if (filters.division !== "All") params.set("division", filters.division); else params.delete("division");
    if (filters.unit !== "All") params.set("businessUnit", filters.unit); else params.delete("businessUnit");
    if (dataFocus?.type === "meeting") params.set("meeting", dataFocus.id); else params.delete("meeting");
    if (dataFocus?.type === "opportunity") params.set("opportunity", dataFocus.id); else params.delete("opportunity");
    if (accountDetail?.type === "employee") params.set("employee", accountDetail.data.id); else params.delete("employee");
    if (accountDetail?.type === "engagement") params.set("engagement", accountDetail.data.engagement.id); else params.delete("engagement");
    window.history.replaceState({}, "", `${window.location.pathname}?${params}${window.location.hash}`);
  }, [topSection, pod, selected?.person.id, filters.division, filters.unit, dataFocus?.type, dataFocus?.id, accountDetail]);
  useEffect(() => { document.title = `${topSection} · Morgan Stanley Account Intelligence`; }, [topSection]);
  const initialStakeholderHandled = useRef(false);
  useEffect(() => {
    if (initialStakeholderHandled.current || !route.stakeholder || mapState !== "ready") return;
    const row = rows.find((item) => item.person.id === route.stakeholder);
    initialStakeholderHandled.current = true;
    if (row) select(row.person, row, { focus: true });
  }, [mapState, rows, route.stakeholder]);
  const assistantEntity = accountDetail
    ? { type: accountDetail.type, id: accountDetail.data?.id || accountDetail.data?.engagement?.id || null }
    : isManageData && dataFocus
      ? { type: dataFocus.type, id: dataFocus.id }
      : topSection === "Stakeholder Map" && selected
        ? { type: "stakeholder", id: selected.person.id }
        : { type: null, id: null };
  return (
    <div className={`app-shell ${leftCollapsed || !showMapChrome ? "left-collapsed" : ""} ${rightCollapsed || !showMapChrome ? "right-collapsed" : ""} ${isFullWidth ? "pod-shell" : ""} ${showMapChrome ? "map-section" : ""} ${topSection === "Settings" ? "settings-section" : ""} ${preferences.compactTooltips ? "compact-tooltips" : "expanded-tooltips"}`}>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <header className="top-navigation">
        <div className="brand">Morgan Stanley</div>
        <button ref={mobileNavTriggerRef} className="mobile-nav-trigger" onClick={() => setMobileNavOpen((current) => !current)} aria-expanded={mobileNavOpen} aria-controls="primary-navigation" aria-label={mobileNavOpen ? "Close navigation" : "Open navigation"}><Menu /></button>
        <nav ref={mobileNavRef} id="primary-navigation" aria-label="Primary navigation" className={mobileNavOpen ? "open" : ""}>{topItems.map((item) => <button key={item} className={topSection === item ? "active" : ""} onClick={() => openTopSection(item)}>{item}</button>)}</nav>
        <div className="global-actions"><label>Select pod:<select value={pod} onChange={(event) => setPod(event.target.value)}><option>All</option><option>ISG</option><option>Wealth Management</option><option>MSIM</option></select></label><button aria-label="Open account alerts" title="Account alerts" onClick={() => setNotificationsOpen(true)}><Bell /></button><button aria-label="Search account data" title="Search account data" onClick={() => setSearchOpen(true)}><Search /></button><span className="user-avatar" title={session?.roles?.join(", ")}>{session?.subject?.slice(0, 2).toUpperCase() || "…"}</span></div>
      </header>
      {mobileNavOpen && <button className="mobile-nav-backdrop" onClick={() => setMobileNavOpen(false)} aria-label="Close navigation" />}
      {showMapChrome && (!leftCollapsed || !rightCollapsed) && <button className="map-panel-backdrop" onClick={() => { setLeftCollapsed(true); setRightCollapsed(true); }} aria-label="Close map side panels" />}
      {showMapChrome && <ControlRail pod={pod} setPod={setPod} view={view} setView={(nextView) => { setView(nextView); setTopSection("Stakeholder Map"); }} filters={filters} setFilters={setFilters} data={data} filterOptions={filterOptions} onAdd={() => setAddOpen(true)} onCollapse={() => setLeftCollapsed(true)} canWrite={!!session?.permissions?.write && !!mapPod} />}
      <main id="main-content" tabIndex="-1" className={`workspace ${isExecutiveView ? "executive-workspace" : ""} ${isResourcingView ? "resourcing-workspace" : ""}`}>
        {!isFullWidth && <section className="workspace-header"><div><span className="workspace-eyebrow">{workspaceEyebrow}</span><h1>{workspaceTitle}</h1><p>{workspaceSubtitle}</p></div><div className="workspace-actions">{showMapChrome && leftCollapsed && <button onClick={() => setLeftCollapsed(false)} aria-label="Open control rail"><PanelLeftOpen /> Filters</button>}{topSection === "Stakeholder Map" && session?.permissions?.write && <button onClick={() => setAddOpen(true)}><Plus /> Add person</button>}{topSection === "Stakeholder Map" && session?.permissions?.write && <button className={editMode ? "active" : ""} onClick={() => setEditMode(!editMode)}><Pencil /> {editMode ? "Finish editing" : "Edit map"}</button>}{topSection === "Stakeholder Map" && <label className="global-search"><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search people or teams…" />{query && <button onClick={() => setQuery("")}><X /></button>}</label>}</div></section>}
        {isPodView ? (
          <PodView pod={pod} onOpenStakeholder={openPodStakeholder} onOpenResourcing={() => openResourcing(pod)} canWrite={session?.permissions?.write} currentEmployeeId={session?.employee_id||""} currentUserName={session?.subject||""} />
        ) : isResourcingView ? (
          <ResourcingView pod={pod} canWrite={!!session?.permissions?.write} canManageCommercial={!!session?.roles?.some((role) => ["Account Manager", "Account Admin"].includes(role))} currentEmployeeId={session?.employee_id || ""} />
        ) : isManageData ? (
          <DataManagement pod={pod} initialSection={dataInitialSection} focus={dataFocus} canWrite={session?.permissions?.write} canAdmin={!!session?.roles?.includes("Account Admin")} />
        ) : topSection === "Settings" ? (
          <SettingsView preferences={preferences} session={session} onChange={(changes) => setPreferences((current) => saveWorkspacePreferences({ ...current, ...changes }))} onReset={() => { setPreferences(resetWorkspacePreferences()); setFilters(DEFAULT_FILTERS); setView("Map View"); setTopSection("Stakeholder Map"); }} />
        ) : isExecutiveView ? (
          <ExecutiveView
            pod={pod}
            onOpenPod={(nextPod) => { setPod(nextPod); setTopSection("Pod View"); }}
            onOpenStakeholder={openPodStakeholder}
            onOpenEmployee={openEmployeeDetail}
            onOpenEngagement={openEngagementDetail}
            onOpenMeeting={(id, nextPod) => openDataRecord("meeting", id, nextPod)}
            onOpenOpportunity={(id, nextPod) => openDataRecord("opportunity", id, nextPod)}
            onOpenResourcing={(nextPod) => openResourcing(nextPod || pod)}
          />
        ) : mapState === "scope-required" ? (
          <div className="map-data-state"><ShieldCheck/><h2>Select a pod to view the stakeholder map</h2><p>All-pod scope is intentionally not mapped to a hidden default. Choose ISG, Wealth Management, or MSIM.</p></div>
        ) : mapState === "loading" ? (
          <div className="map-data-state"><span className="map-skeleton"/><h2>Loading the canonical stakeholder map</h2><p>Resolving organization assignments and reporting lines…</p></div>
        ) : mapState === "error" ? (
          <div className="map-data-state error"><ShieldCheck/><h2>Stakeholder database unavailable</h2><p>{mapError}</p><button onClick={() => setMapReload((value) => value + 1)}>Retry connection</button></div>
        ) : view === "Map View" ? (
          <MapCanvas data={data} query={query} filters={filters} onSelect={select} editMode={editMode} panelMode={panelMode} selectedId={selected?.person.id} focusRequest={mapFocusRequest} />
        ) : (
          <SecondaryView type={view} rows={filteredRows} total={rows.length} onSelect={select} pod={mapPod} coverageState={coverageState} filters={filters} onRetryCoverage={() => setCoverageReload((value) => value + 1)} />
        )}
      </main>
      {showMapChrome && <LiveStakeholderDrawer selected={selected} pod={mapPod} editMode={editMode} canWrite={!!session?.permissions?.write} confirmChanges={preferences.confirmChanges} requestedTab={drawerRequest} onCollapse={() => setRightCollapsed(true)} onMapChanged={(stakeholderId) => { setMapFocusRequest({ id: stakeholderId, key: Date.now() }); setMapReload((value) => value + 1); }} />}
      {showMapChrome && rightCollapsed && selected && <button className="sidebar-reopen reopen-right" onClick={() => setRightCollapsed(false)} aria-label="Open stakeholder drawer" title="Open stakeholder drawer"><PanelRightOpen /></button>}
      {addOpen && mapPod && <AddStakeholderModal pod={mapPod} data={data} onClose={() => setAddOpen(false)} onCreated={(record) => { select(adaptBackendStakeholder(record), { division: record.division, unit: record.business_unit, teamType: record.team_type }, { focus: true }); setMapReload((value) => value + 1); }} />}
      {searchOpen && <GlobalSearchDialog pod={pod} onClose={() => setSearchOpen(false)} onSelect={openSearchResult} />}
      {notificationsOpen && <NotificationCenter pod={pod} onClose={() => setNotificationsOpen(false)} onSelect={openNotification} />}
      {accountDetail && <AccountEntityDialog
        detail={accountDetail}
        onClose={() => setAccountDetail(null)}
        onStakeholder={(item) => { setAccountDetail(null); openPodStakeholder(item); }}
        onEmployee={openEmployeeDetail}
        onEngagement={openEngagementDetail}
        onMeeting={(id, nextPod) => openDataRecord("meeting", id, nextPod)}
        onOpportunity={(id, nextPod) => openDataRecord("opportunity", id, nextPod)}
        onResourcing={openResourcing}
      />}
      {accountDetailError && <div className="pod-toast error-state" role="alert"><AlertTriangle />{accountDetailError}<button onClick={() => setAccountDetailError("")} aria-label="Dismiss error"><X /></button></div>}
      <AccountAssistant
        context={{
          pod,
          section: topSection,
          entity_type: assistantEntity.type,
          entity_id: assistantEntity.id,
        }}
        onNavigate={(navigation) => { setAccountDetail(null); openSearchResult(navigation); }}
      />
    </div>
  );
}

export { AccountEntityDialog, LiveDrawerSection, SecondaryView, SettingsView };
export default App;
