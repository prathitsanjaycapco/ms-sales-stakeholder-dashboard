import React, { useEffect, useState } from "react";
import {
  Activity, AlertTriangle, CheckCircle2, Clock3, Database,
  History, RefreshCw, ShieldCheck,
} from "lucide-react";
import { api } from "./api";

const titleCase = (value = "") => String(value).toLowerCase().replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

function dateTime(value, fallback = "Not recorded") {
  if (!value) return fallback;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? fallback : parsed.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

function StatusBadge({ value }) {
  const normalized = value || "unknown";
  return <span className={`trust-badge ${normalized}`}>{titleCase(normalized)}</span>;
}

function Empty({ children }) {
  return <p className="trust-empty">{children}</p>;
}

export default function OperationsCenter({ session }) {
  const isAdmin = session?.roles?.includes("Account Admin");
  const [state, setState] = useState({ loading: true, error: "", health: null, trust: null, reconciliation: null, audit: [] });
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setState((current) => ({ ...current, loading: true, error: "" }));
    const requests = [api.getHealthDetails(), api.getDataTrust(), api.getReconciliation()];
    if (isAdmin) requests.push(api.getAuditEvents({ limit: 25 }));
    Promise.allSettled(requests).then((results) => {
      if (!active) return;
      const failures = results.filter((item) => item.status === "rejected");
      setState({
        loading: false,
        error: failures.length ? `${failures.length} operational check${failures.length === 1 ? "" : "s"} could not be loaded.` : "",
        health: results[0]?.status === "fulfilled" ? results[0].value : null,
        trust: results[1]?.status === "fulfilled" ? results[1].value : null,
        reconciliation: results[2]?.status === "fulfilled" ? results[2].value : null,
        audit: results[3]?.status === "fulfilled" ? results[3].value : [],
      });
    });
    return () => { active = false; };
  }, [isAdmin, reload]);

  const failedChecks = state.reconciliation?.checks?.filter((item) => !item.passed) || [];

  return <section className="operations-center" aria-labelledby="operations-title">
    <header className="operations-heading">
      <div><span>GOVERNANCE &amp; RELIABILITY</span><h2 id="operations-title">Trust &amp; operations</h2><p>Freshness, lineage, access, and deployment evidence for this account workspace.</p></div>
      <button onClick={() => setReload((value) => value + 1)} disabled={state.loading}><RefreshCw />{state.loading ? "Checking…" : "Run checks"}</button>
    </header>
    {state.error && <div className="trust-warning" role="alert"><AlertTriangle /><span>{state.error}</span></div>}
    <div className="trust-summary" aria-label="Operational summary">
      <article><Database /><span><small>Repository</small><b>{state.health?.persistent ? "Persistent SQL" : "Non-production"}</b></span><StatusBadge value={state.health?.persistent ? "healthy" : "warning"} /></article>
      <article><ShieldCheck /><span><small>Reconciliation</small><b>{state.reconciliation ? `${state.reconciliation.total_checks - state.reconciliation.failed_checks}/${state.reconciliation.total_checks} checks passed` : "Checking evidence"}</b></span><StatusBadge value={state.reconciliation?.status || "unknown"} /></article>
      <article><Activity /><span><small>Data domains</small><b>{state.trust?.sources?.length || 0} monitored</b></span><StatusBadge value={state.trust?.sources?.some((item) => ["stale", "untracked"].includes(item.freshness_status)) ? "attention" : "healthy"} /></article>
    </div>

    <section className="trust-panel">
      <header><div><Clock3 /><span><b>Data freshness and provenance</b><small>Latest persisted evidence by operating domain</small></span></div><time>{dateTime(state.trust?.generated_at, "Not checked")}</time></header>
      <div className="trust-source-list">
        {state.trust?.sources?.map((source) => <article key={source.key}>
          <div><b>{source.label}</b><small>{source.record_count} records · {source.externally_sourced_records || 0} externally sourced · {source.manual_records || 0} manual</small></div>
          <span><small>{source.latest_synced_at ? "Last synchronized" : source.latest_updated_at ? "Last updated" : "Freshness evidence"}</small><b>{dateTime(source.latest_synced_at || source.latest_updated_at, source.freshness_status === "untracked" ? "Not persisted" : "No records")}</b></span>
          <StatusBadge value={source.freshness_status} />
        </article>)}
        {!state.loading && !state.trust?.sources?.length && <Empty>No source status is available.</Empty>}
      </div>
      <footer>“Untracked” means the domain has records but no persisted synchronization timestamp; the source does not persist a synchronization timestamp. It is not treated as current.</footer>
    </section>

    <div className="trust-grid">
      <section className="trust-panel">
        <header><div><ShieldCheck /><span><b>Cross-screen reconciliation</b><small>Canonical values and references</small></span></div><StatusBadge value={state.reconciliation?.status || "unknown"} /></header>
        {state.reconciliation && <div className="reconciliation-summary"><strong>{state.reconciliation.total_checks - state.reconciliation.failed_checks}</strong><span>checks passed<small>As of {state.reconciliation.as_of}</small></span></div>}
        {failedChecks.map((check) => <div className="failed-check" key={check.name}><AlertTriangle /><span><b>{check.name}</b><small>Expected {String(check.expected)} · found {String(check.actual)}</small></span></div>)}
        {state.reconciliation && !failedChecks.length && <div className="trust-success"><CheckCircle2 />Every canonical reconciliation check passed.</div>}
      </section>
      <section className="trust-panel">
        <header><div><Activity /><span><b>Runtime controls</b><small>Configured operating boundaries</small></span></div></header>
        <dl className="control-list">{Object.entries(state.trust?.controls || {}).map(([key, value]) => <div key={key}><dt>{titleCase(key)}</dt><dd>{titleCase(value)}</dd></div>)}</dl>
      </section>
    </div>

    {isAdmin && <div className="trust-grid admin-grid">
      <section className="trust-panel">
        <header><div><History /><span><b>Recent audit history</b><small>Last 25 successful mutations</small></span></div></header>
        <div className="audit-list">{state.audit.map((event) => <article key={event.id}><span><b>{titleCase(event.action)}</b><small>{event.actor_subject} · {event.entity_type || "workspace"}</small></span><time>{dateTime(event.occurred_at)}</time></article>)}{!state.loading && !state.audit.length && <Empty>No mutations have been audited yet.</Empty>}</div>
      </section>
    </div>}
    {!isAdmin && <p className="admin-note"><ShieldCheck />Account Admins can also review mutation audit history.</p>}
  </section>;
}
