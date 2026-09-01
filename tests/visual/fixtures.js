const stakeholder = (id, name, title, extras = {}) => ({
  id, name, title, pod: "ISG", division: "Institutional Securities", business_unit: "Equities",
  team_type: "Business", level: "Managing Director", location: "New York", country_code: "US",
  relationship_strength: "Strong", capco_contingents: 2, capco_owner: "Priya Shah",
  opportunity_count: 1, is_buyer: false, is_influencer: true, is_budget_holder: false,
  tags: ["Data", "Transformation"], ...extras,
});

export const mapResponse = {
  pod: "ISG",
  stakeholders: [
    stakeholder("s1", "John Smith", "Division Head", { is_buyer: true }),
    stakeholder("s2", "Emily Davis", "Head of Equities", { manager_id: "s1", is_budget_holder: true }),
    stakeholder("s3", "Anna Clark", "Equities Coverage Lead", { manager_id: "s2" }),
    stakeholder("s4", "Daniel Kim", "VP, Equities Technology", { team_type: "Technology" }),
    stakeholder("s5", "Priya Nair", "HR Director", { division: "Enterprise", business_unit: "Human Resources" }),
  ],
  reporting_lines: [{ manager_id: "s1", report_id: "s2" }, { manager_id: "s2", report_id: "s3" }],
  divisions: [{ id: "d1", name: "Front Office", color: "blue", head_stakeholder_id: "s1", units: [{ id: "u1", name: "Equities", business_stakeholder_ids: ["s2", "s3"], primary_technology_id: "s4", reporting_unknown_ids: [] }] }],
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

export const resourceRole = { id: "r1", pod_id: "ISG", division: "Front Office", business_unit: "Equities", project_name: "Data Modernization", title: "Senior Data Engineer", role: "Data Engineer", required_skills: ["Python", "AWS"], priority: "CRITICAL", requested_headcount: 3, filled_headcount: 1, remaining_headcount: 2, candidate_count: 1, target_start_date: "2026-09-20", location: "New York", age_days: 35, owner_name: "Jane Smith", client_name: "Daniel Kim", level: "Principal" };
export const candidate = { id: "c1", name: "Priya Nair", first_name: "Priya", last_name: "Nair", role: "Data Engineer", requirement_title: resourceRole.title, project_name: resourceRole.project_name, pod_id: "ISG", division: "Front Office", business_unit: "Equities", stage: "MS_REVIEW", stage_age_days: 6, match_score: 92, level: "Principal", location: "New York", candidate_type: "EXTERNAL", skills: ["Python"], owner_name: "Jane Smith", ms_owner_name: "Daniel Kim", interviews: [], timeline: [], offer: null, onboarding: null };
export const onboarding = { id: "on1", candidate_id: "c1", name: "Priya Nair", pod_id: "ISG", business_unit: "Equities", role: "Data Engineer", project_name: resourceRole.project_name, expected_start_date: "2026-09-08", overall_status: "BLOCKED", completed_steps: 1, total_steps: 2, blocked_steps: 1, responsible_party: "CAPCO", owner_name: "Jane Smith", blocker: "Profile approval pending", risk: "START_AT_RISK", steps: [] };
export const resourcingOverview = { metrics: { open_demand: 2, critical_roles: 1, candidates: 1, with_ms: 1, offers: 0, pending_offers: 0, onboarding: 1, blocked: 1, starting_30_days: 1, starting_at_risk: 1, avg_time_to_fill: null, avg_onboarding_days: null, roles_over_30_days: 1, waiting_on_ms: 0, waiting_on_capco: 1, progressing: 0 }, funnel: [{ stage: "Demand", count: 2 }, { stage: "Sourcing", count: 1 }], critical_items: [], starting_soon: [], open_demand: [{ role: "Data Engineer", count: 2 }], analytics: [] };

export function responseFor(url) {
  const { pathname } = new URL(url);
  if (pathname === "/api/session") return { subject: "local-developer", roles: ["Account Admin"], permissions: { write: true } };
  if (pathname.endsWith("/map")) return mapResponse;
  if (pathname.endsWith("/filters")) return { divisions: ["Institutional Securities"], business_units: ["Equities"], team_types: ["Business", "Technology"], locations: ["New York"], levels: ["Managing Director"], relationship_strengths: ["Strong"], capco_owners: ["Priya Shah"], tags: ["Data"] };
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
  if (pathname === "/api/candidates") return [candidate];
  if (pathname === "/api/onboarding") return [onboarding];
  if (pathname === "/api/stakeholders") return [mapResponse.stakeholders[1]];
  if (pathname === "/api/employees") return [{ id: "e1", name: "Priya Shah", role: "Account Executive", level: "Director", location: "New York" }];
  if (pathname.endsWith("/meeting-options") || pathname === "/api/opportunities") return [];
  if (pathname === "/api/assistant/conversations") return [];
  return {};
}
