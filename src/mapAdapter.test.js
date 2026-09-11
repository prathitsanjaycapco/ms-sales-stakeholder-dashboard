import { describe, expect, it } from "vitest";
import { adaptBackendMap, adaptBackendStakeholder } from "./mapAdapter";


const stakeholder = (id, overrides = {}) => ({
  id, name: id, title: "Leader", level: "Vice President", location: "New York",
  country_code: "US", is_buyer: false, is_influencer: true, is_budget_holder: false,
  relationship_strength: "Medium", capco_contingents: 1, capco_owner: "Owner",
  opportunity_count: 0, tags: [], biography: "", division: "Front Office",
  business_unit: "Equities", team_type: "Business", manager_id: null, ...overrides,
});


describe("canonical map adapter", () => {
  it("preserves backend calendar dates in the user's timezone", () => {
    const adapted = adaptBackendStakeholder(stakeholder("dated", {
      last_meeting: "2026-08-15",
      next_meeting: "2026-09-10",
    }));
    expect(adapted.lastMeeting).toBe("Aug 15, 2026");
    expect(adapted.nextMeeting).toBe("Sep 10, 2026");
  });

  it("builds a complete reporting tree from canonical reporting lines", () => {
    const response = {
      pod: "ISG",
      stakeholders: [
        stakeholder("division-head", { business_unit: "Division Leadership" }),
        stakeholder("business-head", { manager_id: "division-head" }),
        stakeholder("buyer", { manager_id: "business-head", is_buyer: true }),
        stakeholder("tech", { team_type: "Technology", is_primary_technology: true }),
      ],
      reporting_lines: [
        { manager_id: "division-head", report_id: "business-head" },
        { manager_id: "business-head", report_id: "buyer" },
        { manager_id: "buyer", report_id: "business-head" },
      ],
      divisions: [{
        id: "isg-front-office", name: "Front Office", color: "#1675d1",
        head_stakeholder_id: "division-head",
        units: [{ id: "equities", name: "Equities", business_stakeholder_ids: ["business-head", "buyer"], primary_technology_id: "tech", reporting_unknown_ids: [] }],
      }],
      enterprise_functions: [],
    };
    const map = adaptBackendMap(response);
    expect(map.people.map((person) => person.id).sort()).toEqual(["business-head", "buyer", "division-head", "tech"]);
    expect(map.diagnostics.cycles).toHaveLength(0);
    expect(map.diagnostics.duplicateReports).toHaveLength(1);
    expect(map.diagnostics.renderedCount).toBe(4);
    expect(map.roots.flatMap((root) => [root.id, ...root.reports.map((person) => person.id)])).toContain("business-head");
    expect(map.people.find((person) => person.id === "tech").primaryTechnology).toBe(true);
  });

  it("keeps people with a missing manager as explicit roots and reports the data issue", () => {
    const map = adaptBackendMap({
      pod: "ISG", stakeholders: [stakeholder("orphan", { manager_id: "missing" })], reporting_lines: [],
      divisions: [],
      enterprise_functions: [],
    });
    expect(map.roots.map((person) => person.id)).toEqual(["orphan"]);
    expect(map.diagnostics.missingManagers).toEqual([{ manager_id: "missing", report_id: "orphan" }]);
  });

  it("keeps cross-business-unit reporting lines instead of using assignment buckets", () => {
    const map = adaptBackendMap({
      pod: "ISG",
      stakeholders: [
        stakeholder("division-head", { business_unit: "Division Leadership" }),
        stakeholder("unit-head", { business_unit: "Equities", manager_id: "division-head" }),
        stakeholder("technologist", { business_unit: "Equities", team_type: "Technology", manager_id: "unit-head", is_primary_technology: true }),
      ],
      reporting_lines: [
        { manager_id: "division-head", report_id: "unit-head" },
        { manager_id: "unit-head", report_id: "technologist" },
      ],
      divisions: [], enterprise_functions: [],
    });
    expect(map.roots).toHaveLength(1);
    expect(map.roots[0].reports[0].id).toBe("unit-head");
    expect(map.roots[0].reports[0].reports[0].id).toBe("technologist");
    expect(map.divisions.map((group) => group.name)).toEqual(["Front Office"]);
    expect(map.divisions[0].units[0].businessRoots[0].id).toBe("unit-head");
    expect(map.divisions[0].units[0].primaryTechnology.id).toBe("technologist");
    expect(map.diagnostics.renderedCount).toBe(3);
  });

  it("places business members and only the primary technology manager on the map", () => {
    const map = adaptBackendMap({
      pod: "ISG",
      stakeholders: [
        stakeholder("division-head", { business_unit: "Division Leadership", organizational_role: "Division Head" }),
        stakeholder("business-head", { organizational_role: "Business Unit Head", manager_id: "division-head" }),
        stakeholder("business-report", { manager_id: "business-head" }),
        stakeholder("tech-manager", { team_type: "Technology", is_primary_technology: true }),
        stakeholder("tech-report", { team_type: "Technology", manager_id: "tech-manager" }),
      ],
      reporting_lines: [
        { manager_id: "division-head", report_id: "business-head" },
        { manager_id: "business-head", report_id: "business-report" },
        { manager_id: "tech-manager", report_id: "tech-report" },
      ],
      divisions: [{
        id: "front-office", name: "Front Office", color: "#1675d1", head_stakeholder_id: "division-head",
        units: [{ id: "equities", name: "Equities", primary_technology_id: "tech-manager", sort_order: 0 }],
      }],
      enterprise_functions: [],
    });
    const unit = map.divisions[0].units[0];
    expect(unit.businessRoots[0].reports.map((person) => person.id)).toEqual(["business-report"]);
    expect(unit.primaryTechnology.id).toBe("tech-manager");
    expect(unit.primaryTechnology.reports).toEqual([]);
    expect(map.people.map((person) => person.id)).toContain("tech-report");
    expect(map.diagnostics.hiddenTechnologyCount).toBe(1);
    expect(map.diagnostics.renderedCount).toBe(4);
    expect(unit.memberCount).toBe(4);
  });

  it("exposes the canonical pod head above the division lanes", () => {
    const map = adaptBackendMap({
      pod: "ISG",
      pod_head_stakeholder_id: "pod-head",
      stakeholders: [
        stakeholder("pod-head", { division: null, business_unit: null, organizational_role: "Pod Head", manager_id: null }),
        stakeholder("division-head", { organizational_role: "Division Head", manager_id: "pod-head" }),
      ],
      reporting_lines: [{ manager_id: "pod-head", report_id: "division-head" }],
      divisions: [{ id: "front-office", name: "Front Office", head_stakeholder_id: "division-head", units: [] }],
      enterprise_functions: [],
    });
    expect(map.podHead.id).toBe("pod-head");
    expect(map.divisions[0].head.id).toBe("division-head");
    expect(map.diagnostics.renderedCount).toBe(2);
  });

  it("breaks malformed reporting cycles deterministically without losing people", () => {
    const map = adaptBackendMap({
      pod: "ISG",
      stakeholders: [stakeholder("alpha"), stakeholder("beta")],
      reporting_lines: [{ manager_id: "alpha", report_id: "beta" }, { manager_id: "beta", report_id: "alpha" }],
      divisions: [], enterprise_functions: [],
    });
    expect(map.diagnostics.cycles).toHaveLength(1);
    expect(map.diagnostics.renderedCount).toBe(2);
    expect(map.roots).toHaveLength(1);
  });
});
