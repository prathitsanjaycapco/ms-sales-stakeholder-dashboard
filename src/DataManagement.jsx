import React, { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle, BriefcaseBusiness, CalendarDays, Check, Database, FileUp,
  ShieldCheck, UsersRound,
} from "lucide-react";
import { api } from "./api";

const documentTypes = ["Proposal", "Meeting Brief", "Account Plan", "Contract", "Delivery", "Research", "Other"];
const opportunityStages = ["Discovery", "Qualification", "Proposal", "Negotiation", "Closed Won", "Closed Lost"];
const parseTags = (value) => value.split(",").map(item => item.trim()).filter(Boolean);

function localInputDate(offsetDays = 0, withTime = false) {
  const value = new Date();
  value.setDate(value.getDate() + offsetDays);
  const local = new Date(value.getTime() - value.getTimezoneOffset() * 60000).toISOString();
  return withTime ? local.slice(0, 16) : local.slice(0, 10);
}

function weekStartKey() {
  const value = new Date();
  value.setDate(value.getDate() - ((value.getDay() + 6) % 7));
  return localInputFromDate(value);
}

function localInputFromDate(value) {
  return new Date(value.getTime() - value.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function localDateTimeValue(value) {
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

function Field({ label, hint, children }) {
  return <label>{label}{hint && <small>{hint}</small>}{children}</label>;
}

function RecordSummary({ icon: Icon, title, description, count }) {
  return <article><Icon/><span><b>{title}</b><small>{description}</small></span><strong>{count}</strong></article>;
}

export default function DataManagement({ pod, initialSection = "Critical items", focus = null, canWrite = true }) {
  const [section, setSection] = useState(initialSection);
  const [people, setPeople] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [meetings, setMeetings] = useState([]);
  const [opportunities, setOpportunities] = useState([]);
  const [criticalItems, setCriticalItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [fileInputKey, setFileInputKey] = useState(0);
  const [editingCriticalId, setEditingCriticalId] = useState("");
  const [editingMeetingId, setEditingMeetingId] = useState("");
  const [editingOpportunityId, setEditingOpportunityId] = useState("");
  const [editingDocumentId, setEditingDocumentId] = useState("");
  const [targetDocuments, setTargetDocuments] = useState([]);
  const [critical, setCritical] = useState({ title: "", description: "", item_type: "ACCOUNT", severity: "AMBER", capco_owner: "", capco_owner_employee_id: "", due_date: localInputDate(3), stakeholder_id: "", opportunity_id: "", tags: "" });
  const [meeting, setMeeting] = useState({ subject: "", meeting_date: localInputDate(1, true), duration_minutes: 60, summary: "", stakeholder_id: "", organizer: "", organizer_employee_id: "", capco_attendee_ids: [], outcome: "Follow-up required", next_steps: "", event_type: "client", opportunity_id: "", prep_required: true, tags: "" });
  const [pipeline, setPipeline] = useState({ name: "", description: "", estimated_value: "", probability: 30, stage: "Discovery", stakeholder_id: "", owner: "", owner_employee_id: "", target_close_date: localInputDate(60), tags: "" });
  const [document, setDocument] = useState({ target_type: "stakeholder", target_id: "", title: "", file: null, sharepoint_url: "", document_type: "Account Plan", description: "", owner: "", owner_employee_id: "", tags: "" });

  const load = async () => {
    setLoading(true); setError("");
    try {
      const [stakeholderRows, employeeRows, meetingRows, opportunityRows, dashboard] = await Promise.all([
        api.getStakeholders({ pod }),
        api.getEmployees(),
        api.getPodMeetingOptions(pod),
        api.getOpportunities(),
        api.getPodDashboard(pod, "week", weekStartKey()),
      ]);
      const stakeholderIds = new Set(stakeholderRows.map(item => item.id));
      setPeople(stakeholderRows.sort((a, b) => a.name.localeCompare(b.name)));
      setEmployees(employeeRows);
      setMeetings(meetingRows);
      setOpportunities(opportunityRows.filter(item => item.stakeholder_ids.some(id => stakeholderIds.has(id))));
      setCriticalItems(dashboard.view_model?.criticalItems || []);
    } catch (requestError) {
      setError(requestError.message || "Account data could not be loaded.");
    } finally { setLoading(false); }
  };

  useEffect(() => {
    setSection(initialSection);
  }, [initialSection]);
  useEffect(() => {
    setEditingCriticalId(""); setEditingMeetingId(""); setEditingOpportunityId(""); setEditingDocumentId("");
    setCritical(value => ({ ...value, stakeholder_id: "", opportunity_id: "" }));
    setMeeting(value => ({ ...value, stakeholder_id: "", opportunity_id: "" }));
    setPipeline(value => ({ ...value, stakeholder_id: "" }));
    setDocument(value => ({ ...value, target_id: "", title: "", file: null }));
    load();
  }, [pod]);
  useEffect(() => {
    if (!people.length) return;
    const firstId = people[0].id;
    setCritical(value => ({ ...value, stakeholder_id: value.stakeholder_id || firstId }));
    setMeeting(value => ({ ...value, stakeholder_id: value.stakeholder_id || firstId }));
    setPipeline(value => ({ ...value, stakeholder_id: value.stakeholder_id || firstId }));
    setDocument(value => ({ ...value, target_id: value.target_id || firstId }));
  }, [people]);
  useEffect(() => {
    if (!employees.length) return;
    const primary = employees[0];
    const secondary = employees[1] || primary;
    setCritical(value => ({ ...value, capco_owner_employee_id: value.capco_owner_employee_id || primary.id, capco_owner: value.capco_owner || primary.name }));
    setMeeting(value => ({ ...value, organizer_employee_id: value.organizer_employee_id || primary.id, organizer: value.organizer || primary.name, capco_attendee_ids: value.capco_attendee_ids.length ? value.capco_attendee_ids : [primary.id, secondary.id] }));
    setPipeline(value => ({ ...value, owner_employee_id: value.owner_employee_id || primary.id, owner: value.owner || primary.name }));
    setDocument(value => ({ ...value, owner_employee_id: value.owner_employee_id || primary.id, owner: value.owner || primary.name }));
  }, [employees]);
  useEffect(() => {
    if (!notice) return undefined;
    const timer = setTimeout(() => setNotice(""), 3200);
    return () => clearTimeout(timer);
  }, [notice]);

  const loadTargetDocuments = async () => {
    if (!document.target_id) { setTargetDocuments([]); return; }
    try {
      const rows = document.target_type === "stakeholder" ? await api.getDocuments(document.target_id) : await api.getMeetingDocuments(document.target_id);
      setTargetDocuments(rows);
    } catch { setTargetDocuments([]); }
  };
  useEffect(() => { if (section === "Documents") loadTargetDocuments(); }, [section, document.target_type, document.target_id]);

  const podOpportunities = useMemo(() => [...opportunities].sort((a, b) => b.estimated_value - a.estimated_value), [opportunities]);
  const submit = async (operation, message, after) => {
    setSaving(true); setError("");
    try { await operation(); if (after) await after(); await load(); setNotice(message); }
    catch (requestError) { setError(requestError.message || "The record could not be saved."); }
    finally { setSaving(false); }
  };
  const changeDocumentTarget = (targetType) => { setEditingDocumentId(""); setDocument(value => ({ ...value, target_type: targetType, target_id: targetType === "stakeholder" ? people[0]?.id || "" : meetings[0]?.id || "", document_type: targetType === "meeting" ? "Meeting Brief" : "Account Plan" })); };
  const chooseCritical = (id) => {
    setEditingCriticalId(id);
    const item = criticalItems.find(value => value.id === id);
    if (!item) { setCritical(value => ({ ...value, title: "", description: "", opportunity_id: "" })); return; }
    setCritical({ title: item.title, description: item.description || "", item_type: item.type, severity: item.severity, capco_owner: item.capcoOwner || item.owner, capco_owner_employee_id: item.capcoOwnerEmployeeId || "", due_date: item.due, stakeholder_id: item.stakeholderId, opportunity_id: item.opportunityId || "", tags: (item.tags || []).join(", ") });
  };
  const chooseMeeting = (id) => {
    setEditingMeetingId(id);
    const item = meetings.find(value => value.id === id);
    if (!item) { setMeeting(value => ({ ...value, subject: "", summary: "", next_steps: "" })); return; }
    setMeeting({ subject: item.title, meeting_date: localDateTimeValue(item.meeting_date), duration_minutes: item.duration_minutes, summary: item.summary || "", stakeholder_id: item.stakeholder_id, organizer: item.organizer, organizer_employee_id: item.organizer_employee_id || "", capco_attendee_ids: item.capco_attendee_ids || [], outcome: item.outcome || "", next_steps: (item.next_steps || []).join("\n"), event_type: item.event_type, opportunity_id: item.opportunity_id || "", prep_required: item.prep_required, tags: (item.tags || []).join(", ") });
  };
  const chooseOpportunity = (id) => {
    setEditingOpportunityId(id);
    const item = opportunities.find(value => value.id === id);
    if (!item) { setPipeline(value => ({ ...value, name: "", description: "", estimated_value: "" })); return; }
    setPipeline({ name: item.name, description: item.description || "", estimated_value: item.estimated_value, probability: item.probability, stage: item.stage, stakeholder_id: item.stakeholder_ids[0] || people[0]?.id || "", owner: item.owner, owner_employee_id: item.owner_employee_id || "", target_close_date: item.target_close_date || "", tags: (item.tags || []).join(", ") });
  };
  useEffect(() => {
    if (!focus?.id) return;
    if (focus.type === "meeting" && meetings.some(item => item.id === focus.id)) {
      setSection("Meetings"); chooseMeeting(focus.id);
    }
    if (focus.type === "opportunity" && opportunities.some(item => item.id === focus.id)) {
      setSection("Commercial pipeline"); chooseOpportunity(focus.id);
    }
  }, [focus?.type, focus?.id, meetings, opportunities]);
  const chooseDocument = (id) => {
    setEditingDocumentId(id);
    const item = targetDocuments.find(value => value.id === id);
    if (!item) { setDocument(value => ({ ...value, title: "", file: null, sharepoint_url: "", description: "" })); return; }
    setDocument(value => ({ ...value, title: item.title, file: null, sharepoint_url: item.sharepoint_url || item.url || "", document_type: item.document_type, description: item.description || "", owner: item.owner, owner_employee_id: item.owner_employee_id || "", tags: (item.tags || []).join(", ") }));
  };

  const tabs = [
    ["Critical items", AlertTriangle], ["Meetings", CalendarDays], ["Commercial pipeline", BriefcaseBusiness], ["Documents", FileUp],
  ];

  return <div className="data-management">
    <header className="data-management-head"><div><span>{pod.toUpperCase()} DATA ADMINISTRATION</span><h1>Manage account information</h1><p>Add operational records and documents to the same database used by Pod View and stakeholder profiles.</p></div><div className="database-chip"><Database/><span><b>Canonical data pool</b><small>Changes appear throughout the account cockpit</small></span></div></header>
    <div className="data-summary">
      <RecordSummary icon={UsersRound} title="Stakeholders" description="Available linking records" count={people.length}/>
      <RecordSummary icon={CalendarDays} title="Meetings" description="Calendar and profile records" count={meetings.length}/>
      <RecordSummary icon={BriefcaseBusiness} title="Pipeline" description="Commercial opportunities" count={opportunities.length}/>
      <RecordSummary icon={AlertTriangle} title="Critical" description="Active Pod View items" count={criticalItems.length}/>
    </div>
    <nav className="data-tabs">{tabs.map(([name, Icon]) => <button key={name} className={section === name ? "active" : ""} onClick={() => { setSection(name); setError(""); }}><Icon/>{name}</button>)}</nav>
    <main className="data-management-body">
      <section className={`data-entry-card ${canWrite ? "" : "read-only"}`}>
        {!canWrite && <div className="data-error"><ShieldCheck/><span><b>Read-only access</b><small>Your current role can view these records but cannot change them.</small></span></div>}
        {section === "Critical items" && <form onSubmit={event => { event.preventDefault(); const payload = { ...critical, opportunity_id: critical.opportunity_id || null, tags: parseTags(critical.tags) }; submit(() => editingCriticalId ? api.updateCriticalItem(pod, editingCriticalId, payload) : api.createCriticalItem(pod, payload), editingCriticalId ? "Critical item updated throughout Pod View" : "Critical item added to Pod View", () => { setEditingCriticalId(""); setCritical(value => ({ ...value, title: "", description: "", tags: "" })); }); }}>
          <div className="data-form-title"><AlertTriangle/><div><h2>{editingCriticalId ? "Edit critical item" : "Add critical item"}</h2><p>{editingCriticalId ? "Updates the existing linked risk or decision record." : "Creates an active risk or decision item in the Pod View."}</p></div></div>
          <Field label="Create or edit"><select value={editingCriticalId} onChange={e => chooseCritical(e.target.value)}><option value="">Create a new critical item</option>{criticalItems.map(item => <option key={item.id} value={item.id}>Edit: {item.title}</option>)}</select></Field>
          <Field label="Title"><input required value={critical.title} onChange={e => setCritical({ ...critical, title: e.target.value })}/></Field>
          <Field label="Description"><textarea required rows="4" value={critical.description} onChange={e => setCritical({ ...critical, description: e.target.value })}/></Field>
          <div className="data-form-grid three"><Field label="Severity"><select value={critical.severity} onChange={e => setCritical({ ...critical, severity: e.target.value })}><option>RED</option><option>AMBER</option><option>YELLOW</option></select></Field><Field label="Type"><input value={critical.item_type} onChange={e => setCritical({ ...critical, item_type: e.target.value.toUpperCase() })}/></Field><Field label="Due date"><input required type="date" value={critical.due_date} onChange={e => setCritical({ ...critical, due_date: e.target.value })}/></Field></div>
          <div className="data-form-grid"><Field label="Morgan Stanley person"><select required value={critical.stakeholder_id} onChange={e => setCritical({ ...critical, stakeholder_id: e.target.value })}>{people.map(person => <option key={person.id} value={person.id}>{person.name} — {person.title}</option>)}</select></Field><Field label="Capco relationship owner"><select required value={critical.capco_owner_employee_id} onChange={e => { const employee = employees.find(item => item.id === e.target.value); setCritical({ ...critical, capco_owner_employee_id: e.target.value, capco_owner: employee?.name || "" }); }}>{employees.map(employee => <option key={employee.id} value={employee.id}>{employee.name} — {employee.role}</option>)}</select></Field></div>
          <Field label="Linked opportunity" hint="Optional"><select value={critical.opportunity_id} onChange={e => setCritical({ ...critical, opportunity_id: e.target.value })}><option value="">No linked opportunity</option>{podOpportunities.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
          <Field label="Tags" hint="Comma-separated; used by the Pod View account filter"><input value={critical.tags} onChange={e => setCritical({ ...critical, tags: e.target.value })} placeholder="AI, Data, Risk"/></Field>
          <button className="data-submit" disabled={saving || loading}><AlertTriangle/>{saving ? "Saving…" : editingCriticalId ? "Save critical item" : "Add critical item"}</button>
        </form>}

        {section === "Meetings" && <form onSubmit={event => { event.preventDefault(); const payload = { ...meeting, meeting_date: new Date(meeting.meeting_date).toISOString(), duration_minutes: Number(meeting.duration_minutes), stakeholder_ids: [meeting.stakeholder_id], capco_attendees: meeting.capco_attendee_ids.map(id => employees.find(item => item.id === id)?.name).filter(Boolean), next_steps: meeting.next_steps.split("\n").map(value => value.trim()).filter(Boolean), opportunity_id: meeting.opportunity_id || null, opportunity_ids: meeting.opportunity_id ? [meeting.opportunity_id] : [], tags: parseTags(meeting.tags) }; submit(() => editingMeetingId ? api.updatePodMeeting(pod, editingMeetingId, payload) : api.createPodMeeting(pod, payload), editingMeetingId ? "Meeting updated in the calendar and linked profile" : "Meeting added to the calendar and stakeholder profile", () => { setEditingMeetingId(""); setMeeting(value => ({ ...value, subject: "", summary: "", next_steps: "", tags: "" })); }); }}>
          <div className="data-form-title"><CalendarDays/><div><h2>{editingMeetingId ? "Edit meeting" : "Add meeting"}</h2><p>{editingMeetingId ? "Updates its calendar event and canonical profile history where linked." : "Writes one canonical meeting record and its linked Pod calendar event."}</p></div></div>
          <Field label="Create or edit"><select value={editingMeetingId} onChange={e => chooseMeeting(e.target.value)}><option value="">Create a new meeting</option>{meetings.map(item => <option key={`${item.id}-${item.event_id}`} value={item.id}>Edit: {new Date(item.meeting_date).toLocaleDateString()} — {item.title}</option>)}</select></Field>
          <Field label="Meeting subject"><input required value={meeting.subject} onChange={e => setMeeting({ ...meeting, subject: e.target.value })}/></Field>
          <div className="data-form-grid three"><Field label="Date and time"><input required type="datetime-local" value={meeting.meeting_date} onChange={e => setMeeting({ ...meeting, meeting_date: e.target.value })}/></Field><Field label="Duration (minutes)"><input required type="number" min="15" max="480" value={meeting.duration_minutes} onChange={e => setMeeting({ ...meeting, duration_minutes: e.target.value })}/></Field><Field label="Meeting type"><select value={meeting.event_type} onChange={e => setMeeting({ ...meeting, event_type: e.target.value })}><option value="client">Client</option><option value="internal">Internal</option><option value="workshop">Workshop</option><option value="critical">Critical</option><option value="deadline">Deadline</option></select></Field></div>
          <div className="data-form-grid"><Field label="Morgan Stanley attendee"><select required value={meeting.stakeholder_id} onChange={e => setMeeting({ ...meeting, stakeholder_id: e.target.value })}>{people.map(person => <option key={person.id} value={person.id}>{person.name} — {person.title}</option>)}</select></Field><Field label="Capco organizer"><select required value={meeting.organizer_employee_id} onChange={e => { const employee = employees.find(item => item.id === e.target.value); setMeeting({ ...meeting, organizer_employee_id: e.target.value, organizer: employee?.name || "" }); }}>{employees.map(employee => <option key={employee.id} value={employee.id}>{employee.name} — {employee.role}</option>)}</select></Field></div>
          <Field label="Capco attendees" hint="Use Ctrl/Cmd to select more than one canonical employee"><select multiple required value={meeting.capco_attendee_ids} onChange={e => setMeeting({ ...meeting, capco_attendee_ids: Array.from(e.target.selectedOptions, option => option.value) })}>{employees.map(employee => <option key={employee.id} value={employee.id}>{employee.name} — {employee.role}</option>)}</select></Field>
          <Field label="Meeting summary"><textarea rows="3" value={meeting.summary} onChange={e => setMeeting({ ...meeting, summary: e.target.value })}/></Field>
          <div className="data-form-grid"><Field label="Expected outcome"><input value={meeting.outcome} onChange={e => setMeeting({ ...meeting, outcome: e.target.value })}/></Field><Field label="Linked opportunity" hint="Optional"><select value={meeting.opportunity_id} onChange={e => setMeeting({ ...meeting, opportunity_id: e.target.value })}><option value="">No linked opportunity</option>{podOpportunities.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field></div>
          <Field label="Next steps" hint="One per line"><textarea rows="3" value={meeting.next_steps} onChange={e => setMeeting({ ...meeting, next_steps: e.target.value })}/></Field>
          <Field label="Tags" hint="Comma-separated; inherited by calendar and prep views"><input value={meeting.tags} onChange={e => setMeeting({ ...meeting, tags: e.target.value })} placeholder="AI, Data, Risk"/></Field>
          <label className="data-check"><input type="checkbox" checked={meeting.prep_required} onChange={e => setMeeting({ ...meeting, prep_required: e.target.checked })}/> Meeting preparation required</label>
          <button className="data-submit" disabled={saving || loading}><CalendarDays/>{saving ? "Saving…" : editingMeetingId ? "Save meeting" : "Add meeting"}</button>
        </form>}

        {section === "Commercial pipeline" && <form onSubmit={event => { event.preventDefault(); const payload = { ...pipeline, estimated_value: Number(pipeline.estimated_value), probability: Number(pipeline.probability), stakeholder_ids: [pipeline.stakeholder_id], target_close_date: pipeline.target_close_date || null, tags: parseTags(pipeline.tags) }; submit(() => editingOpportunityId ? api.updateOpportunity(editingOpportunityId, payload) : api.createOpportunity(payload), editingOpportunityId ? "Commercial opportunity updated throughout Pod View" : "Commercial opportunity added to Pod View", () => { setEditingOpportunityId(""); setPipeline(value => ({ ...value, name: "", description: "", estimated_value: "", tags: "" })); }); }}>
          <div className="data-form-title"><BriefcaseBusiness/><div><h2>{editingOpportunityId ? "Edit commercial pipeline item" : "Add commercial pipeline item"}</h2><p>{editingOpportunityId ? "Updates the existing opportunity and every linked commercial view." : "Creates an opportunity linked to an accountable Morgan Stanley stakeholder."}</p></div></div>
          <Field label="Create or edit"><select value={editingOpportunityId} onChange={e => chooseOpportunity(e.target.value)}><option value="">Create a new pipeline item</option>{podOpportunities.map(item => <option key={item.id} value={item.id}>Edit: {item.name}</option>)}</select></Field>
          <Field label="Opportunity name"><input required value={pipeline.name} onChange={e => setPipeline({ ...pipeline, name: e.target.value })}/></Field>
          <Field label="Commercial context"><textarea required rows="4" value={pipeline.description} onChange={e => setPipeline({ ...pipeline, description: e.target.value })}/></Field>
          <div className="data-form-grid three"><Field label="Estimated value"><input required type="number" min="0" step="1000" value={pipeline.estimated_value} onChange={e => setPipeline({ ...pipeline, estimated_value: e.target.value })}/></Field><Field label="Probability"><input required type="number" min="0" max="100" value={pipeline.probability} onChange={e => setPipeline({ ...pipeline, probability: e.target.value })}/></Field><Field label="Stage"><select value={pipeline.stage} onChange={e => setPipeline({ ...pipeline, stage: e.target.value })}>{opportunityStages.map(value => <option key={value}>{value}</option>)}</select></Field></div>
          <div className="data-form-grid"><Field label="Morgan Stanley sponsor"><select required value={pipeline.stakeholder_id} onChange={e => setPipeline({ ...pipeline, stakeholder_id: e.target.value })}>{people.map(person => <option key={person.id} value={person.id}>{person.name} — {person.title}</option>)}</select></Field><Field label="Capco owner"><select required value={pipeline.owner_employee_id} onChange={e => { const employee = employees.find(item => item.id === e.target.value); setPipeline({ ...pipeline, owner_employee_id: e.target.value, owner: employee?.name || "" }); }}>{employees.map(employee => <option key={employee.id} value={employee.id}>{employee.name} — {employee.role}</option>)}</select></Field></div>
          <Field label="Target close date"><input type="date" value={pipeline.target_close_date} onChange={e => setPipeline({ ...pipeline, target_close_date: e.target.value })}/></Field>
          <Field label="Tags" hint="Comma-separated; shared with linked stakeholders and Pod View"><input value={pipeline.tags} onChange={e => setPipeline({ ...pipeline, tags: e.target.value })} placeholder="AI, Data, Risk"/></Field>
          <button className="data-submit" disabled={saving || loading}><BriefcaseBusiness/>{saving ? "Saving…" : editingOpportunityId ? "Save pipeline item" : "Add pipeline item"}</button>
        </form>}

        {section === "Documents" && <form key={fileInputKey} onSubmit={event => { event.preventDefault(); const metadata = { title: document.title, sharepoint_url: document.sharepoint_url || null, document_type: document.document_type, description: document.description, owner: document.owner, owner_employee_id: document.owner_employee_id || null, tags: editingDocumentId ? parseTags(document.tags) : document.tags }; const uploader = document.target_type === "stakeholder" ? api.uploadStakeholderDocument : api.uploadMeetingDocument; submit(() => editingDocumentId ? api.updateDocument(editingDocumentId, metadata) : uploader(document.target_id, document.file, metadata), editingDocumentId ? "Document metadata, tags, and SharePoint link updated" : "Local document uploaded and linked", async () => { setEditingDocumentId(""); setDocument(value => ({ ...value, title: "", file: null, sharepoint_url: "", description: "", tags: "" })); setFileInputKey(value => value + 1); await loadTargetDocuments(); }); }}>
          <div className="data-form-title"><FileUp/><div><h2>{editingDocumentId ? "Edit document" : "Upload and link document"}</h2><p>{editingDocumentId ? "Updates document metadata while preserving the stored local copy." : "Stores a downloadable local copy and optionally links the SharePoint version."}</p></div></div>
          <div className="target-toggle"><button disabled={!!editingDocumentId} type="button" className={document.target_type === "stakeholder" ? "active" : ""} onClick={() => changeDocumentTarget("stakeholder")}>Stakeholder</button><button disabled={!!editingDocumentId} type="button" className={document.target_type === "meeting" ? "active" : ""} onClick={() => changeDocumentTarget("meeting")}>Meeting</button></div>
          <Field label={`Linked ${document.target_type}`}><select disabled={!!editingDocumentId} required value={document.target_id} onChange={e => { setEditingDocumentId(""); setDocument({ ...document, target_id: e.target.value }); }}>{document.target_type === "stakeholder" ? people.map(person => <option key={person.id} value={person.id}>{person.name} — {person.title}</option>) : meetings.map(item => <option key={`${item.id}-${item.event_id}`} value={item.id}>{new Date(item.meeting_date).toLocaleDateString()} — {item.title}</option>)}</select></Field>
          <Field label="Create or edit"><select value={editingDocumentId} onChange={e => chooseDocument(e.target.value)}><option value="">Upload a new document</option>{targetDocuments.map(item => <option key={item.id} value={item.id}>Edit: {item.title}</option>)}</select></Field>
          <Field label="Document title"><input required value={document.title} onChange={e => setDocument({ ...document, title: e.target.value })}/></Field>
          {!editingDocumentId && <Field label="Local file" hint="Required · PDF, Office, text, image, email · maximum 25 MB"><input required type="file" onChange={e => setDocument({ ...document, file: e.target.files?.[0] || null })}/></Field>}
          <Field label="SharePoint link" hint="Optional"><input type="url" placeholder="https://...sharepoint.com/..." value={document.sharepoint_url} onChange={e => setDocument({ ...document, sharepoint_url: e.target.value })}/></Field>
          <div className="data-form-grid"><Field label="Document type"><select value={document.document_type} onChange={e => setDocument({ ...document, document_type: e.target.value })}>{documentTypes.map(value => <option key={value}>{value}</option>)}</select></Field><Field label="Owner"><select required value={document.owner_employee_id} onChange={e => { const employee = employees.find(item => item.id === e.target.value); setDocument({ ...document, owner_employee_id: e.target.value, owner: employee?.name || "" }); }}>{employees.map(employee => <option key={employee.id} value={employee.id}>{employee.name} — {employee.role}</option>)}</select></Field></div>
          <Field label="Tags" hint="Comma-separated; searchable operating context"><input value={document.tags} onChange={e => setDocument({ ...document, tags: e.target.value })} placeholder="AI, Data, Risk"/></Field>
          <Field label="Description"><textarea rows="3" value={document.description} onChange={e => setDocument({ ...document, description: e.target.value })}/></Field>
          <button className="data-submit" disabled={saving || loading || !document.target_id || (!editingDocumentId && !document.file)}><FileUp/>{saving ? "Saving…" : editingDocumentId ? "Save document" : "Upload document"}</button>
        </form>}
        {error && <div className="data-error"><AlertTriangle/><span><b>Could not save</b><small>{error}</small></span></div>}
      </section>

      <aside className="data-guidance">
        <div><ShieldCheck/><h2>One linked data pool</h2><p>Every record managed here uses canonical stakeholder IDs, so profile drawers, calendar meetings, critical items, and pipeline cards stay connected.</p></div>
        {section === "Critical items" && <><h3>Currently active</h3><div className="data-record-list editable-record-list">{criticalItems.slice(0,8).map(item => <article key={item.id}><span className={item.severity.toLowerCase()}>{item.severity}</span><div><b>{item.title}</b><small>{item.msOwner} · {item.capcoOwner}</small></div><button onClick={() => chooseCritical(item.id)}>Edit</button></article>)}</div></>}
        {section === "Meetings" && <><h3>Recent meeting records</h3><div className="data-record-list editable-record-list">{meetings.slice(0,8).map(item => <article key={`${item.id}-${item.event_id}`}><CalendarDays/><div><b>{item.title}</b><small>{new Date(item.meeting_date).toLocaleString()}</small></div><button onClick={() => chooseMeeting(item.id)}>Edit</button></article>)}</div></>}
        {section === "Commercial pipeline" && <><h3>Current pipeline</h3><div className="data-record-list editable-record-list">{podOpportunities.slice(0,8).map(item => <article key={item.id}><BriefcaseBusiness/><div><b>{item.name}</b><small>{item.stage} · {new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(item.estimated_value)}</small></div><button onClick={() => chooseOpportunity(item.id)}>Edit</button></article>)}</div></>}
        {section === "Documents" && <><div className="document-policy"><h3>Document behavior</h3><ul><li>The uploaded file becomes the downloadable website copy.</li><li>The SharePoint URL and metadata can be edited later.</li><li>Removing a document deletes its local stored copy.</li><li>Files are served as downloads, not executed in the browser.</li></ul></div><h3>Documents for selected {document.target_type}</h3><div className="data-record-list editable-record-list">{targetDocuments.map(item => <article key={item.id}><FileUp/><div><b>{item.title}</b><small>{item.file_name || "Shared link only"}</small></div><button onClick={() => chooseDocument(item.id)}>Edit</button><button className="remove-record" onClick={() => window.confirm("Remove this document and its stored file? This cannot be undone.") && submit(() => api.deleteDocument(item.id), "Document removed", async () => { if (editingDocumentId === item.id) chooseDocument(""); await loadTargetDocuments(); })}>Remove</button></article>)}</div></>}
      </aside>
    </main>
    {notice && <div className="pod-toast" role="status"><Check/>{notice}</div>}
  </div>;
}
