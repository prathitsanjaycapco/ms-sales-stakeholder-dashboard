const csvCell = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;

export function executiveBrief(data, posture) {
  const attention = (data.attentionItems || []).map((item) => `- [${item.severity || item.priority || "Open"}] ${item.title}: ${item.nextAction || item.context || "Follow up required"}`);
  const projects = (data.projects || []).map((item) => `- ${item.name} — ${item.health} — ${item.pod} — $${Number(item.commercialValue || 0).toLocaleString("en-US")}`);
  const opportunities = (data.salesSummary?.opportunities || []).map((item) => `- ${item.name} — ${item.stage} — ${item.pod} — $${Number(item.value || 0).toLocaleString("en-US")}`);
  return [
    "# Morgan Stanley account weekly brief", "",
    `**Operating week:** ${data.meta?.weekStart || "Unknown"} to ${data.meta?.weekEnd || "Unknown"}`,
    `**Scope:** ${data.meta?.pod || "All pods"}`, "", "## Account posture",
    `- Active portfolio: $${Number(posture.totalProjectValue || 0).toLocaleString("en-US")}`,
    `- Delivery exposure: $${Number(posture.atRiskValue || 0).toLocaleString("en-US")} (${posture.atRiskPercent || 0}%)`,
    `- Weighted pipeline confidence: ${posture.confidencePercent || 0}%`,
    `- Leadership queue: ${(data.attentionItems || []).length}`,
    `- Active Capco footprint: ${data.pulse?.activeEmployees ?? "Unknown"}`, "",
    "## Decisions and interventions", ...(attention.length ? attention : ["- No leadership interventions recorded."]), "",
    "## Active engagements", ...(projects.length ? projects : ["- No active engagements in scope."]), "",
    "## Commercial pipeline", ...(opportunities.length ? opportunities : ["- No active opportunities in scope."]), "", "---",
    `Generated ${new Date().toISOString()} from normalized account records.`,
  ].join("\n");
}

export function executiveCsv(data) {
  const rows = [["record_type", "name", "pod", "status", "value", "owner_or_next_action"]];
  (data.attentionItems || []).forEach((item) => rows.push(["leadership_action", item.title, item.pod, item.severity || item.priority, "", item.owner || item.nextAction]));
  (data.projects || []).forEach((item) => rows.push(["engagement", item.name, item.pod, item.health, item.commercialValue, item.nextMilestone?.title]));
  (data.salesSummary?.opportunities || []).forEach((item) => rows.push(["opportunity", item.name, item.pod, item.stage, item.value, item.nextStep]));
  return rows.map((row) => row.map(csvCell).join(",")).join("\r\n");
}

export function downloadText(filename, content, type = "text/plain;charset=utf-8") {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
