import React, { useEffect, useMemo, useRef, useState } from "react";
import { hierarchy, tree } from "d3-hierarchy";
import {
  BriefcaseBusiness, Building2, CalendarDays, ChevronDown, CircleDollarSign,
  Crosshair, FileChartColumn, Filter, Flame, Focus, Grid2X2,
  Download, ExternalLink, FileText, Hand, Layers3, List, Map as MapIcon, Maximize2, Menu, MousePointer2, Network,
  NotebookPen, Pencil, Plus, RotateCcw, Search, Settings, ShieldCheck,
  Sparkles, Tag, Trash2, UserRound, UsersRound, X, ZoomIn, ZoomOut,
  PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen,
} from "lucide-react";
import { api } from "./api";
import { adaptBackendMap, adaptBackendStakeholder } from "./mapAdapter";
import DataManagement from "./DataManagement";
import PodView from "./PodView";
import ExecutiveView from "./ExecutiveView";
import AccountAssistant from "./AccountAssistant";

const viewItems = [
  { name: "Map View", icon: MapIcon },
  { name: "List View", icon: List },
  { name: "Heat Map", icon: Flame },
  { name: "Influence Map", icon: Network },
];
const drawerTabs = ["Overview", "Meetings", "Team", "Notes", "Documents", "Opportunities", "Bio"];
const defaultFilters = {
  division: "All", unit: "All", teamType: "All", location: "All", level: "All",
  influence: "All", budget: "All", relationship: "All", owner: "All",
  recency: "All", opportunities: "All", tags: "All",
};

const emptyMap = { title: "Stakeholder Map", divisions: [], enterprise: [] };
const initials = (name = "") => name.split(" ").filter(Boolean).map((part) => part[0]).slice(0, 2).join("");
function flattenPeople(data) {
  const rows = [];
  const walk = (person, context) => {
    if (!person) return;
    rows.push({ person, ...context });
    (person.reports || []).forEach((report) => walk(report, context));
  };
  data.divisions.forEach((division) => {
    walk(division.head, { division: division.name, unit: "Division Leadership", teamType: "Business" });
    division.units.forEach((unit) => {
      const context = { division: division.name, unit: unit.name, teamType: "Business" };
      walk(unit.lead, context);
      unit.unknownReports.forEach((person) => walk(person, context));
      walk(unit.primaryTechnology, { ...context, teamType: "Technology" });
    });
  });
  data.enterprise.forEach((group) => {
    const context = { division: "Enterprise Functions", unit: group.name, teamType: "Business" };
    walk(group.lead, context);
    group.members.forEach((person) => walk(person, context));
  });
  return rows;
}

const sectionKeys = {
  "Executive View": "executive", "Pod View": "pod", "Stakeholder Map": "stakeholders",
  Meetings: "meetings", Opportunities: "opportunities", Settings: "settings",
};
const sectionNames = Object.fromEntries(Object.entries(sectionKeys).map(([name, key]) => [key, name]));
function initialRoute() {
  const query = new URLSearchParams(window.location.search);
  const requestedPod = query.get("pod");
  const section = sectionNames[query.get("section")] || "Executive View";
  const validPod = ["All", "ISG", "Wealth Management", "MSIM"].includes(requestedPod) ? requestedPod : "All";
  return {
    pod: validPod === "All" && !["Executive View", "Pod View"].includes(section) ? "ISG" : validPod,
    section,
    stakeholder: query.get("stakeholder"),
    meeting: query.get("meeting"),
    opportunity: query.get("opportunity"),
    employee: query.get("employee"),
    engagement: query.get("engagement"),
    division: query.get("division") || "All",
    businessUnit: query.get("businessUnit") || "All",
  };
}

function CountryFlag({ country, location }) {
  const code = country === "UK" ? "GB" : country;
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
      <span><b>Division</b>{context.division}</span>
      <span><b>Business unit</b>{context.unit}</span>
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
      <span className="node-avatar">{initials(stakeholder.name)}</span>
      {stakeholder.capcoContacts > 0 && <sup>{stakeholder.capcoContacts}</sup>}
      <span className="node-copy"><strong>{stakeholder.name}</strong><small>{stakeholder.title}</small></span>
      <CountryFlag country={stakeholder.country} location={stakeholder.location} />
      <PersonTooltip stakeholder={stakeholder} context={context} />
    </button>
  );
}

function TreeChart({ stakeholder, context, onSelect, matches, selectedId, enterprise = false }) {
  const layout = useMemo(() => {
    const root = hierarchy(stakeholder, (item) => item.reports || []);
    tree().nodeSize([92, 82]).separation((left, right) => left.parent === right.parent ? 1 : 1.12)(root);
    const descendants = root.descendants();
    const minX = Math.min(...descendants.map((node) => node.x));
    const maxX = Math.max(...descendants.map((node) => node.x));
    const naturalWidth = maxX - minX + 110;
    const width = Math.max(300, naturalWidth);
    const contentOffset = (width - naturalWidth) / 2;
    const height = Math.max(74, Math.max(...descendants.map((node) => node.y)) + 72);
    const nodes = descendants.map((node) => ({ ...node, drawX: node.x - minX + 55 + contentOffset, drawY: node.y + 2 }));
    const byData = new Map(nodes.map((node) => [node.data.id, node]));
    const links = root.links().map((link) => ({ source: byData.get(link.source.data.id), target: byData.get(link.target.data.id) }));
    return { nodes, links, width, height };
  }, [stakeholder]);
  return (
    <div className={`org-tree-d3 ${enterprise ? "enterprise-tree" : ""}`} style={{ height: `${layout.height}px`, minWidth: `${layout.width}px` }}>
      <svg className="org-links" viewBox={`0 0 ${layout.width} ${layout.height}`} preserveAspectRatio="xMidYMin meet" aria-hidden="true">
        {layout.links.map(({ source, target }) => {
          const sourceBottom = source.drawY + 62;
          const midpoint = sourceBottom + Math.max(5, (target.drawY - sourceBottom) / 2);
          return <path key={`${source.data.id}-${target.data.id}`} d={`M ${source.drawX} ${sourceBottom} V ${midpoint} H ${target.drawX} V ${target.drawY}`} />;
        })}
      </svg>
      <div className="org-node-layer" style={{ width: `${layout.width}px`, height: `${layout.height}px` }}>
        {layout.nodes.map((node) => (
          <div key={node.data.id} className="positioned-org-node" style={{ left: `${node.drawX}px`, top: `${node.drawY}px` }}>
            <StakeholderNode stakeholder={node.data} context={context} onSelect={onSelect} muted={!matches(node.data, context)} selected={node.data.id===selectedId} variant={node.depth === 0 ? (enterprise ? "enterprise-lead" : "manager") : node.children?.length ? "manager" : "standard"} />
          </div>
        ))}
      </div>
    </div>
  );
}

function BusinessUnit({ businessUnit, division, onSelect, matches, selectedId }) {
  const businessContext = { division: division.name, unit: businessUnit.name, teamType: "Business" };
  const technologyContext = { ...businessContext, teamType: "Technology" };
  return (
    <article className="business-unit" style={{ "--lane-accent": division.color }}>
      <header className="unit-heading">
        <strong>{businessUnit.name}</strong>
        <span>Business Team <em>(Stakeholders)</em></span>
        <span>Technology <em>(Primary Stakeholder)</em></span>
      </header>
      <div className="unit-content">
        <section className="business-org" aria-label={`${businessUnit.name} business reporting structure`}>
          <div className="org-tree">
            <TreeChart stakeholder={businessUnit.lead} context={businessContext} onSelect={onSelect} matches={matches} selectedId={selectedId} />
          </div>
          {businessUnit.unknownReports.length > 0 && (
            <div className="unknown-reporting">
              <span>Reporting line unknown</span>
              <div>
                {businessUnit.unknownReports.map((stakeholder) => (
                  <StakeholderNode key={stakeholder.id} stakeholder={stakeholder} context={businessContext} onSelect={onSelect} muted={!matches(stakeholder, businessContext)} selected={stakeholder.id===selectedId} />
                ))}
              </div>
            </div>
          )}
        </section>
        <section className="technology-primary">
          <span className="primary-eyebrow">Primary technology stakeholder</span>
          <StakeholderNode stakeholder={businessUnit.primaryTechnology} context={technologyContext} onSelect={onSelect} muted={!matches(businessUnit.primaryTechnology, technologyContext)} selected={businessUnit.primaryTechnology.id===selectedId} variant="technology" />
          <span className="team-count">+{businessUnit.primaryTechnology.reports.length} team members</span>
          <small>View reports in profile</small>
        </section>
      </div>
    </article>
  );
}

function DivisionLane({ division, onSelect, matches, unitVisible, selectedId }) {
  const context = { division: division.name, unit: "Division Leadership", teamType: "Business" };
  return (
    <section className="division-lane" style={{ "--lane-accent": division.color }}>
      <div className="division-heading">
        <span className="division-title"><UsersRound /> {division.name.toUpperCase()}</span>
        <StakeholderNode stakeholder={division.head} context={context} onSelect={onSelect} muted={!matches(division.head, context)} selected={division.head.id===selectedId} variant="division-head" />
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
              <h3><BriefcaseBusiness /> {group.name}</h3>
              <div className="enterprise-org">
                <div className="enterprise-lead-box">
                  <StakeholderNode stakeholder={group.lead} context={context} onSelect={onSelect} muted={!matches(group.lead, context)} selected={group.lead.id===selectedId} variant="enterprise-lead" />
                </div>
                <div className="enterprise-report-row" style={{ "--report-count": group.members.length }}>
                  {group.members.map((stakeholder) => (
                    <div className="enterprise-report" key={stakeholder.id}>
                      <StakeholderNode stakeholder={stakeholder} context={context} onSelect={onSelect} muted={!matches(stakeholder, context)} selected={stakeholder.id===selectedId} />
                    </div>
                  ))}
                </div>
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
      <span className="mini-enterprise" />
      <i className="mini-viewport" style={{ transform: `translate(${Math.max(0, -offset.x / 18)}px, ${Math.max(0, -offset.y / 18)}px)`, width: `${Math.max(38, 82 / zoom)}px`, height: `${Math.max(22, 45 / zoom)}px` }} />
    </div>
  );
}

function MapCanvas({ data, query, filters, onSelect, editMode, panelMode, selectedId, focusRequest }) {
  const viewportRef = useRef(null);
  const worldRef = useRef(null);
  const defaultZoom = panelMode === 2 ? 0.75 : panelMode === 1 ? 0.66 : 0.58;
  const [zoom, setZoom] = useState(defaultZoom);
  const [offset, setOffset] = useState({ x: 18, y: 14 });
  const [drag, setDrag] = useState(null);
  const [tool, setTool] = useState("select");

  const matches = (stakeholder, context) => {
    if (stakeholder.id === selectedId) return true;
    const haystack = `${stakeholder.name} ${stakeholder.title} ${context.division} ${context.unit} ${stakeholder.tags.join(" ")}`.toLowerCase();
    if (query && !haystack.includes(query.toLowerCase())) return false;
    if (filters.teamType !== "All" && context.teamType !== filters.teamType) return false;
    if (filters.location !== "All" && stakeholder.location !== filters.location) return false;
    if (filters.level !== "All" && stakeholder.level !== filters.level) return false;
    if (filters.influence === "Buyer" && !stakeholder.buyer) return false;
    if (filters.influence === "Influencer" && !stakeholder.influencer) return false;
    if (filters.budget === "Yes" && !stakeholder.budgetHolder) return false;
    if (filters.relationship !== "All" && stakeholder.relationship !== filters.relationship) return false;
    if (filters.owner !== "All" && stakeholder.capcoOwner !== filters.owner) return false;
    if (filters.recency !== "All") {
      const meetingDate = Date.parse(stakeholder.lastMeeting);
      const today = new Date(); today.setHours(0,0,0,0);
      const daysSinceMeeting = Number.isNaN(meetingDate) ? Infinity : (today.getTime() - meetingDate) / 86400000;
      if (filters.recency === "Last 30 days" && daysSinceMeeting > 30) return false;
      if (filters.recency === "Last 90 days" && daysSinceMeeting > 90) return false;
      if (filters.recency === "No recent meeting" && daysSinceMeeting <= 90) return false;
    }
    if (filters.opportunities === "Has opportunities" && stakeholder.opportunityCount < 1) return false;
    if (filters.tags !== "All" && !stakeholder.tags.includes(filters.tags)) return false;
    return true;
  };
  const hasActivePersonFilter = query || ["teamType", "location", "level", "influence", "budget", "relationship", "owner", "recency", "opportunities", "tags"].some((key) => filters[key] !== "All");
  const unitVisible = (businessUnit, division) => {
    const containsSelected = (stakeholder) => stakeholder.id === selectedId || stakeholder.reports.some(containsSelected);
    if (selectedId && (containsSelected(businessUnit.lead) || businessUnit.unknownReports.some(containsSelected) || containsSelected(businessUnit.primaryTechnology))) return true;
    if (filters.division !== "All" && filters.division !== division.name) return false;
    if (filters.unit !== "All" && filters.unit !== businessUnit.name) return false;
    if (!hasActivePersonFilter) return true;
    const context = { division: division.name, unit: businessUnit.name, teamType: "Business" };
    const walk = (stakeholder, teamContext = context) => matches(stakeholder, teamContext) || stakeholder.reports.some((report) => walk(report, teamContext));
    return walk(businessUnit.lead) || businessUnit.unknownReports.some((stakeholder) => matches(stakeholder, context)) || walk(businessUnit.primaryTechnology, { ...context, teamType: "Technology" });
  };
  const setZoomClamped = (value) => setZoom(Math.min(1.35, Math.max(0.42, value)));
  const fit = () => {
    if (!viewportRef.current || !worldRef.current) return;
    const next = Math.min((viewportRef.current.clientWidth - 34) / worldRef.current.offsetWidth, (viewportRef.current.clientHeight - 34) / worldRef.current.offsetHeight, 1);
    setZoomClamped(next);
    setOffset({ x: 17, y: 17 });
  };
  const reset = () => { setZoom(defaultZoom); setOffset({ x: 18, y: 14 }); };
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
    const next = Math.min(1.35, Math.max(0.42, zoom * (event.deltaY > 0 ? 0.92 : 1.08)));
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
  return (
    <div className={`map-viewport ${drag ? "dragging" : ""} ${editMode ? "edit-mode" : ""}`} ref={viewportRef} onWheel={onWheel} onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={() => setDrag(null)} onPointerCancel={() => setDrag(null)}>
      <div className="canvas-toolbar">
        <button className={tool === "select" ? "active" : ""} onClick={() => setTool("select")} title="Select"><MousePointer2 /></button>
        <button className={tool === "pan" ? "active" : ""} onClick={() => setTool("pan")} title="Pan"><Hand /></button>
        <button onClick={() => setZoomClamped(zoom * 1.12)} title="Zoom in"><ZoomIn /></button>
        <button onClick={() => setZoomClamped(zoom / 1.12)} title="Zoom out"><ZoomOut /></button>
        <button onClick={fit} title="Fit to screen"><Focus /></button>
        <button onClick={reset} title="Reset view"><RotateCcw /></button>
        <span>{Math.round(zoom * 100)}%</span>
      </div>
      <div className="map-world" ref={worldRef} style={{ transform: `translate(${offset.x}px, ${offset.y}px) scale(${zoom})` }}>
        <div className="division-grid">
          {data.divisions.map((division) => <DivisionLane key={division.id} division={division} onSelect={onSelect} matches={matches} unitVisible={unitVisible} selectedId={selectedId} />)}
        </div>
        <EnterpriseFunctions groups={data.enterprise} onSelect={onSelect} matches={matches} selectedId={selectedId} />
      </div>
      <MiniMap data={data} zoom={zoom} offset={offset} />
      <div className="canvas-hint">Drag to pan · Scroll to zoom</div>
    </div>
  );
}

const formatDate = (value) => value ? new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value)) : "Not scheduled";
const formatMoney = (value) => value == null ? "Not recorded" : new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
const slug = (value) => value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

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

function LiveDrawerSection({ tab, profile, candidates, editMode, onRefresh, onChanged }) {
  const { stakeholder, team, meetings, notes, documents = [], opportunities } = profile;
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

  const run = async (operation, message) => {
    setSaving(true); setError("");
    try { await operation(); setPanel(""); setEditingNote(null); setEditingDocument(null); await onRefresh(); onChanged(message); }
    catch (requestError) { setError(requestError.message); }
    finally { setSaving(false); }
  };
  const editProfile = (payload) => run(() => api.updateStakeholder(stakeholder.id, payload), "Profile saved");

  if (panel === "profile") return <div className="drawer-tab-content"><h4>Edit stakeholder profile</h4><ProfileForm stakeholder={stakeholder} onSave={editProfile} onCancel={() => setPanel("")} saving={saving} />{error && <div className="form-error">{error}</div>}</div>;

  if (tab === "Meetings") return <div className="drawer-tab-content"><div className="section-title"><h4>Meeting history</h4><button onClick={() => setPanel(panel === "meeting" ? "" : "meeting")}><Plus /> Add</button></div>
    {panel === "meeting" && <form className="drawer-form compact-form" onSubmit={(event) => { event.preventDefault(); run(() => api.createPodMeeting(stakeholder.pod, { ...meeting, meeting_date: new Date(`${meeting.meeting_date}T14:00:00`).toISOString(), stakeholder_ids: [stakeholder.id], organizer: "Capco Account Team", capco_attendees: [stakeholder.capco_owner || "Priya Shah"], next_steps: [], tags: meeting.tags.split(",").map(value => value.trim()).filter(Boolean) }), "Meeting added to the profile and Pod View"); }}><label>Subject<input required value={meeting.subject} onChange={(event) => setMeeting({ ...meeting, subject: event.target.value })} /></label><label>Date<input required type="date" value={meeting.meeting_date} onChange={(event) => setMeeting({ ...meeting, meeting_date: event.target.value })} /></label><label>Summary<textarea rows="3" value={meeting.summary} onChange={(event) => setMeeting({ ...meeting, summary: event.target.value })} /></label><label>Outcome<input value={meeting.outcome} onChange={(event) => setMeeting({ ...meeting, outcome: event.target.value })} /></label><label>Tags <small>Comma separated</small><input value={meeting.tags} onChange={(event) => setMeeting({ ...meeting, tags: event.target.value })}/></label><div className="form-actions"><button type="button" onClick={() => setPanel("")}>Cancel</button><button className="primary-action" disabled={saving}>Save meeting</button></div></form>}
    {meetings.length ? <div className="activity">{meetings.map((item) => <React.Fragment key={item.id}><i /><span><b>{formatDate(item.meeting_date)} · {item.subject}</b>{item.summary || item.outcome}</span></React.Fragment>)}</div> : <p className="empty-note">No meetings recorded.</p>}{error && <div className="form-error">{error}</div>}</div>;

  if (tab === "Team") {
    const managerOptions = candidates.filter((item) => item.id !== stakeholder.id && item.business_unit === stakeholder.business_unit);
    const unitId = `${slug(stakeholder.pod)}-${slug(stakeholder.division)}-${slug(stakeholder.business_unit)}`;
    return <div className="drawer-tab-content team-tab"><div className="section-title"><h4>Reporting structure</h4>{editMode && <span className="edit-chip">Editing</span>}</div>
      <label>Manager</label>{editMode ? <div className="inline-editor"><select value={managerId} onChange={(event) => setManagerId(event.target.value)}><option value="">Reporting line unknown</option>{managerOptions.map((item) => <option key={item.id} value={item.id}>{item.name} — {item.title}</option>)}</select><button className="primary-action" disabled={saving || managerId === (team.manager?.id || "")} onClick={() => run(() => api.updateReportingLine({ report_id: stakeholder.id, manager_id: managerId || null, reason: "Updated in stakeholder map" }), "Reporting line saved")}>Save</button></div> : <div className="team-manager">{team.manager ? `${team.manager.name} — ${team.manager.title}` : "Reporting line not confirmed"}</div>}
      <label>Direct reports <span>{team.direct_reports.length}</span></label>{team.direct_reports.length ? <div className="report-list">{team.direct_reports.map((report, index) => <div key={report.id}><i>{index === team.direct_reports.length - 1 ? "└" : "├"}</i><span><b>{report.name}</b><small>{report.title}</small></span></div>)}</div> : <p className="empty-note">No confirmed direct reports.</p>}
      {stakeholder.team_type === "Technology" && <div className="primary-tech-card"><b>{team.is_primary_technology ? "Primary technology stakeholder" : "Technology team member"}</b><p>{team.is_primary_technology ? "This person is the visible technology owner for the business unit." : "This person is in the full team but is not the unit's primary technology owner."}</p>{editMode && !team.is_primary_technology && <button className="primary-action" disabled={saving} onClick={() => run(() => api.updatePrimaryTechnology(unitId, { stakeholder_id: stakeholder.id, reason: "Updated in stakeholder map" }), "Primary technology owner updated")}>Make primary technology</button>}</div>}
      {!editMode && <p className="editing-hint">Turn on <b>Edit map</b> to change reporting lines and technology ownership.</p>}{error && <div className="form-error">{error}</div>}</div>;
  }

  if (tab === "Notes") return <div className="drawer-tab-content"><div className="section-title"><h4>Relationship notes</h4><button onClick={() => setPanel(panel === "note" ? "" : "note")}><Plus /> Add</button></div>
    {panel === "note" && <form className="drawer-form compact-form" onSubmit={(event) => { event.preventDefault(); run(() => api.createNote(stakeholder.id, { ...note, author: "Current User" }), "Note added"); }}><label>Category<select value={note.category} onChange={(event) => setNote({ ...note, category: event.target.value })}><option>Relationship</option><option>Opportunity</option><option>Meeting</option><option>General</option></select></label><label>Note<textarea required rows="4" value={note.body} onChange={(event) => setNote({ ...note, body: event.target.value })} /></label><div className="form-actions"><button type="button" onClick={() => setPanel("")}>Cancel</button><button className="primary-action" disabled={saving}>Save note</button></div></form>}
    <div className="note-list">{notes.map((item) => editingNote?.id === item.id ? <form key={item.id} className="drawer-form compact-form" onSubmit={(event) => { event.preventDefault(); run(() => api.updateNote(item.id, { body: editingNote.body, category: editingNote.category }), "Note updated"); }}><textarea required rows="4" value={editingNote.body} onChange={(event) => setEditingNote({ ...editingNote, body: event.target.value })} /><div className="form-actions"><button type="button" onClick={() => setEditingNote(null)}>Cancel</button><button className="primary-action" disabled={saving}>Update</button></div></form> : <article key={item.id}><span>{item.category} · {formatDate(item.updated_at)}</span><p>{item.body}</p><div className="record-actions"><button onClick={() => setEditingNote(item)}><Pencil /> Edit</button><button className="danger-action" onClick={() => window.confirm("Delete this sensitive note? This cannot be undone.") && run(() => api.deleteNote(item.id), "Note deleted")}><Trash2 /> Delete</button></div></article>)}</div>{!notes.length && <p className="empty-note">No notes recorded.</p>}{error && <div className="form-error">{error}</div>}</div>;

  if (tab === "Documents") return <div className="drawer-tab-content">
    <div className="section-title"><h4>Stakeholder documents</h4><button onClick={() => setPanel(panel === "document" ? "" : "document")}><Plus /> Upload</button></div>
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
    </form> : <article key={item.id}><FileText/><div><span>{item.document_type} · {formatDate(item.updated_at)}</span><b>{item.title}</b><p>{item.description || `Owned by ${item.owner}`}</p><small>{item.file_name ? `${item.file_name}${item.file_size ? ` · ${(item.file_size / 1024).toFixed(0)} KB` : ""}` : "Shared link only"}</small>{item.tags?.length>0&&<div className="drawer-tags">{item.tags.map(value=><span key={value}>{value}</span>)}</div>}</div><div className="document-actions">{item.stored_name && <a href={api.documentDownloadUrl(item.id)}><Download /> Download</a>}{(item.sharepoint_url || item.url) && <a href={item.sharepoint_url || item.url} target="_blank" rel="noreferrer"><ExternalLink /> SharePoint</a>}<button onClick={() => setEditingDocument({ ...item, sharepoint_url: item.sharepoint_url || item.url || "" })}><Pencil /> Edit</button><button className="danger-action" onClick={() => window.confirm("Remove this document and its stored file? This cannot be undone.") && run(() => api.deleteDocument(item.id), "Document removed")}><Trash2 /> Remove</button></div></article>)}</div>
    {!documents.length && <p className="empty-note">No documents uploaded for this stakeholder.</p>}{error && <div className="form-error">{error}</div>}
  </div>;

  if (tab === "Opportunities") return <div className="drawer-tab-content"><div className="section-title"><h4>Potential opportunities</h4><button onClick={() => setPanel(panel === "opportunity" ? "" : "opportunity")}><Plus /> Add</button></div>
    {panel === "opportunity" && <form className="drawer-form compact-form" onSubmit={(event) => { event.preventDefault(); run(() => api.createOpportunity({ ...opportunity, estimated_value: Number(opportunity.estimated_value || 0), probability: Number(opportunity.probability), stakeholder_ids: [stakeholder.id], owner: "Capco Account Team", target_close_date: null, tags: opportunity.tags.split(",").map(value => value.trim()).filter(Boolean) }), "Opportunity added"); }}><label>Name<input required value={opportunity.name} onChange={(event) => setOpportunity({ ...opportunity, name: event.target.value })} /></label><div className="form-row"><label>Estimated value<input type="number" min="0" value={opportunity.estimated_value} onChange={(event) => setOpportunity({ ...opportunity, estimated_value: event.target.value })} /></label><label>Probability<input type="number" min="0" max="100" value={opportunity.probability} onChange={(event) => setOpportunity({ ...opportunity, probability: event.target.value })} /></label></div><label>Stage<select value={opportunity.stage} onChange={(event) => setOpportunity({ ...opportunity, stage: event.target.value })}><option>Discovery</option><option>Qualification</option><option>Proposal</option><option>Negotiation</option><option>Closed Won</option><option>Closed Lost</option></select></label><label>Description<textarea rows="3" value={opportunity.description} onChange={(event) => setOpportunity({ ...opportunity, description: event.target.value })} /></label><label>Tags <small>Comma separated</small><input value={opportunity.tags} onChange={(event) => setOpportunity({ ...opportunity, tags: event.target.value })}/></label><div className="form-actions"><button type="button" onClick={() => setPanel("")}>Cancel</button><button className="primary-action" disabled={saving}>Save opportunity</button></div></form>}
    {opportunities.map((item) => <div className="opportunity" key={item.id}><b>{item.name}</b><span>{item.stage} · {formatMoney(item.estimated_value)}</span><strong>{item.probability}%</strong></div>)}{!opportunities.length && <p className="empty-note">No active opportunities.</p>}{error && <div className="form-error">{error}</div>}</div>;

  if (tab === "Bio") return <div className="drawer-tab-content"><div className="section-title"><h4>Biography</h4><button onClick={() => setPanel("profile")}><Pencil /> Edit</button></div><p>{stakeholder.biography || "No biography has been added."}</p><h4>Areas of expertise</h4><div className="drawer-tags">{(stakeholder.tags || []).map((tagName) => <span key={tagName}>{tagName}</span>)}</div></div>;

  return <div className="drawer-tab-content overview-tab"><dl><dt>Division</dt><dd>{stakeholder.division}</dd><dt>Business unit</dt><dd>{stakeholder.business_unit}</dd><dt>Team</dt><dd>{stakeholder.team_type}</dd><dt>Location</dt><dd>{stakeholder.location}</dd><dt>Level</dt><dd>{stakeholder.level}</dd><dt>Last meeting</dt><dd>{formatDate(stakeholder.last_meeting_at)}</dd><dt>Next meeting</dt><dd>{formatDate(stakeholder.next_meeting_at)}</dd><dt>Capco owner</dt><dd className="link-value">{stakeholder.capco_owner || "Unassigned"}</dd></dl><div className="drawer-divider" /><div className="section-title"><span>Stakeholder profile</span><button onClick={() => setPanel("profile")}><Pencil /> Edit</button></div><div className="profile-fields"><span>Role</span><b>{stakeholder.is_buyer ? "Buyer" : stakeholder.is_influencer ? "Influencer" : "Stakeholder"}</b><span>Has budget</span><b>{stakeholder.is_budget_holder ? "Yes" : "No"}</b><span>Budget amount</span><b>{formatMoney(stakeholder.budget_amount)}</b><span>Relationship</span><b>{stakeholder.relationship_strength}</b></div><div className="drawer-divider" /><h4>Latest intelligence</h4><p>{notes[0]?.body || stakeholder.biography || "No relationship intelligence recorded."}</p></div>;
}

function LiveStakeholderDrawer({ selected, pod, editMode, requestedTab, onCollapse }) {
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
      const nextCandidates = await api.getStakeholders({ pod, business_unit: nextProfile.stakeholder.business_unit, limit: 500 });
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
  return <aside className="stakeholder-drawer"><button className="drawer-close" onClick={onCollapse} aria-label="Collapse stakeholder drawer" title="Collapse stakeholder drawer"><PanelRightClose /></button><section className="drawer-profile"><div className="profile-avatar">{initials(person.name)}<sup>{selected.person.capcoContacts || 1}</sup></div><div><h2>{person.name}</h2>{(person.is_buyer ?? selected.person.buyer) && <span className="buyer-badge">Buyer / decision-maker</span>}<strong>{person.title}</strong><p>{person.division || selected.division} · {person.business_unit || selected.unit}<br />{person.location}</p></div></section><div className="drawer-tags">{tags.slice(0, 4).map((tagName) => <span key={tagName}>{tagName}</span>)}</div>{editMode && <div className="edit-mode-banner"><Pencil /> Map editing is on</div>}<nav className="drawer-tabs">{drawerTabs.map((item) => <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>{item}</button>)}</nav>{notice && <div className="save-notice">{notice}</div>}{loading && !profile && <div className="api-state"><span className="loading-dot" /> Loading stakeholder intelligence...</div>}{error && !loading && <div className="api-state error-state"><b>Backend profile unavailable</b><span>{error}</span><button onClick={loadProfile}>Retry</button></div>}{profile && <LiveDrawerSection tab={tab} profile={profile} candidates={candidates} editMode={editMode} onRefresh={loadProfile} onChanged={setNotice} />}</aside>;
}

function ControlRail({ pod, setPod, view, setView, filters, setFilters, data, onAdd, onCollapse, canWrite }) {
  const allRows = flattenPeople(data);
  const units = [...new Set(data.divisions.flatMap((division) => division.units.map((businessUnit) => businessUnit.name)))];
  const selectFilter = (label, key, values) => (
    <label className="rail-filter"><span>{label}</span><select value={filters[key]} onChange={(event) => setFilters({ ...filters, [key]: event.target.value })}>{values.map((value) => <option key={value}>{value}</option>)}</select></label>
  );
  return (
    <aside className="control-rail">
      <button className="rail-collapse" onClick={onCollapse} aria-label="Collapse control rail" title="Collapse control rail"><PanelLeftClose /></button>
      <section><label className="rail-label">Pod selection</label><select className="pod-select" value={pod} onChange={(event) => setPod(event.target.value)}><option>ISG</option><option>Wealth Management</option><option>MSIM</option></select></section>
      <section><label className="rail-label">Views</label>{viewItems.map(({ name, icon: Icon }) => <button key={name} className={`view-button ${view === name ? "active" : ""}`} onClick={() => setView(name)}><Icon /> {name}</button>)}</section>
      <section className="filter-section"><label className="rail-label"><Filter /> Filters</label>
        {selectFilter("Division", "division", ["All", ...data.divisions.map((division) => division.name)])}
        {selectFilter("Business unit", "unit", ["All", ...units])}
        {selectFilter("Business / Technology", "teamType", ["All", "Business", "Technology"])}
        {selectFilter("Location", "location", ["All", ...new Set(allRows.map((row) => row.person.location))])}
        {selectFilter("Level", "level", ["All", "Managing Director", "Executive Director", "Vice President", "Director", "Associate"])}
        {selectFilter("Buyer / Influencer", "influence", ["All", "Buyer", "Influencer"])}
        {selectFilter("Budget holder", "budget", ["All", "Yes"])}
        {selectFilter("Relationship strength", "relationship", ["All", "Strong", "Medium", "Developing"])}
        {selectFilter("Capco relationship owner", "owner", ["All", "Alex Morgan"])}
        {selectFilter("Meeting recency", "recency", ["All", "Last 30 days", "Last 90 days", "No recent meeting"])}
        {selectFilter("Opportunities", "opportunities", ["All", "Has opportunities"])}
        {selectFilter("Expertise / interest tags", "tags", ["All", "Digital Assets", "Data", "Trading", "Automation", "Cloud"])}
        <button className="clear-filters" onClick={() => setFilters(defaultFilters)}>Clear all filters</button>
      </section>
      <section className="legend-section"><label className="rail-label">Map indicators</label><span><i className="legend-tech" /> Primary technology</span><span><i className="legend-capco">2</i> Capco contacts</span><span><i className="legend-flag" /> Stakeholder location</span><small>Buyer and budget details appear in the profile and hover view.</small></section>
      {canWrite && <button className="rail-add" onClick={onAdd}><Plus /> Add person</button>}
    </aside>
  );
}

function SecondaryView({ type, rows, onSelect, pod }) {
  if (type === "Heat Map") return <div className="secondary-view"><h2>Relationship coverage</h2><p>{pod} · organizational intelligence coverage by business unit</p><div className="coverage-grid">{[...new Set(rows.map((row) => row.unit))].filter((unitName) => unitName !== "Division Leadership").map((unitName, index) => <div key={unitName}><b>{unitName}</b><span>{rows.filter((row) => row.unit === unitName).length} stakeholders</span><strong className={index % 3 === 0 ? "medium" : "strong"}>{index % 3 === 0 ? "Medium" : "Strong"}</strong></div>)}</div></div>;
  if (type === "Influence Map") return <div className="secondary-view"><h2>Influence map</h2><p>Relationship influence is visualized separately from formal reporting lines.</p><div className="influence-view">{rows.slice(0, 16).map((row) => <button key={row.person.id} onClick={() => onSelect(row.person, row)}><span>{initials(row.person.name)}</span><b>{row.person.name}</b><small>{row.person.buyer ? "Buyer · Sponsor" : "Influencer"}</small></button>)}</div></div>;
  return <div className="secondary-view"><h2>Stakeholder directory</h2><p>{pod} · {rows.length} known stakeholders</p><div className="list-table"><div><b>Name</b><b>Division</b><b>Business unit</b><b>Team</b><b>Relationship</b></div>{rows.map((row) => <button key={`${row.person.id}-${row.unit}`} onClick={() => onSelect(row.person, row)}><span>{row.person.name}<small>{row.person.title}</small></span><span>{row.division}</span><span>{row.unit}</span><span>{row.teamType}</span><span>{row.person.relationship}</span></button>)}</div></div>;
}

function SettingsView({ pod, setPod, onReset, session }) {
  const [compactTooltips, setCompactTooltips] = useState(true);
  const [confirmChanges, setConfirmChanges] = useState(true);
  return <div className="secondary-view settings-view"><h2>Workspace settings</h2><p>Identity, access, and personal map preferences for this browser session.</p><div className="settings-card"><div className="session-summary"><ShieldCheck/><span><b>{session?.subject || "Loading identity…"}</b><small>{session?.roles?.join(" · ") || "Resolving application roles"}</small></span><em>{session?.permissions?.write ? "Can edit" : "Read only"}</em></div><label><span>Default pod<small>Controls the organization loaded in the map.</small></span><select value={pod} onChange={(event) => setPod(event.target.value)}><option>ISG</option><option>Wealth Management</option><option>MSIM</option></select></label><label><span>Compact hover details<small>Keep stakeholder tooltips dense on large maps.</small></span><input type="checkbox" checked={compactTooltips} onChange={(event) => setCompactTooltips(event.target.checked)} /></label><label><span>Confirm organization changes<small>Show save controls before reporting-line updates.</small></span><input type="checkbox" checked={confirmChanges} onChange={(event) => setConfirmChanges(event.target.checked)} /></label><button onClick={onReset}><RotateCcw /> Reset map preferences</button></div></div>;
}

function AccountEntityDialog({ detail, onClose, onStakeholder }) {
  useEffect(() => {
    const handleKey = (event) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);
  if (!detail) return null;
  const employee = detail.type === "employee" ? detail.data : null;
  const engagement = detail.type === "engagement" ? detail.data : null;
  const title = employee?.name || engagement?.engagement?.name || "Account record";
  return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className="entity-detail-dialog" role="dialog" aria-modal="true" aria-label={`${title} details`}><button className="modal-close" onClick={onClose} aria-label="Close details"><X/></button><span className="detail-kicker">{employee ? "CAPCO EMPLOYEE" : "CLIENT ENGAGEMENT"}</span><h2>{title}</h2>{employee ? <><p>{employee.role} · {employee.level} · {employee.location}</p><div className="entity-metrics"><span><b>{employee.assignments.length}</b>Engagements</span><span><b>{employee.stakeholder_relationships.filter(item => item.is_current).length}</b>Relationships</span><span><b>{employee.meetings.length}</b>Meetings</span><span><b>{employee.owned_opportunities.length}</b>Opportunities</span></div><h3>Capabilities</h3><div className="drawer-tags">{employee.skills.map(value => <span key={value}>{value}</span>)}</div><h3>Active engagement assignments</h3><div className="entity-records">{employee.assignments.map(item => <article key={item.id}><b>{item.engagement_name}</b><small>{item.pod_id} · {item.allocation_percent}% allocation · {item.billable ? "Billable" : "Non-billable"}</small></article>)}</div><h3>Stakeholder relationships</h3><div className="entity-records">{employee.stakeholder_relationships.filter(item => item.is_current).map(item => <button key={item.id} onClick={() => onStakeholder({ id: item.stakeholder_id })}><b>{item.stakeholder_name}</b><small>{item.relationship_role}{item.is_primary ? " · Primary" : ""}</small></button>)}</div></> : <><p>{engagement.engagement.pod_id} · {engagement.engagement.division} · {engagement.engagement.business_unit}</p><div className="entity-metrics"><span><b>{engagement.engagement.health}</b>Health</span><span><b>{engagement.team.length}</b>Team</span><span><b>{engagement.stakeholders.length}</b>Stakeholders</span><span><b>{engagement.meetings.length}</b>Linked meetings</span></div><h3>Client stakeholders</h3><div className="entity-records">{engagement.stakeholders.map(item => <button key={item.id} onClick={() => onStakeholder({ id: item.id })}><b>{item.name}</b><small>{item.title} · {item.relationship_role}</small></button>)}</div><h3>Assigned Capco team</h3><div className="entity-records">{engagement.team.map(item => <article key={item.id}><b>{item.name}</b><small>{item.role} · {item.allocation_percent}% allocation</small></article>)}</div></>}</section></div>;
}

function AddStakeholderModal({ pod, data, onClose, onCreated }) {
  const [form, setForm] = useState({ name: "", title: "", division: data.divisions[0].name, business_unit: data.divisions[0].units[0].name, team_type: "Business" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const division = data.divisions.find((item) => item.name === form.division) || data.divisions[0];
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  const submit = async (event) => {
    event.preventDefault(); setSaving(true); setError("");
    try { const record = await api.createStakeholder({ ...form, pod }); onCreated({ person: { ...record, id: record.id, reports: [], tags: [], capcoContacts: 0, relationship: "Developing", lastMeeting: "Not recorded", nextMeeting: "Not scheduled", country: "US" }, division: record.division, unit: record.business_unit, teamType: record.team_type }); onClose(); }
    catch (requestError) { setError(requestError.message); }
    finally { setSaving(false); }
  };
  return <div className="modal-backdrop"><form className="modal" onSubmit={submit}><button type="button" className="modal-close" onClick={onClose}><X /></button><h2>Add stakeholder</h2><p>Create a new organizational assignment.</p><label>Full name<input required value={form.name} onChange={(event) => update("name", event.target.value)} /></label><label>Title<input required value={form.title} onChange={(event) => update("title", event.target.value)} /></label><label>Division<select value={form.division} onChange={(event) => { const next = event.target.value; const nextDivision = data.divisions.find((item) => item.name === next); setForm({ ...form, division: next, business_unit: nextDivision.units[0].name }); }}>{data.divisions.map((item) => <option key={item.id}>{item.name}</option>)}</select></label><label>Business unit<select value={form.business_unit} onChange={(event) => update("business_unit", event.target.value)}>{division.units.map((item) => <option key={item.id}>{item.name}</option>)}</select></label><label>Team<select value={form.team_type} onChange={(event) => update("team_type", event.target.value)}><option>Business</option><option>Technology</option></select></label>{error && <div className="form-error">{error}</div>}<button className="modal-submit" disabled={saving}>{saving ? "Saving…" : "Add person"}</button></form></div>;
}

function GlobalSearchDialog({ pod, onClose, onSelect }) {
  const [value, setValue] = useState("");
  const [groups, setGroups] = useState({});
  const [state, setState] = useState("idle");
  useEffect(() => {
    const handleKey = (event) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);
  useEffect(() => {
    if (value.trim().length < 2) { setGroups({}); setState("idle"); return undefined; }
    let active = true; setState("loading");
    const timer = setTimeout(() => api.search(value.trim(), pod).then((result) => {
      if (active) { setGroups(result.groups); setState("ready"); }
    }).catch(() => { if (active) setState("error"); }), 180);
    return () => { active = false; clearTimeout(timer); };
  }, [value, pod]);
  const count = Object.values(groups).reduce((total, rows) => total + rows.length, 0);
  return <div className="global-search-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className="global-search-dialog" role="dialog" aria-modal="true" aria-label="Search account data"><header><Search/><input autoFocus value={value} onChange={(event) => setValue(event.target.value)} placeholder="Search stakeholders, meetings, opportunities, projects…"/><button onClick={onClose} aria-label="Close search"><X/></button></header><div className="global-search-results">{state === "idle" && <p>Enter at least two characters to search the canonical account data.</p>}{state === "loading" && <p>Searching account records…</p>}{state === "error" && <p>Search is temporarily unavailable. Try again.</p>}{state === "ready" && !count && <p>No matching account records.</p>}{Object.entries(groups).map(([group, rows]) => rows.length ? <section key={group}><h3>{group}<span>{rows.length}</span></h3>{rows.map((item) => <button key={`${item.type}-${item.id}`} onClick={() => onSelect(item)}><span><b>{item.label}</b><small>{item.context}</small></span><em>{item.pod || "Account"}</em></button>)}</section> : null)}</div></section></div>;
}

function App() {
  const route = useRef(initialRoute()).current;
  const [pod, setPod] = useState(route.pod);
  const [view, setView] = useState("Map View");
  const [topSection, setTopSection] = useState(route.section);
  const [drawerRequest, setDrawerRequest] = useState(null);
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState({ ...defaultFilters, division: route.division, unit: route.businessUnit });
  const [editMode, setEditMode] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(true);
  const [backendMap, setBackendMap] = useState(null);
  const [mapState, setMapState] = useState("loading");
  const [mapError, setMapError] = useState("");
  const [mapReload, setMapReload] = useState(0);
  const [searchOpen, setSearchOpen] = useState(false);
  const [dataFocus, setDataFocus] = useState(() => route.meeting ? { type: "meeting", id: route.meeting } : route.opportunity ? { type: "opportunity", id: route.opportunity } : null);
  const [session, setSession] = useState(null);
  const [accountDetail, setAccountDetail] = useState(null);
  const mapPod = pod === "All" ? "ISG" : pod;
  const data = backendMap?.pod === mapPod ? backendMap.data : emptyMap;
  const rows = useMemo(() => flattenPeople(data), [data]);
  const [selected, setSelected] = useState(null);
  const [mapFocusRequest, setMapFocusRequest] = useState(null);
  const [pendingPodStakeholder, setPendingPodStakeholder] = useState(null);
  useEffect(() => { api.getSession().then(setSession).catch(() => setSession(null)); }, []);
  useEffect(() => {
    if (route.employee) api.getEmployeeProfile(route.employee).then(data => setAccountDetail({ type: "employee", data })).catch(() => setMapError("The linked employee profile could not be loaded."));
    else if (route.engagement) api.getEngagement(route.engagement).then(data => setAccountDetail({ type: "engagement", data })).catch(() => setMapError("The linked engagement could not be loaded."));
  }, [route.employee, route.engagement]);
  useEffect(() => {
    let active = true;
    setBackendMap(null);
    setMapState("loading");
    setMapError("");
    api.getMap(mapPod).then((response) => {
      if (active) { setBackendMap({ pod: mapPod, data: adaptBackendMap(response) }); setMapState("ready"); }
    }).catch((requestError) => {
      if (active) { setBackendMap(null); setMapState("error"); setMapError(requestError.message || "Stakeholder data could not be loaded."); }
    });
    return () => { active = false; };
  }, [mapPod, mapReload]);
  const previousPod = useRef(pod);
  useEffect(() => {
    setSelected(null);
    setRightCollapsed(true);
    if (previousPod.current !== pod) setFilters(defaultFilters);
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
  const topItems = ["Executive View", "Pod View", "Stakeholder Map", "Meetings", "Opportunities", "Settings"];
  const openTopSection = (item) => {
    if (pod === "All" && !["Pod View", "Executive View"].includes(item)) setPod("ISG");
    setTopSection(item);
    setDataFocus(null);
    setAccountDetail(null);
    if (item === "Pod View" || item === "Stakeholder Map") setView("Map View");
  };
  const workspaceTitle = topSection === "Stakeholder Map" ? `${pod} Stakeholder Map` : `${pod} Settings`;
  const isPodView = topSection === "Pod View";
  const isExecutiveView = topSection === "Executive View";
  const isManageData = ["Meetings", "Opportunities"].includes(topSection);
  const isFullWidth = isPodView || isExecutiveView || isManageData;
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
    if (item.type === "meeting") { setDataFocus({ type: "meeting", id: item.id }); setTopSection("Meetings"); return; }
    if (item.type === "opportunity") { setDataFocus({ type: "opportunity", id: item.id }); setTopSection("Opportunities"); return; }
    if (item.type === "business_unit") { setFilters({ ...defaultFilters, unit: item.label }); setTopSection("Stakeholder Map"); return; }
    if (item.type === "employee") {
      try { setAccountDetail({ type: "employee", data: await api.getEmployeeProfile(item.id) }); }
      catch { setMapError("The selected employee profile could not be loaded."); }
      return;
    }
    if (item.type === "engagement") {
      try { setAccountDetail({ type: "engagement", data: await api.getEngagement(item.id) }); }
      catch { setMapError("The selected engagement could not be loaded."); }
      return;
    }
    setTopSection("Executive View");
  };
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    params.set("section", sectionKeys[topSection]);
    params.set("pod", pod);
    if (selected?.person.id) params.set("stakeholder", selected.person.id); else params.delete("stakeholder");
    if (filters.division !== "All") params.set("division", filters.division); else params.delete("division");
    if (filters.unit !== "All") params.set("businessUnit", filters.unit); else params.delete("businessUnit");
    if (dataFocus?.type === "meeting") params.set("meeting", dataFocus.id); else params.delete("meeting");
    if (dataFocus?.type === "opportunity") params.set("opportunity", dataFocus.id); else params.delete("opportunity");
    if (accountDetail?.type === "employee") params.set("employee", accountDetail.data.id); else params.delete("employee");
    if (accountDetail?.type === "engagement") params.set("engagement", accountDetail.data.engagement.id); else params.delete("engagement");
    window.history.replaceState({}, "", `${window.location.pathname}?${params}${window.location.hash}`);
  }, [topSection, pod, selected?.person.id, filters.division, filters.unit, dataFocus?.type, dataFocus?.id, accountDetail]);
  const initialStakeholderHandled = useRef(false);
  useEffect(() => {
    if (initialStakeholderHandled.current || !route.stakeholder || mapState !== "ready") return;
    const row = rows.find((item) => item.person.id === route.stakeholder);
    initialStakeholderHandled.current = true;
    if (row) select(row.person, row, { focus: true });
  }, [mapState, rows, route.stakeholder]);
  return (
    <div className={`app-shell ${leftCollapsed || isFullWidth ? "left-collapsed" : ""} ${rightCollapsed || isFullWidth ? "right-collapsed" : ""} ${isFullWidth ? "pod-shell" : ""}`}>
      <header className="top-navigation">
        <div className="brand">Morgan Stanley</div>
        <nav>{topItems.map((item) => <button key={item} className={topSection === item ? "active" : ""} onClick={() => openTopSection(item)}>{item}</button>)}</nav>
        <div className="global-actions"><label>Select pod:<select value={pod} onChange={(event) => setPod(event.target.value)}><option>All</option><option>ISG</option><option>Wealth Management</option><option>MSIM</option></select></label><button aria-label="Search account data" title="Search account data" onClick={() => setSearchOpen(true)}><Search /></button><span className="user-avatar" title={session?.roles?.join(", ")}>{session?.subject?.slice(0, 2).toUpperCase() || "…"}</span></div>
      </header>
      {!isFullWidth && <ControlRail pod={pod} setPod={setPod} view={view} setView={(nextView) => { setView(nextView); setTopSection("Stakeholder Map"); }} filters={filters} setFilters={setFilters} data={data} onAdd={() => setAddOpen(true)} onCollapse={() => setLeftCollapsed(true)} canWrite={session?.permissions?.write} />}
      <main className={`workspace ${isExecutiveView ? "executive-workspace" : ""}`}>
        {!isFullWidth && <section className="workspace-header"><div><h1>{workspaceTitle}</h1><p>Organizational intelligence · Reporting structure and technology ownership</p></div><div className="workspace-actions">{session?.permissions?.write && <button onClick={() => setAddOpen(true)}><Plus /> Add person</button>}{session?.permissions?.write && <button className={editMode ? "active" : ""} onClick={() => setEditMode(!editMode)}><Pencil /> {editMode ? "Finish editing" : "Edit map"}</button>}<label className="global-search"><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search people or teams…" />{query && <button onClick={() => setQuery("")}><X /></button>}</label></div></section>}
        {isPodView ? <PodView pod={pod} onOpenStakeholder={openPodStakeholder} canWrite={session?.permissions?.write} /> : isManageData ? <DataManagement pod={pod} initialSection={topSection === "Meetings" ? "Meetings" : "Commercial pipeline"} focus={dataFocus} canWrite={session?.permissions?.write} /> : topSection === "Settings" ? <SettingsView pod={pod} setPod={setPod} session={session} onReset={() => { setFilters(defaultFilters); setView("Map View"); setTopSection("Stakeholder Map"); }} /> : isExecutiveView ? <ExecutiveView pod={pod} onOpenPod={(nextPod) => { setPod(nextPod); setTopSection("Pod View"); }} onOpenStakeholder={openPodStakeholder} onOpenEmployee={async (id) => { try { setAccountDetail({ type: "employee", data: await api.getEmployeeProfile(id) }); } catch { setMapError("The selected employee profile could not be loaded."); } }} onOpenEngagement={async (id) => { try { setAccountDetail({ type: "engagement", data: await api.getEngagement(id) }); } catch { setMapError("The selected engagement could not be loaded."); } }} onOpenMeeting={(id) => { setDataFocus({ type: "meeting", id }); setTopSection("Meetings"); }} onOpenOpportunity={(id) => { setDataFocus({ type: "opportunity", id }); setTopSection("Opportunities"); }} /> : mapState === "loading" ? <div className="map-data-state"><span className="map-skeleton"/><h2>Loading the canonical stakeholder map</h2><p>Resolving organization assignments and reporting lines…</p></div> : mapState === "error" ? <div className="map-data-state error"><ShieldCheck/><h2>Stakeholder database unavailable</h2><p>{mapError}</p><button onClick={() => setMapReload((value) => value + 1)}>Retry connection</button></div> : view === "Map View" ? <MapCanvas data={data} query={query} filters={filters} onSelect={select} editMode={editMode} panelMode={panelMode} selectedId={selected?.person.id} focusRequest={mapFocusRequest} /> : <SecondaryView type={view} rows={rows} onSelect={select} pod={pod} />}
      </main>
      {!isFullWidth && <LiveStakeholderDrawer selected={selected} pod={pod} editMode={editMode} requestedTab={drawerRequest} onCollapse={() => setRightCollapsed(true)} />}
      {!isFullWidth && leftCollapsed && <button className="sidebar-reopen reopen-left" onClick={() => setLeftCollapsed(false)} aria-label="Open control rail" title="Open control rail"><PanelLeftOpen /></button>}
      {!isFullWidth && rightCollapsed && selected && <button className="sidebar-reopen reopen-right" onClick={() => setRightCollapsed(false)} aria-label="Open stakeholder drawer" title="Open stakeholder drawer"><PanelRightOpen /></button>}
      {addOpen && <AddStakeholderModal pod={pod} data={data} onClose={() => setAddOpen(false)} onCreated={setSelected} />}
      {searchOpen && <GlobalSearchDialog pod={pod} onClose={() => setSearchOpen(false)} onSelect={openSearchResult} />}
      {accountDetail && <AccountEntityDialog detail={accountDetail} onClose={() => setAccountDetail(null)} onStakeholder={(item) => { setAccountDetail(null); openPodStakeholder(item); }} />}
      <AccountAssistant
        context={{
          pod,
          section: topSection,
          entity_type: selected ? "stakeholder" : dataFocus?.type || accountDetail?.type || null,
          entity_id: selected?.person.id || dataFocus?.id || accountDetail?.data?.id || accountDetail?.data?.engagement?.id || null,
        }}
        onNavigate={(navigation) => { setAccountDetail(null); openSearchResult(navigation); }}
      />
    </div>
  );
}

export default App;
