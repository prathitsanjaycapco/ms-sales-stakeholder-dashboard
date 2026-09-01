import React, { useEffect, useRef, useState } from "react";
import { AlertTriangle, Bell, CheckCircle2, RefreshCw, X } from "lucide-react";
import { api } from "./api";
import { useDialogAccessibility } from "./useDialogAccessibility";

export default function NotificationCenter({ pod, onClose, onSelect }) {
  const dialogRef = useRef(null);
  useDialogAccessibility(dialogRef, onClose);
  const [state, setState] = useState({ loading: true, error: "", data: null });
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true;
    setState((current) => ({ ...current, loading: true, error: "" }));
    api.getNotificationDigest(pod).then((data) => { if (active) setState({ loading: false, error: "", data }); }).catch((error) => { if (active) setState({ loading: false, error: error.message || "Alerts could not be loaded.", data: null }); });
    return () => { active = false; };
  }, [pod, reload]);
  return <><button className="notification-backdrop" onClick={onClose} aria-label="Close alerts" /><aside ref={dialogRef} className="notification-center" role="dialog" aria-modal="true" aria-label="Account alerts">
    <header><div><span>ACCOUNT OPERATIONS</span><h2>Alerts &amp; ownership</h2><p>{pod === "All" ? "All Morgan Stanley pods" : pod}</p></div><button data-dialog-initial-focus onClick={onClose} aria-label="Close alerts"><X /></button></header>
    <div className="notification-summary"><Bell /><span><b>{state.data?.summary?.total ?? "—"}</b><small>items requiring attention</small></span><em>{state.data?.summary?.red || 0} critical</em></div>
    <div className="notification-list">
      {state.loading && <p>Checking leadership and resourcing queues…</p>}
      {state.error && <div className="notification-error"><AlertTriangle /><span>{state.error}</span><button onClick={() => setReload((value) => value + 1)}><RefreshCw />Retry</button></div>}
      {state.data?.items?.map((item) => <button key={item.id} onClick={() => { onSelect(item); onClose(); }}><i className={item.severity?.toLowerCase()}><AlertTriangle /></i><span><small>{item.category} · {item.pod || "Account"}</small><b>{item.title}</b><p>{item.context || "Review and assign the next action."}</p><em>{item.owner || "Owner not assigned"}</em></span></button>)}
      {!state.loading && !state.error && !state.data?.items?.length && <div className="notification-clear"><CheckCircle2 /><b>No active alerts</b><span>Leadership and resourcing queues are clear.</span></div>}
    </div>
    <footer><span>External delivery is {state.data?.delivery?.external === "not_configured" ? "not configured" : "enabled"}.</span><button onClick={() => setReload((value) => value + 1)}><RefreshCw />Refresh</button></footer>
  </aside></>;
}
