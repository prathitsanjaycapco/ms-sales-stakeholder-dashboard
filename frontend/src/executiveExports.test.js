import { describe, expect, it } from "vitest";
import { executiveBrief, executiveCsv } from "./executiveExports";

const data = {
  meta: { weekStart: "2026-08-31", weekEnd: "2026-09-06", pod: "ISG" },
  pulse: { activeEmployees: 12 },
  attentionItems: [{ title: "Approve recovery plan", severity: "RED", pod: "ISG", owner: "Priya", nextAction: "Meet sponsor" }],
  projects: [{ name: "Risk platform", health: "AMBER", pod: "ISG", commercialValue: 2500000 }],
  salesSummary: { opportunities: [{ name: "AI controls", stage: "Proposal", pod: "ISG", value: 400000, nextStep: "Pricing" }] },
};

describe("executive outputs", () => {
  it("creates a leadership-readable evidence brief", () => {
    const value = executiveBrief(data, { totalProjectValue: 2500000, atRiskValue: 2500000, atRiskPercent: 100, confidencePercent: 55 });
    expect(value).toContain("# Morgan Stanley account weekly brief");
    expect(value).toContain("Approve recovery plan");
    expect(value).toContain("Risk platform — AMBER");
    expect(value).toContain("AI controls — Proposal");
  });

  it("creates one escaped CSV containing actions, engagements, and opportunities", () => {
    const value = executiveCsv(data);
    expect(value.split("\r\n")).toHaveLength(4);
    expect(value).toContain('"leadership_action","Approve recovery plan"');
    expect(value).toContain('"engagement","Risk platform"');
    expect(value).toContain('"opportunity","AI controls"');
  });
});
