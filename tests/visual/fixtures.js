const stakeholder = (id, name, title, extras = {}) => ({
  id, name, title, pod: "ISG", division: "Front Office", business_unit: "Equities",
  team_type: "Business", level: "Managing Director", location: "New York", country_code: "US",
  relationship_strength: "Strong", capco_contingents: 2, capco_owner: "Priya Shah",
  opportunity_count: 1, is_buyer: false, is_influencer: true, is_budget_holder: false,
  tags: ["Data", "Transformation"], ...extras,
});

export const mapResponse = {
  pod: "ISG",
  pod_head_stakeholder_id: "s0",
  stakeholders: [
    stakeholder("s0", "Dan Simkowitz", "Co-President; responsible for Institutional Securities Group", { division: null, business_unit: null, organizational_role: "Pod Head", is_buyer: true }),
    stakeholder("s1", "John Smith", "Division Head", { organizational_role: "Division Head", manager_id: "s0", is_buyer: true }),
    stakeholder("s2", "Emily Davis", "Head of Equities", { manager_id: "s1", is_budget_holder: true }),
    stakeholder("s3", "Anna Clark", "Equities Coverage Lead", { manager_id: "s2" }),
    stakeholder("s13", "Jonathan Montgomery", "Global Electronic Trading Transformation Director", { manager_id: "s2", country_code: "GB", location: "London" }),
    stakeholder("s14", "Maya Wilson", "Equities Operations Lead", { manager_id: "s2", country_code: "CA", location: "Toronto" }),
    stakeholder("s15", "Sarah Singh", "Equities Senior Specialist", { manager_id: "s2", country_code: "IN", location: "Mumbai" }),
    stakeholder("s4", "Daniel Kim", "VP, Equities Technology", { team_type: "Technology", manager_id: "s2", is_primary_technology: true }),
    stakeholder("s6", "Morgan Lee", "Equities Technology Director", { team_type: "Technology", manager_id: "s4" }),
    stakeholder("s5", "Priya Nair", "HR Director", { division: "Enterprise Functions", business_unit: "Human Resources", manager_id: "s0" }),
    stakeholder("s7", "Marcus Hill", "Head of Middle Office", { division: "Middle Office", business_unit: "Division Leadership", organizational_role: "Division Head", manager_id: "s0" }),
    stakeholder("s8", "Sofia Patel", "Head of Risk Management", { division: "Middle Office", business_unit: "Risk Management", organizational_role: "Business Unit Head", manager_id: "s7" }),
    stakeholder("s9", "Liam Chen", "Risk Technology Manager", { division: "Middle Office", business_unit: "Risk Management", team_type: "Technology", manager_id: "s8", is_primary_technology: true }),
    stakeholder("s10", "Elena Brooks", "Head of Back Office", { division: "Back Office", business_unit: "Division Leadership", organizational_role: "Division Head", manager_id: "s0" }),
    stakeholder("s11", "Owen Grant", "Head of Operations", { division: "Back Office", business_unit: "Operations", organizational_role: "Business Unit Head", manager_id: "s10" }),
    stakeholder("s12", "Maya Singh", "Operations Technology Manager", { division: "Back Office", business_unit: "Operations", team_type: "Technology", manager_id: "s11", is_primary_technology: true }),
  ],
  reporting_lines: [{ manager_id: "s0", report_id: "s1" }, { manager_id: "s1", report_id: "s2" }, { manager_id: "s2", report_id: "s3" }, { manager_id: "s2", report_id: "s13" }, { manager_id: "s2", report_id: "s14" }, { manager_id: "s2", report_id: "s15" }, { manager_id: "s2", report_id: "s4" }, { manager_id: "s4", report_id: "s6" }, { manager_id: "s0", report_id: "s5" }, { manager_id: "s0", report_id: "s7" }, { manager_id: "s7", report_id: "s8" }, { manager_id: "s8", report_id: "s9" }, { manager_id: "s0", report_id: "s10" }, { manager_id: "s10", report_id: "s11" }, { manager_id: "s11", report_id: "s12" }],
  divisions: [
    { id: "d1", name: "Front Office", color: "#536dfe", head_stakeholder_id: "s1", units: [{ id: "u1", name: "Equities", business_stakeholder_ids: ["s2", "s3", "s13", "s14", "s15"], primary_technology_id: "s4", reporting_unknown_ids: [] }] },
    { id: "d2", name: "Middle Office", color: "#2b8a68", head_stakeholder_id: "s7", units: [{ id: "u2", name: "Risk Management", business_stakeholder_ids: ["s8"], primary_technology_id: "s9", reporting_unknown_ids: [] }] },
    { id: "d3", name: "Back Office", color: "#9a55b6", head_stakeholder_id: "s10", units: [{ id: "u3", name: "Operations", business_stakeholder_ids: ["s11"], primary_technology_id: "s12", reporting_unknown_ids: [] }] },
  ],
  enterprise_functions: [{ id: "e1", name: "Human Resources", lead_stakeholder_id: "s5", member_ids: [] }],
};

export const dashboard = {
  people: [{ id: "s2", name: "Emily Davis", title: "Head of Equities", unit: "Equities", relationship: "Strong", role: "Buyer", lastMeeting: "2026-08-20" }],
  meetings: [{ id: "m1", meetingId: "m1", title: "Equities strategy review", person: "Emily Davis", stakeholderId: "s2", pod: "ISG", type: "client", start: "2026-09-01T10:00:00-04:00", end: "2026-09-01T11:00:00-04:00", capcoAttendees: ["Priya Shah"] }],
  upcomingPrep: [], opportunities: [], criticalItems: [], tasks: [], relationships: [], relationshipAttention: [], milestones: [], commitments: [],
  focus: ["Confirm modernization scope", "Align the executive sponsor", "Protect September delivery"],
  health: [], tagOptions: ["Data", "Risk"], activeTag: "All",
  resourcing: { open_demand: 3, onboarding: 2, blocked: 1 },
  summary: { meetingCount: 1, buyerCount: 1, influencerCount: 1, deadlineCount: 2, urgentDeadlineCount: 1, openActionCount: 4, overdueActionCount: 1, pipelineValue: 4200000, weightedPipelineValue: 2100000, relationshipAttentionCount: 2, highRelationshipAttentionCount: 1 },
};

export const executiveWeekly = {
  meta: { weekStart: "2026-08-31", weekEnd: "2026-09-06", pod: "All" },
  pulse: { activeEmployees: 84, importantEvents: 4, attentionItems: 2, activeProjects: 3, pipeline: 52000000, upcomingMilestones: 3 },
  teamActivity: [{ id: "e1", name: "Priya Shah", title: "Account Executive", role: "Account Executive", level: "Director", location: "New York", capabilities: ["Strategy"], pods: ["ISG"], primaryProject: "Equities", allocationPercent: 110, assignments: [], activities: [], nextFewWeeks: [], stakeholders: [], opportunities: [] }],
  attentionItems: [{ id: "a1", severity: "RED", category: "DELIVERY", title: "Data platform decision required", pod: "ISG", context: "Executive outcome review", owner: "Priya Shah", nextAction: "Agree recovery plan", engagementId: "p2" }],
  weeklyCalendar: [], upcomingWeeks: [], changes: [], recommendations: [],
  projects: [
    { id: "p1", name: "Equities Transformation", pod: "ISG", businessUnit: "Equities", health: "GREEN", commercialValue: 10800000, nextMilestone: null },
    { id: "p2", name: "Risk Data Platform", pod: "MSIM", businessUnit: "Risk", health: "RED", commercialValue: 6800000, nextMilestone: null },
    { id: "p3", name: "Digital Advisory", pod: "Wealth Management", businessUnit: "Advisory", health: "AMBER", commercialValue: 6400000, nextMilestone: null },
  ],
  podSummaries: [{ pod: "ISG", criticalIssues: 1 }, { pod: "MSIM", criticalIssues: 1 }],
  salesSummary: { pipeline: 52400000, weightedPipeline: 28800000, nearTermOpportunities: 1, upcomingProposalsDecisions: 1, opportunities: [{ id: "o1", name: "AI-enabled trading workflow", pod: "ISG", stage: "Discovery", value: 450000, nextStep: "Division leadership decision" }] },
  resourcing: { open_demand: 13, onboarding: 4, starting_30_days: 4, roles_over_30_days: 4, blocked: 2 },
};

export const resourceRole = { id: "r1", pod_id: "ISG", division: "Front Office", business_unit: "Equities", project_name: "Data Modernization", title: "Senior Data Engineer", role: "Data Engineer", required_skills: ["Python", "AWS"], priority: "CRITICAL", requested_headcount: 3, filled_headcount: 1, remaining_headcount: 2, candidate_count: 1, target_start_date: "2026-09-20", location: "New York", age_days: 35, owner_name: "Jane Smith", client_name: "Daniel Kim", level: "Principal", status: "SOURCING", resourcing_app_created: true, bench_checked: true, bench_outcome: "EXISTING_PIPELINE", resourcing_request_submitted: false, sourcing_ready: true, sourcing_state: "CANDIDATE_FOUND", sourcing_next_action: "Candidate pipeline active" };
export const candidate = { id: "c1", name: "Priya Nair", first_name: "Priya", last_name: "Nair", role: "Data Engineer", requirement_title: resourceRole.title, project_name: resourceRole.project_name, pod_id: "ISG", division: "Front Office", business_unit: "Equities", stage: "RESUME_REVIEW", stage_age_days: 6, match_score: 92, level: "Principal", location: "New York", candidate_type: "EXTERNAL", skills: ["Python"], owner_name: "Jane Smith", ms_owner_name: "Daniel Kim", updated_at: "2026-08-20T00:00:00Z", interviews: [], timeline: [], offer: null, onboarding: null };
export const onboarding = { id: "on1", candidate_id: "c1", name: "Priya Nair", pod_id: "ISG", business_unit: "Equities", role: "Data Engineer", project_name: resourceRole.project_name, expected_start_date: "2026-09-08", overall_status: "BLOCKED", completed_steps: 1, total_steps: 10, blocked_steps: 1, responsible_party: "CAPCO", owner_name: "Jane Smith", blocker: "Profile approval pending", risk: "START_AT_RISK", risk_explanation: { remaining_steps: 9, historical_average_remaining_days: 12, days_until_expected_start: 7 }, steps: [
  { id: "s1", step_label: "PT ID Approved", status: "COMPLETE", responsible_party: "MORGAN_STANLEY" },
  { id: "s2", step_label: "Profile Worker Opened", status: "BLOCKED", responsible_party: "CAPCO", blocker_reason: "Profile approval pending" },
  { id: "s3", step_label: "Profile Worker Approved", status: "NOT_STARTED", responsible_party: "MORGAN_STANLEY" },
  { id: "s4", step_label: "Rehire Eligibility", status: "NOT_STARTED", responsible_party: "MORGAN_STANLEY" },
  { id: "s5", step_label: "Forms Uploaded", status: "NOT_STARTED", responsible_party: "CAPCO" },
  { id: "s6", step_label: "Forms Approved", status: "NOT_STARTED", responsible_party: "MORGAN_STANLEY" },
  { id: "s7", step_label: "Fingerprint Appointment Complete", status: "NOT_STARTED", responsible_party: "CAPCO" },
  { id: "s8", step_label: "Fingerprints Cleared", status: "NOT_STARTED", responsible_party: "MORGAN_STANLEY" },
  { id: "s9", step_label: "Attestation / MSID Activation", status: "NOT_STARTED", responsible_party: "MORGAN_STANLEY" },
  { id: "s10", step_label: "Ready to Start", status: "NOT_STARTED", responsible_party: "CAPCO" },
] };
export const resourcingOverview = { metrics: { open_demand: 2, critical_roles: 1, candidates: 1, with_ms: 1, offers: 0, pending_offers: 0, onboarding: 1, blocked: 1, starting_30_days: 1, starting_at_risk: 1, avg_time_to_fill: null, avg_onboarding_days: null, roles_over_30_days: 1, waiting_on_ms: 0, waiting_on_capco: 1, progressing: 0 }, funnel: [{ stage: "Demand", count: 2 }, { stage: "Sourcing", count: 1 }], critical_items: [], starting_soon: [], open_demand: [{ role: "Data Engineer", count: 2 }], analytics: [] };

export function responseFor(url) {
  const { pathname } = new URL(url);
  if (pathname === "/api/session") return { subject: "local-developer", roles: ["Account Admin"], permissions: { write: true } };
  if (pathname.endsWith("/map")) return mapResponse;
  if (pathname.endsWith("/filters")) return { divisions: ["Front Office", "Middle Office", "Back Office"], business_units: ["Equities", "Risk Management", "Operations"], team_types: ["Business", "Technology"], locations: ["New York"], levels: ["Managing Director"], relationship_strengths: ["Strong"], capco_owners: ["Priya Shah"], tags: ["Data"] };
  if (pathname === "/api/executive/weekly") return executiveWeekly;
  if (pathname.endsWith("/dashboard")) return { data_source: "sql", view_model: dashboard };
  if (pathname === "/api/resourcing/overview") return resourcingOverview;
  if (pathname === "/api/resourcing/options") return {
    engagements: [{ id: "p1", pod_id: "ISG", division_id: "d1", business_unit_id: "u1", business_unit: "Equities", name: "Data Modernization" }],
    employees: [{ id: "e1", name: "Priya Shah", role: "Account Executive" }],
    stakeholders: [{ id: "s2", name: "Emily Davis", title: "Head of Equities" }],
    priorities: ["CRITICAL", "HIGH", "MEDIUM", "LOW"], levels: ["Principal"], locations: ["New York"],
  };
  if (pathname === "/api/resource-requirements") return [resourceRole];
  if (pathname === "/api/resource-requirements/r1") return { ...resourceRole, candidates: [candidate] };
  if (pathname === "/api/candidates") return [candidate];
  if (pathname === "/api/candidates/c1") return candidate;
  if (pathname === "/api/onboarding") return [onboarding];
  if (pathname === "/api/onboarding/on1") return onboarding;
  if (pathname === "/api/stakeholders/s0/profile") return {
    stakeholder: mapResponse.stakeholders[0],
    team: { manager: null, direct_reports: mapResponse.stakeholders.filter((item) => item.manager_id === "s0"), reporting_line_known: false, is_primary_technology: false },
    meetings: [], notes: [], documents: [], opportunities: [], resourcing: {},
  };
  if (pathname === "/api/resourcing/trash") return [{ id: "r-archived", type: "ROLE", label: "Legacy Cloud Engineer", context: "Platform Modernization", affected_count: 2, archived_at: "2026-08-28T15:00:00Z", archived_by_name: "Account Admin", archive_reason: "Superseded requirement" }];
  if (pathname === "/api/stakeholders") return [mapResponse.stakeholders[1]];
  if (pathname === "/api/employees") return [{ id: "e1", name: "Priya Shah", role: "Account Executive", level: "Director", location: "New York" }];
  if (pathname.endsWith("/meeting-options") || pathname === "/api/opportunities") return [];
  if (pathname === "/api/assistant/conversations") return [];
  return {};
}
