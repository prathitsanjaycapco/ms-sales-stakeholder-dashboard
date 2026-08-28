const shortDate = (value, emptyValue) => value
  ? new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value))
  : emptyValue;

export function adaptBackendStakeholder(record) {
  return {
    id: record.id,
    name: record.name,
    title: record.title,
    level: record.level,
    location: record.location,
    country: record.country_code,
    buyer: record.is_buyer,
    influencer: record.is_influencer,
    budgetHolder: record.is_budget_holder,
    keyStakeholder: record.is_buyer || record.relationship_strength === "Strong",
    relationship: record.relationship_strength,
    capcoContacts: record.capco_contingents,
    capcoOwner: record.capco_owner,
    opportunityCount: record.opportunity_count,
    budget: record.budget_amount,
    lastMeeting: shortDate(record.last_meeting || record.last_meeting_at, "Not recorded"),
    nextMeeting: shortDate(record.next_meeting || record.next_meeting_at, "Not scheduled"),
    tags: record.tags || [],
    bio: record.biography || "",
    manager: null,
    reports: [],
  };
}

function stakeholderAdapter(records, children, id, allowedIds = null, ancestry = new Set()) {
  const record = records.get(id);
  if (!record) return null;
  const nextAncestry = new Set(ancestry);
  nextAncestry.add(id);
  const reportIds = (children.get(id) || []).filter((childId) =>
    !nextAncestry.has(childId) && (!allowedIds || allowedIds.has(childId))
  );
  return {
    ...adaptBackendStakeholder(record),
    manager: record.manager_id ? records.get(record.manager_id)?.name : null,
    reports: reportIds.map((childId) => stakeholderAdapter(records, children, childId, allowedIds, nextAncestry)).filter(Boolean),
  };
}

export function adaptBackendMap(response) {
  const records = new Map(response.stakeholders.map((stakeholder) => [stakeholder.id, stakeholder]));
  const children = new Map();
  response.reporting_lines.forEach(({ manager_id: managerId, report_id: reportId }) => {
    if (!children.has(managerId)) children.set(managerId, []);
    children.get(managerId).push(reportId);
  });
  const person = (id, allowedIds = null) => stakeholderAdapter(records, children, id, allowedIds);
  const divisions = response.divisions.map((division) => ({
    id: division.id,
    name: division.name,
    color: division.color,
    head: person(division.head_stakeholder_id, new Set([division.head_stakeholder_id])),
    units: division.units.map((unit) => {
      const businessIds = new Set(unit.business_stakeholder_ids);
      const technologyIds = new Set(response.stakeholders
        .filter((stakeholder) => stakeholder.division === division.name && stakeholder.business_unit === unit.name && stakeholder.team_type === "Technology")
        .map((stakeholder) => stakeholder.id));
      return {
        id: unit.id,
        name: unit.name,
        lead: person(unit.business_stakeholder_ids[0], businessIds),
        primaryTechnology: person(unit.primary_technology_id, technologyIds),
        unknownReports: unit.reporting_unknown_ids.map((id) => person(id, businessIds)).filter(Boolean),
      };
    }),
  }));
  const enterprise = response.enterprise_functions.map((group) => ({
    id: group.id,
    name: group.name,
    lead: person(group.lead_stakeholder_id, new Set([group.lead_stakeholder_id])),
    members: group.member_ids.map((id) => person(id, new Set([id]))).filter(Boolean),
  }));
  return { title: `${response.pod} Stakeholder Map`, divisions, enterprise };
}
