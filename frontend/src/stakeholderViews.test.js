import { describe, expect, it } from "vitest";
import {
  DEFAULT_FILTERS, deriveFilterOptions, filterStakeholderRows, flattenCoverage,
  normalizeFilterOptions, rankInfluenceRows,
} from "./stakeholderViews";

const row = (overrides = {}, context = {}) => ({
  division: "Institutional Securities",
  unit: "Equities",
  teamType: "Business",
  person: {
    id: "person-1", name: "Ada Morgan", title: "Managing Director", location: "New York, US",
    level: "Managing Director", buyer: true, influencer: true, budgetHolder: true,
    relationship: "Strong", capcoOwner: "Priya Shah", opportunityCount: 2,
    lastMeeting: "Aug 20, 2026", tags: ["Data", "Trading"],
    ...overrides,
  },
  ...context,
});

describe("stakeholder view helpers", () => {
  const now = new Date("2026-08-31T12:00:00");
  const rows = [
    row(),
    row({ id: "person-2", name: "Ben Stone", title: "Director", location: "London, UK", level: "Director", buyer: false, influencer: true, budgetHolder: false, relationship: "Developing", capcoOwner: "Alex Morgan", opportunityCount: 0, lastMeeting: "Mar 1, 2026", tags: ["Cloud"] }, { division: "Wealth", unit: "Digital", teamType: "Technology" }),
  ];

  it.each([
    ["query", "Ada", { ...DEFAULT_FILTERS }],
    ["division", "", { ...DEFAULT_FILTERS, division: "Institutional Securities" }],
    ["unit", "", { ...DEFAULT_FILTERS, unit: "Equities" }],
    ["team", "", { ...DEFAULT_FILTERS, teamType: "Business" }],
    ["location", "", { ...DEFAULT_FILTERS, location: "New York, US" }],
    ["level", "", { ...DEFAULT_FILTERS, level: "Managing Director" }],
    ["buyer", "", { ...DEFAULT_FILTERS, influence: "Buyer" }],
    ["budget", "", { ...DEFAULT_FILTERS, budget: "Yes" }],
    ["relationship", "", { ...DEFAULT_FILTERS, relationship: "Strong" }],
    ["owner", "", { ...DEFAULT_FILTERS, owner: "Priya Shah" }],
    ["recency", "", { ...DEFAULT_FILTERS, recency: "Last 30 days" }],
    ["opportunities", "", { ...DEFAULT_FILTERS, opportunities: "Has opportunities" }],
    ["tags", "", { ...DEFAULT_FILTERS, tags: "Trading" }],
  ])("applies the %s filter consistently", (_name, query, filters) => {
    expect(filterStakeholderRows(rows, query, filters, now).map((item) => item.person.id)).toEqual(["person-1"]);
  });

  it("derives and normalizes canonical filter options", () => {
    const derived = deriveFilterOptions(rows);
    expect(derived.capco_owners).toEqual(["Alex Morgan", "Priya Shah"]);
    expect(derived.tags).toEqual(["Cloud", "Data", "Trading"]);
    expect(normalizeFilterOptions({ locations: ["Server location"] }, rows).locations).toEqual(["Server location"]);
    expect(normalizeFilterOptions({}, rows).business_units).toEqual(["Digital", "Equities"]);
  });

  it("ranks influence deterministically from canonical attributes", () => {
    expect(rankInfluenceRows(rows).map((item) => item.person.id)).toEqual(["person-1", "person-2"]);
  });

  it("flattens canonical coverage and respects organization filters", () => {
    const coverage = { divisions: [{ id: "d1", name: "Institutional Securities", business_units: [{ id: "u1", name: "Equities", coverage_score: 82, coverage: "Strong" }] }, { id: "d2", name: "Wealth", business_units: [{ id: "u2", name: "Digital", coverage_score: 55, coverage: "Medium" }] }] };
    expect(flattenCoverage(coverage, { ...DEFAULT_FILTERS, division: "Wealth" })).toEqual([expect.objectContaining({ id: "u2", division: "Wealth", coverage_score: 55 })]);
  });
});
