import { formatBackendDate } from "./dateUtils";

const shortDate = (value, emptyValue) => formatBackendDate(
  value,
  { month: "short", day: "numeric", year: "numeric" },
  emptyValue,
);

const byName = (left, right) => left.name.localeCompare(right.name) || left.id.localeCompare(right.id);

export function adaptBackendStakeholder(record) {
  return {
    id: record.id,
    name: record.name,
    title: record.title,
    level: record.level,
    location: record.location || "Not recorded",
    country: record.country_code || "",
    pod: record.pod,
    division: record.division,
    businessUnit: record.business_unit,
    teamType: record.team_type,
    organizationalRole: record.organizational_role,
    primaryTechnology: record.is_primary_technology,
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

function contextFor(person) {
  return { division: person.division, unit: person.businessUnit, teamType: person.teamType };
}

function breakCycles(managerByReport, records, diagnostics) {
  const state = new Map();
  const visit = (id, trail = []) => {
    if (!records.has(id) || state.get(id) === "done") return;
    const position = trail.indexOf(id);
    if (position >= 0) {
      const cycle = trail.slice(position).sort();
      const detachedId = cycle[0];
      managerByReport.delete(detachedId);
      diagnostics.cycles.push({ members: cycle, detached_id: detachedId });
      return;
    }
    if (state.get(id) === "visiting") return;
    state.set(id, "visiting");
    const managerId = managerByReport.get(id);
    if (managerId) visit(managerId, [...trail, id]);
    state.set(id, "done");
  };
  [...records.keys()].forEach((id) => visit(id));
}

function buildTree(id, peopleById, children, ancestry = new Set()) {
  const person = peopleById.get(id);
  if (!person || ancestry.has(id)) return null;
  const nextAncestry = new Set(ancestry);
  nextAncestry.add(id);
  return {
    ...person,
    context: contextFor(person),
    reports: (children.get(id) || [])
      .map((childId) => buildTree(childId, peopleById, children, nextAncestry))
      .filter(Boolean),
  };
}

const DEFAULT_DIVISION_COLORS = ["#1675d1", "#2b8a68", "#9a55b6", "#b67b2c", "#607d94"];

function presentationTree(ids, peopleById, managerByReport) {
  const members = new Set(ids.filter((id) => peopleById.has(id)));
  const children = new Map();
  members.forEach((id) => {
    const managerId = managerByReport.get(id);
    if (!members.has(managerId)) return;
    if (!children.has(managerId)) children.set(managerId, []);
    children.get(managerId).push(id);
  });
  children.forEach((childIds) => childIds.sort((left, right) => byName(peopleById.get(left), peopleById.get(right))));
  return [...members]
    .filter((id) => !members.has(managerByReport.get(id)))
    .sort((left, right) => byName(peopleById.get(left), peopleById.get(right)))
    .map((id) => ({
      ...buildTree(id, peopleById, children),
      externalManager: managerByReport.has(id) && !members.has(managerByReport.get(id))
        ? peopleById.get(managerByReport.get(id))?.name || "Manager outside this subdomain"
        : null,
    }));
}

function divisionDefinitions(response, people, placementById) {
  const definitions = new Map();
  (response.divisions || []).forEach((division, index) => definitions.set(division.name, {
    ...division,
    color: division.color || DEFAULT_DIVISION_COLORS[index % DEFAULT_DIVISION_COLORS.length],
    order: index,
    units: [...(division.units || [])],
  }));
  people
    .filter((person) => {
      const division = placementById.get(person.id)?.division || person.division;
      return division && division !== "Enterprise Functions";
    })
    .forEach((person) => {
      const division = placementById.get(person.id)?.division || person.division;
      if (!definitions.has(division)) definitions.set(division, {
        id: `division-${division}`,
        name: division,
        color: DEFAULT_DIVISION_COLORS[definitions.size % DEFAULT_DIVISION_COLORS.length],
        order: definitions.size,
        units: [],
      });
    });
  return [...definitions.values()].sort((left, right) => left.order - right.order || left.name.localeCompare(right.name));
}

function enterpriseDefinitions(response, people, placementById) {
  const definitions = new Map((response.enterprise_functions || []).map((group, index) => [group.name, { ...group, order: index }]));
  people.filter((person) => (placementById.get(person.id)?.division || person.division) === "Enterprise Functions").forEach((person) => {
    const unit = placementById.get(person.id)?.unit || person.businessUnit;
    if (!definitions.has(unit)) definitions.set(unit, {
      id: `enterprise-${unit}`,
      name: unit,
      lead_stakeholder_id: null,
      member_ids: [],
      order: definitions.size,
    });
  });
  return [...definitions.values()].sort((left, right) => left.order - right.order || left.name.localeCompare(right.name));
}

/** Converts the canonical response into the deliberately compact map projection. */
export function adaptBackendMap(response) {
  const records = new Map((response.stakeholders || []).map((stakeholder) => [stakeholder.id, stakeholder]));
  const peopleById = new Map([...records.values()].map((record) => [record.id, adaptBackendStakeholder(record)]));
  const managerByReport = new Map();
  const diagnostics = { missingManagers: [], duplicateReports: [], cycles: [] };

  (response.reporting_lines || []).forEach(({ manager_id: managerId, report_id: reportId }) => {
    if (!records.has(reportId) || !records.has(managerId) || reportId === managerId) {
      diagnostics.missingManagers.push({ manager_id: managerId, report_id: reportId });
      return;
    }
    if (managerByReport.has(reportId)) {
      diagnostics.duplicateReports.push({ manager_id: managerId, report_id: reportId });
      return;
    }
    managerByReport.set(reportId, managerId);
  });
  [...records.values()].forEach((record) => {
    if (!record.manager_id) {
      if (record.id !== response.pod_head_stakeholder_id && record.organizational_role !== "Pod Head") {
        diagnostics.missingManagers.push({ manager_id: null, report_id: record.id });
      }
      return;
    }
    if (managerByReport.has(record.id)) return;
    if (records.has(record.manager_id) && record.manager_id !== record.id) managerByReport.set(record.id, record.manager_id);
    else diagnostics.missingManagers.push({ manager_id: record.manager_id, report_id: record.id });
  });
  breakCycles(managerByReport, records, diagnostics);

  const children = new Map();
  managerByReport.forEach((managerId, reportId) => {
    if (!children.has(managerId)) children.set(managerId, []);
    children.get(managerId).push(reportId);
    peopleById.get(reportId).manager = peopleById.get(managerId)?.name || null;
  });
  children.forEach((childIds) => childIds.sort((left, right) => byName(peopleById.get(left), peopleById.get(right))));

  const roots = [...peopleById.values()]
    .filter((person) => !managerByReport.has(person.id))
    .sort(byName)
    .map((person) => buildTree(person.id, peopleById, children))
    .filter(Boolean);
  const count = (node) => 1 + node.reports.reduce((total, report) => total + count(report), 0);
  const people = [...peopleById.values()].sort(byName);
  const placementById = new Map();
  (response.divisions || []).forEach((division) => {
    if (division.head_stakeholder_id) placementById.set(division.head_stakeholder_id, { division: division.name, unit: "Division Leadership" });
    (division.units || []).forEach((unit) => {
      (unit.business_stakeholder_ids || []).forEach((id) => placementById.set(id, { division: division.name, unit: unit.name }));
      if (unit.primary_technology_id) placementById.set(unit.primary_technology_id, { division: division.name, unit: unit.name });
    });
  });
  (response.enterprise_functions || []).forEach((group) => {
    [group.lead_stakeholder_id, ...(group.member_ids || [])].filter(Boolean).forEach((id) => placementById.set(id, { division: "Enterprise Functions", unit: group.name }));
  });
  const divisions = divisionDefinitions(response, people, placementById).map((definition) => {
    const assigned = people.filter((person) => (placementById.get(person.id)?.division || person.division) === definition.name);
    const head = peopleById.get(definition.head_stakeholder_id)
      || assigned.find((person) => person.organizationalRole === "Division Head")
      || assigned.find((person) => person.businessUnit === "Division Leadership")
      || null;
    const unitDefinitions = new Map((definition.units || []).map((unit, index) => [unit.name, { ...unit, order: unit.sort_order ?? index }]));
    assigned.filter((person) => person.id !== head?.id).forEach((person) => {
      const unitName = placementById.get(person.id)?.unit || person.businessUnit || "Unassigned";
      if (!unitDefinitions.has(unitName)) unitDefinitions.set(unitName, {
        id: `unit-${definition.name}-${unitName}`,
        name: unitName,
        order: unitDefinitions.size,
      });
    });
    const units = [...unitDefinitions.values()]
      .sort((left, right) => left.order - right.order || left.name.localeCompare(right.name))
      .map((unit) => {
        const members = assigned.filter((person) => person.id !== head?.id && (placementById.get(person.id)?.unit || person.businessUnit || "Unassigned") === unit.name);
        const businessIds = members.filter((person) => person.teamType !== "Technology").map((person) => person.id);
        const primaryTechnologyId = unit.primary_technology_id
          || members.find((person) => person.primaryTechnology)?.id
          || null;
        const primaryTechnology = primaryTechnologyId && peopleById.has(primaryTechnologyId)
          ? { ...peopleById.get(primaryTechnologyId), context: { division: definition.name, unit: unit.name, teamType: "Technology" }, reports: [] }
          : null;
        return {
          ...unit,
          businessRoots: presentationTree(businessIds, peopleById, managerByReport),
          businessRoot: presentationTree(businessIds, peopleById, managerByReport)[0] || null,
          primaryTechnology,
          primaryTechnologyId,
          memberCount: members.length,
          technologyTeamSize: members.filter((person) => person.teamType === "Technology").length,
        };
      });
    return { ...definition, head, units };
  });

  const enterprise = enterpriseDefinitions(response, people, placementById).map((definition) => {
    const assigned = people.filter((person) => (placementById.get(person.id)?.division || person.division) === "Enterprise Functions"
      && (placementById.get(person.id)?.unit || person.businessUnit) === definition.name);
    const assignedIds = assigned.map((person) => person.id);
    const rootsForGroup = presentationTree(assignedIds, peopleById, managerByReport);
    return { ...definition, roots: rootsForGroup, memberCount: assigned.length };
  });

  const podHead = peopleById.get(response.pod_head_stakeholder_id) || null;
  const visualIds = new Set();
  if (podHead) visualIds.add(podHead.id);
  divisions.forEach((division) => {
    if (division.head) visualIds.add(division.head.id);
    division.units.forEach((unit) => {
      unit.businessRoots.forEach((root) => {
        const collect = (node) => { visualIds.add(node.id); node.reports.forEach(collect); };
        collect(root);
      });
      if (unit.primaryTechnology) visualIds.add(unit.primaryTechnology.id);
    });
  });
  enterprise.forEach((group) => group.roots.forEach((root) => {
    const collect = (node) => { visualIds.add(node.id); node.reports.forEach(collect); };
    collect(root);
  }));
  const hiddenTechnologyCount = people.filter((person) => person.teamType === "Technology" && !person.primaryTechnology).length;

  return {
    title: `${response.pod} Stakeholder Map`,
    people,
    roots,
    podHead,
    divisions,
    enterprise,
    diagnostics: {
      ...diagnostics,
      canonicalCount: peopleById.size,
      hierarchyCount: roots.reduce((total, root) => total + count(root), 0),
      renderedCount: visualIds.size,
      hiddenTechnologyCount,
    },
  };
}
