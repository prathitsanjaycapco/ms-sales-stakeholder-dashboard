import React, { useState } from "react";
import { AlertTriangle, Database, Download, FileUp, ShieldCheck } from "lucide-react";
import { api } from "./api";
import "./accountWorkbookAdmin.css";

export default function AccountWorkbookAdmin({ canAdmin }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [clearPreview, setClearPreview] = useState(null);
  const [phrase, setPhrase] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const run = async (operation, after) => {
    setBusy(true); setError(""); setResult(null);
    try { const value = await operation(); after(value); }
    catch (requestError) { setError(requestError.message || "The action could not be completed."); }
    finally { setBusy(false); }
  };

  return <section className="workbook-admin">
    <header><FileUp/><span><h2>Import account data from Excel</h2><p>Fill the workbook, preview its rows, then import into an empty local database. Employees, client contacts, organization structure, and relationship owners appear throughout the dashboard.</p></span></header>
    {!canAdmin && <p>Account Admin access is required to import or clear account data.</p>}
    <div className="workbook-admin-grid">
      <div>
        <h3>1. Fill the template</h3>
        {canAdmin && <a className="workbook-action" href={api.accountImportTemplateUrl} download="account-import-template-friendly.xlsx"><Download/>Download Excel template</a>}
        <label className="workbook-file">Completed .xlsx workbook<input type="file" accept=".xlsx" disabled={!canAdmin || busy} onChange={(event) => { setFile(event.target.files?.[0] || null); setPreview(null); setResult(null); }} /></label>
        <button type="button" disabled={!canAdmin || !file || busy} onClick={() => run(() => api.previewAccountWorkbook(file), setPreview)}>Preview workbook</button>
        {preview && <div className="workbook-preview"><b>{preview.account}</b><p>{Object.entries(preview.counts).map(([key, count]) => `${count} ${key.replaceAll("_", " ")}`).join(" · ")}</p><button type="button" disabled={busy} onClick={() => run(() => api.importAccountWorkbook(file), (value) => { setResult(`Imported account data. Backup: ${value.backup}`); setPreview(null); })}>Import these records</button></div>}
      </div>
      <div>
        <h3>2. Clear demo data, if present</h3>
        <p>This clears the local demo dataset after checking that no non-demo records or recorded user changes exist. A database backup is saved first.</p>
        <button type="button" disabled={!canAdmin || busy} onClick={() => run(api.previewDemoClear, (value) => { setClearPreview(value); setPhrase(""); })}><Database/>Review demo data</button>
        {clearPreview && <div className="workbook-preview danger"><AlertTriangle/><p>Review: {clearPreview.total_rows} database rows across {Object.keys(clearPreview.counts).length} tables. This action removes the local demo dataset.</p><label>Type <b>CLEAR DEMO DATA</b> to confirm<input value={phrase} onChange={(event) => setPhrase(event.target.value)} autoComplete="off" /></label><button type="button" disabled={busy || phrase !== clearPreview.confirmation_phrase} onClick={() => run(() => api.clearDemoData(clearPreview.token, phrase), (value) => { setResult(`Demo data cleared. Import the completed workbook next. Backup: ${value.backup}`); setClearPreview(null); })}>Confirm and clear demo data</button></div>}
      </div>
    </div>
    {error && <div className="data-error" role="alert"><AlertTriangle/><span>{error}</span></div>}
    {result && <div className="workbook-result" role="status"><ShieldCheck/><span>{result}</span><button type="button" onClick={() => window.location.reload()}>Reload dashboard</button></div>}
  </section>;
}
