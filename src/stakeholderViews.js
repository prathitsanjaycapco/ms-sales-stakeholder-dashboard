export const DEFAULT_FILTERS = {
  division: "All",
  unit: "All",
  teamType: "All",
  location: "All",
  level: "All",
  influence: "All",
  budget: "All",
  relationship: "All",
  owner: "All",
  recency: "All",
  opportunities: "All",
  tags: "All",
};

const unique = (values) => [...new Set(values.filter(Boolean))].sort((left, right) => left.localeCompare(right));

export function deriveFilterOptions(rows) {
  return {
    divisions: unique(rows.map((row) => row.division).filter((value) => value !== "Enterprise Functions")),
    business_units: unique(rows.map((row) => row.unit).filter((value) => value !== "Division Leadership")),
    team_types: unique(rows.map((row) => row.teamType)),
    locations: unique(rows.map((row) => row.person.location)),
    levels: unique(rows.map((row) => row.person.level)),
    relationship_strengths: unique(rows.map((row) => row.person.relationship)),
    capco_owners: unique(rows.map((row) => row.person.capcoOwner)),
    tags: unique(rows.flatMap((row) => row.person.tags || [])),
  };
}

export function normalizeFilterOptions(options, rows) {
  const fallback = deriveFilterOptions(rows);
  const normalized = {};
  Object.keys(fallback).forEach((key) => {
    normalized[key] = Array.isArray(options?.[key]) && options[key].length ? unique(options[key]) : fallback[key];
  });
  return normalized;
}

export function matchesStakeholderRow(row, query = "", filters = DEFAULT_FILTERS, now = new Date()) {
  const stakeholder = row.person;
  const haystack = [stakeholder.name, stakeholder.title, row.division, row.unit, ...(stakeholder.tags || [])].join(" ").toLowerCase();
  if (query.trim() && !haystack.includes(query.trim().toLowerCase())) return false;
  if (filters.division !== "All" && row.division !== filters.division) return false;
  if (filters.unit !== "All" && row.unit !== filters.unit) return false;
  if (filters.teamType !== "All" && row.teamType !== filters.teamType) return false;
  if (filters.location !== "All" && stakeholder.location !== filters.location) return false;
  if (filters.level !== "All" && stakeholder.level !== filters.level) return false;
  if (filters.influence === "Buyer" && !stakeholder.buyer) return false;
  if (filters.influence === "Influencer" && !stakeholder.influencer) return false;
  if (filters.budget === "Yes" && !stakeholder.budgetHolder) return false;
  if (filters.budget === "No" && stakeholder.budgetHolder) return false;
  if (filters.relationship !== "All" && stakeholder.relationship !== filters.relationship) return false;
  if (filters.owner !== "All" && stakeholder.capcoOwner !== filters.owner) return false;
  if (filters.recency !== "All") {
    const meetingDate = Date.parse(stakeholder.lastMeeting);
    const today = new Date(now); today.setHours(0, 0, 0, 0);
    const daysSinceMeeting = Number.isNaN(meetingDate) ? Infinity : (today.getTime() - meetingDate) / 86400000;
    if (filters.recency === "Last 30 days" && daysSinceMeeting > 30) return false;
    if (filters.recency === "Last 90 days" && daysSinceMeeting > 90) return false;
    if (filters.recency === "No recent meeting" && daysSinceMeeting <= 90) return false;
  }
  if (filters.opportunities === "Has opportunities" && stakeholder.opportunityCount < 1) return false;
  if (filters.tags !== "All" && !(stakeholder.tags || []).includes(filters.tags)) return false;
  return true;
}

export function filterStakeholderRows(rows, query, filters, now) {
  return rows.filter((row) => matchesStakeholderRow(row, query, filters, now));
}

const relationshipRank = { Strong: 4, Medium: 3, Developing: 2, Unknown: 1 };

export function rankInfluenceRows(rows) {
  return [...rows].sort((left, right) => {
    const a = left.person;
    const b = right.person;
    return Number(b.buyer) - Number(a.buyer)
      || Number(b.budgetHolder) - Number(a.budgetHolder)
      || Number(b.influencer) - Number(a.influencer)
      || (relationshipRank[b.relationship] || 0) - (relationshipRank[a.relationship] || 0)
      || (b.opportunityCount || 0) - (a.opportunityCount || 0)
      || a.name.localeCompare(b.name);
  });
}

export function flattenCoverage(coverage, filters = DEFAULT_FILTERS) {
  if (!coverage?.divisions) return [];
  return coverage.divisions.flatMap((division) => division.business_units.map((unit) => ({
    ...unit,
    division: division.name,
    divisionId: division.id,
  }))).filter((unit) =>
    (filters.division === "All" || unit.division === filters.division)
    && (filters.unit === "All" || unit.name === filters.unit)
  );
}
