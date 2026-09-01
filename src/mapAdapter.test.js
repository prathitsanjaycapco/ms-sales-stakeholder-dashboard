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

  it("preserves canonical IDs and prevents reporting cycles from duplicating people", () => {
    const response = {
      pod: "ISG",
      stakeholders: [
        stakeholder("division-head", { business_unit: "Division Leadership" }),
        stakeholder("business-head", { manager_id: "division-head" }),
        stakeholder("buyer", { manager_id: "business-head", is_buyer: true }),
        stakeholder("tech", { team_type: "Technology" }),
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
    const unit = map.divisions[0].units[0];
    expect(unit.lead.id).toBe("business-head");
    expect(unit.lead.reports.map((person) => person.id)).toEqual(["buyer"]);
    expect(unit.lead.reports[0].reports).toEqual([]);
    expect(unit.primaryTechnology.id).toBe("tech");
  });

  it("does not invent missing map entities", () => {
    const map = adaptBackendMap({
      pod: "ISG", stakeholders: [], reporting_lines: [],
      divisions: [{ id: "d", name: "Front Office", color: "#000", head_stakeholder_id: "missing", units: [] }],
      enterprise_functions: [],
    });
    expect(map.divisions[0].head).toBeNull();
  });
});
