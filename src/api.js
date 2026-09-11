const API_BASE = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");

async function request(path, options = {}) {
  const { headers = {}, ...requestOptions } = options;
  const response = await fetch(`${API_BASE}${path}`, {
    ...requestOptions,
    headers: { ...(options.body instanceof Blob ? {} : { "Content-Type": "application/json" }), ...headers },
  });
  if (!response.ok) {
    const body = await response.text();
    let detail = body.trim();
    try {
      const payload = JSON.parse(body);
      detail = Array.isArray(payload.detail)
        ? payload.detail.map((item) => item.msg).filter(Boolean).join("; ")
        : payload.detail || payload.message || detail;
    } catch {}
    const error = new Error(detail || `Request failed with ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}

async function archive(path) {
  try { return await request(path, { method: "POST" }); }
  catch (error) {
    if (error.status === 404) throw new Error("The active API does not support recoverable deletion, or this record was already archived. Restart or redeploy the API, refresh this page, and try again.");
    throw error;
  }
}

function upload(path, file, metadata) {
  const query = new URLSearchParams({
    ...Object.fromEntries(Object.entries(metadata).filter(([, value]) => value !== undefined && value !== null && value !== "")),
    file_name: file.name,
  });
  return request(`${path}?${query}`, {
    method: "POST",
    headers: { "Content-Type": file.type || "application/octet-stream" },
    body: file,
  });
}

export const api = {
  getSession: () => request("/session"),
  getHealthDetails: () => request("/health/details"),
  getDataTrust: () => request("/data-trust"),
  getEmployees: (search) => request(`/employees${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  getEmployeeProfile: (id) => request(`/employees/${encodeURIComponent(id)}/profile`),
  getEngagement: (id) => request(`/engagements/${encodeURIComponent(id)}`),
  getAuditEvents: (params = {}) => {
    const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== ""));
    return request(`/audit-events${query.size ? `?${query}` : ""}`);
  },
  getAssistantDocumentIndex: () => request("/assistant/document-index"),
  reindexAssistantDocuments: () => request("/assistant/documents/reindex", { method: "POST" }),
  getAssistantConversations: () => request("/assistant/conversations"),
  getAssistantConversation: (id) => request(`/assistant/conversations/${encodeURIComponent(id)}`),
  deleteAssistantConversation: (id) => request(`/assistant/conversations/${encodeURIComponent(id)}`, { method: "DELETE" }),
  askAssistant: (message, conversationId, context = {}) => request("/assistant/chat", {
    method: "POST",
    body: JSON.stringify({ message, conversation_id: conversationId || null, context }),
  }),
  getPods: () => request("/pods"),
  search: (query, pod = "All") => request(`/search?${new URLSearchParams({ q: query, ...(pod && pod !== "All" ? { pod } : {}) })}`),
  getMap: (pod, params = {}) => {
    const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== "" && value !== "All"));
    return request(`/pods/${encodeURIComponent(pod)}/map${query.size ? `?${query}` : ""}`);
  },
  getFilterOptions: (pod) => request(`/pods/${encodeURIComponent(pod)}/filters`),
  getPodDashboard: (pod, period = "week", periodStart, tag) => request(`/pods/${encodeURIComponent(pod)}/dashboard?${new URLSearchParams({ period, ...(periodStart ? { period_start: periodStart } : {}), ...(tag && tag !== "All" ? { tag } : {}) })}`),
  getExecutiveOverview: ({ period = "quarter", anchor, startDate, endDate, pod = "All" } = {}) => request(`/executive/overview?${new URLSearchParams({ period, ...(anchor ? { anchor } : {}), ...(startDate ? { start_date: startDate } : {}), ...(endDate ? { end_date: endDate } : {}), ...(pod && pod !== "All" ? { pod } : {}) })}`),
  getExecutiveWeekly: ({ weekStart, pod = "All", outlookWeeks = 4 } = {}) => request(`/executive/weekly?${new URLSearchParams({ ...(weekStart ? { week_start: weekStart } : {}), ...(pod && pod !== "All" ? { pod } : {}), outlook_weeks: outlookWeeks })}`),
  getNotificationDigest: (pod = "All") => request(`/notifications/digest${pod && pod !== "All" ? `?pod=${encodeURIComponent(pod)}` : ""}`),
  getResourcingOverview: (pod = "All") => request(`/resourcing/overview${pod && pod !== "All" ? `?pod=${encodeURIComponent(pod)}` : ""}`),
  getResourcingAnalytics: (pod = "All") => request(`/resourcing/analytics${pod && pod !== "All" ? `?pod=${encodeURIComponent(pod)}` : ""}`),
  getResourcingOptions: (pod = "All") => request(`/resourcing/options${pod && pod !== "All" ? `?pod=${encodeURIComponent(pod)}` : ""}`),
  getResourcingTrash: (pod = "All") => request(`/resourcing/trash${pod && pod !== "All" ? `?pod=${encodeURIComponent(pod)}` : ""}`),
  restoreResourcingItem: (type, id) => request(`/resourcing/trash/${encodeURIComponent(type)}/${encodeURIComponent(id)}/restore`, { method: "POST" }),
  getResourceRequirements: (pod = "All") => request(`/resource-requirements${pod && pod !== "All" ? `?pod=${encodeURIComponent(pod)}` : ""}`),
  getResourceRequirement: (id) => request(`/resource-requirements/${encodeURIComponent(id)}`),
  createResourceRequirement: (payload) => request("/resource-requirements", { method: "POST", body: JSON.stringify(payload) }),
  updateResourceRequirement: (id, payload) => request(`/resource-requirements/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteResourceRequirement: (id, reason = "") => archive(`/resource-requirements/${encodeURIComponent(id)}/archive?reason=${encodeURIComponent(reason)}`),
  getCandidates: (pod = "All", requirementId) => request(`/candidates?${new URLSearchParams({ ...(pod && pod !== "All" ? { pod } : {}), ...(requirementId ? { resource_requirement_id: requirementId } : {}) })}`),
  getCandidate: (id) => request(`/candidates/${encodeURIComponent(id)}`),
  createCandidate: (payload) => request("/candidates", { method: "POST", body: JSON.stringify(payload) }),
  updateCandidate: (id, payload) => request(`/candidates/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) }),
  transitionCandidate: (id, payload) => request(`/candidates/${encodeURIComponent(id)}/transition`, { method: "POST", body: JSON.stringify(payload) }),
  deleteCandidate: (id, reason = "") => archive(`/candidates/${encodeURIComponent(id)}/archive?reason=${encodeURIComponent(reason)}`),
  createInterview: (candidateId, payload) => request(`/candidates/${encodeURIComponent(candidateId)}/interviews`, { method: "POST", body: JSON.stringify(payload) }),
  updateInterview: (id, payload) => request(`/interviews/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) }),
  createOffer: (candidateId, payload) => request(`/candidates/${encodeURIComponent(candidateId)}/offer`, { method: "POST", body: JSON.stringify(payload) }),
  getOffer: (candidateId) => request(`/candidates/${encodeURIComponent(candidateId)}/offer`),
  updateOffer: (candidateId, payload) => request(`/candidates/${encodeURIComponent(candidateId)}/offer`, { method: "PATCH", body: JSON.stringify(payload) }),
  getOnboarding: (pod = "All") => request(`/onboarding${pod && pod !== "All" ? `?pod=${encodeURIComponent(pod)}` : ""}`),
  getOnboardingRecord: (id) => request(`/onboarding/${encodeURIComponent(id)}`),
  updateOnboarding: (id, payload) => request(`/onboarding/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteOnboarding: (id, reason = "") => archive(`/onboarding/${encodeURIComponent(id)}/archive?reason=${encodeURIComponent(reason)}`),
  updateOnboardingStep: (id, stepId, payload) => request(`/onboarding/${encodeURIComponent(id)}/steps/${encodeURIComponent(stepId)}`, { method: "PATCH", body: JSON.stringify(payload) }),
  startOnboardingCandidate: (id) => request(`/onboarding/${encodeURIComponent(id)}/start`, { method: "POST" }),
  getReconciliation: (anchor) => request(`/integrity/reconciliation${anchor ? `?anchor=${encodeURIComponent(anchor)}` : ""}`),
  updatePodTask: (pod, taskId, status) => request(`/pods/${encodeURIComponent(pod)}/tasks/${taskId}`, { method: "PATCH", body: JSON.stringify({ status }) }),
  createPodTask: (pod, payload) => request(`/pods/${encodeURIComponent(pod)}/tasks`, { method: "POST", body: JSON.stringify(payload) }),
  updatePodFocus: (pod, focus) => request(`/pods/${encodeURIComponent(pod)}/focus`, { method: "PATCH", body: JSON.stringify({ focus }) }),
  updateCriticalItem: (pod, itemId, changes) => request(`/pods/${encodeURIComponent(pod)}/critical-items/${itemId}`, { method: "PATCH", body: JSON.stringify(typeof changes === "string" ? { status: changes } : changes) }),
  createCriticalItem: (pod, payload) => request(`/pods/${encodeURIComponent(pod)}/critical-items`, { method: "POST", body: JSON.stringify(payload) }),
  getStakeholders: (params = {}) => {
    const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== "" && value !== "All"));
    return request(`/stakeholders${query.size ? `?${query}` : ""}`);
  },
  getStakeholder: (id) => request(`/stakeholders/${id}`),
  getStakeholderProfile: (id) => request(`/stakeholders/${id}/profile`),
  createStakeholder: (payload) => request("/stakeholders", { method: "POST", body: JSON.stringify(payload) }),
  updateStakeholder: (id, payload) => request(`/stakeholders/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteStakeholder: (id) => request(`/stakeholders/${id}`, { method: "DELETE" }),
  getTeam: (id) => request(`/stakeholders/${id}/team`),
  getHistory: (id) => request(`/stakeholders/${id}/history`),
  updateReportingLine: (payload) => request("/organization/reporting-line", { method: "PATCH", body: JSON.stringify(payload) }),
  updatePrimaryTechnology: (businessUnitId, payload) => request(`/business-units/${businessUnitId}/primary-tech-stakeholder`, { method: "PATCH", body: JSON.stringify(payload) }),
  updatePodHead: (pod, payload) => request(`/pods/${encodeURIComponent(pod)}/head`, { method: "PATCH", body: JSON.stringify(payload) }),
  getCoverage: (pod) => request(`/pods/${encodeURIComponent(pod)}/coverage`),
  getMeetings: (stakeholderId, upcoming) => request(`/stakeholders/${stakeholderId}/meetings${upcoming === undefined ? "" : `?upcoming=${upcoming}`}`),
  getPodMeetings: (pod) => request(`/meetings?pod=${encodeURIComponent(pod)}`),
  getPodMeetingOptions: (pod) => request(`/pods/${encodeURIComponent(pod)}/meeting-options`),
  createMeeting: (payload) => request("/meetings", { method: "POST", body: JSON.stringify(payload) }),
  createPodMeeting: (pod, payload) => request(`/pods/${encodeURIComponent(pod)}/meetings`, { method: "POST", body: JSON.stringify(payload) }),
  updatePodMeeting: (pod, meetingId, payload) => request(`/pods/${encodeURIComponent(pod)}/meetings/${meetingId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  getNotes: (stakeholderId) => request(`/stakeholders/${stakeholderId}/notes`),
  createNote: (stakeholderId, payload) => request(`/stakeholders/${stakeholderId}/notes`, { method: "POST", body: JSON.stringify(payload) }),
  updateNote: (noteId, payload) => request(`/notes/${noteId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteNote: (noteId) => request(`/notes/${noteId}`, { method: "DELETE" }),
  getDocuments: (stakeholderId) => request(`/stakeholders/${stakeholderId}/documents`),
  createDocument: (stakeholderId, payload) => request(`/stakeholders/${stakeholderId}/documents`, { method: "POST", body: JSON.stringify(payload) }),
  uploadStakeholderDocument: (stakeholderId, file, metadata) => upload(`/stakeholders/${stakeholderId}/documents/upload`, file, metadata),
  getMeetingDocuments: (meetingId) => request(`/meetings/${meetingId}/documents`),
  getMeetingBrief: (meetingId) => request(`/meetings/${meetingId}/brief`),
  getMeeting: (meetingId) => request(`/meetings/${meetingId}`),
  uploadMeetingDocument: (meetingId, file, metadata) => upload(`/meetings/${meetingId}/documents/upload`, file, metadata),
  documentDownloadUrl: (documentId) => `${API_BASE}/documents/${documentId}/download`,
  updateDocument: (documentId, payload) => request(`/documents/${documentId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteDocument: (documentId) => request(`/documents/${documentId}`, { method: "DELETE" }),
  getOpportunities: (stakeholderId, stage) => {
    const query = new URLSearchParams();
    if (stakeholderId) query.set("stakeholder_id", stakeholderId);
    if (stage && stage !== "All") query.set("stage", stage);
    return request(`/opportunities${query.size ? `?${query}` : ""}`);
  },
  getOpportunity: (id) => request(`/opportunities/${id}`),
  createOpportunity: (payload) => request("/opportunities", { method: "POST", body: JSON.stringify(payload) }),
  updateOpportunity: (id, payload) => request(`/opportunities/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
};
