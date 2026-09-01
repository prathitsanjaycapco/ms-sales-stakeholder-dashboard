// @vitest-environment jsdom
import React from "react";
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ getExecutiveWeekly: vi.fn() }));
vi.mock("./api", () => ({ api }));
import ExecutiveView, { deriveExecutivePosture } from "./ExecutiveView";

const weekly = {
  meta: { weekStart: "2026-08-31", weekEnd: "2026-09-06", pod: "All" },
  pulse: { activeEmployees: 1, importantEvents: 1, attentionItems: 1, activeProjects: 0, pipeline: 250000, upcomingMilestones: 0 },
  teamActivity: [{
    id: "employee-1", name: "Priya Shah", title: "Account Executive", role: "Account Executive",
    level: "Director", location: "New York", capabilities: ["Strategy"], pods: ["ISG"],
    primaryProject: "Equities", allocationPercent: 120, assignments: [], activities: [], nextFewWeeks: [],
    stakeholders: [], opportunities: [],
  }],
  attentionItems: [{
    id: "attention-1", severity: "RED", category: "DELIVERY", title: "Delivery escalation",
    pod: "MSIM", context: "Recovery required", owner: "Priya Shah", nextAction: "Agree recovery plan",
    engagementId: "engagement-attention", stakeholderId: "stakeholder-attention", opportunityId: "opportunity-attention",
  }],
  weeklyCalendar: [{
    id: "event-1", sourceType: "meeting", sourceId: "meeting-1", type: "client", title: "Client checkpoint",
    date: "2026-08-31", start: "2026-08-31T10:00:00-04:00", allDay: false, pod: "Wealth Management",
    employees: [], importance: "High", isClient: true,
  }],
  podSummaries: [], upcomingWeeks: [], projects: [],
  salesSummary: {
    pipeline: 250000, weightedPipeline: 125000, nearTermOpportunities: 1, upcomingProposalsDecisions: 1,
    opportunities: [{ id: "opportunity-1", name: "Digital proposal", pod: "MSIM", stage: "Proposal", value: 250000, nextStep: "Client decision" }],
  },
  recommendations: [{
    id: "recommendation-1", priority: "High", category: "DELIVERY", recommendation: "Protect delivery",
    why: "Milestone risk", suggestedAction: "Convene sponsors", pod: "MSIM",
    relatedEntities: { engagementIds: ["engagement-1"], stakeholderIds: ["stakeholder-1"], opportunityIds: ["opportunity-2"] },
  }],
  changes: [],
};

const callbacks = () => ({
  onOpenPod: vi.fn(), onOpenStakeholder: vi.fn(), onOpenEmployee: vi.fn(),
  onOpenEngagement: vi.fn(), onOpenMeeting: vi.fn(), onOpenOpportunity: vi.fn(),
});

beforeEach(() => api.getExecutiveWeekly.mockResolvedValue(weekly));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe("Executive View cross-screen links", () => {
  it("derives account-head exposure and commercial confidence from canonical portfolio values", () => {
    const posture = deriveExecutivePosture({
      projects: [
        { pod: "ISG", health: "GREEN", commercialValue: 3000000 },
        { pod: "MSIM", health: "RED", commercialValue: 2000000 },
      ],
      podSummaries: [{ pod: "MSIM", criticalIssues: 2 }],
      teamActivity: [{ id: "e1", allocationPercent: 125, pods: ["ISG", "MSIM"] }],
      salesSummary: { pipeline: 4000000, weightedPipeline: 1500000 },
    });
    expect(posture.totalProjectValue).toBe(5000000);
    expect(posture.atRiskValue).toBe(2000000);
    expect(posture.atRiskPercent).toBe(40);
    expect(posture.confidencePercent).toBe(38);
    expect(posture.pressurePeople).toHaveLength(1);
    expect(posture.crossPodPeople).toBe(1);
  });

  it("keeps the source pod attached to meeting and opportunity drill-downs", async () => {
    const user = userEvent.setup();
    const handlers = callbacks();
    render(<ExecutiveView pod="All" {...handlers} />);
    await user.click(await screen.findByRole("button", { name: /Client checkpoint/i }));
    expect(handlers.onOpenMeeting).toHaveBeenCalledWith("meeting-1", "Wealth Management");
    await user.click(screen.getByRole("button", { name: /Digital proposal/i }));
    expect(handlers.onOpenOpportunity).toHaveBeenCalledWith("opportunity-1", "MSIM");
  });

  it("exposes recommendation evidence as working navigation and closes the detail drawer", async () => {
    const user = userEvent.setup();
    const handlers = callbacks();
    render(<ExecutiveView pod="All" {...handlers} />);
    await user.click(await screen.findByText("Protect delivery"));
    expect(screen.getByRole("dialog", { name: /Protect delivery details/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Open engagement/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Open stakeholder/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Open opportunity/i }));
    expect(handlers.onOpenOpportunity).toHaveBeenCalledWith("opportunity-2", "MSIM");
    await waitFor(() => expect(screen.queryByRole("dialog", { name: /Protect delivery details/i })).not.toBeInTheDocument());
  });

  it("shows attention context before navigating and avoids stacked employee drawers", async () => {
    const user = userEvent.setup();
    const handlers = callbacks();
    render(<ExecutiveView pod="All" {...handlers} />);
    await user.click(await screen.findByRole("button", { name: /Delivery escalation/i }));
    expect(handlers.onOpenEngagement).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog", { name: /Delivery escalation details/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Close detail/i }));
    await user.click(screen.getByRole("button", { name: /Priya Shah.*Equities.*120%/i }));
    await user.click(screen.getByRole("button", { name: /Open full account profile/i }));
    expect(handlers.onOpenEmployee).toHaveBeenCalledWith("employee-1");
    expect(screen.queryByRole("dialog", { name: /Priya Shah details/i })).not.toBeInTheDocument();
  });

  it("filters the connected project list by delivery health and opens canonical engagement detail", async () => {
    const user = userEvent.setup();
    const handlers = callbacks();
    api.getExecutiveWeekly.mockResolvedValue({
      ...weekly,
      projects: [
        { id: "engagement-green", name: "Green program", pod: "ISG", businessUnit: "Equities", health: "GREEN", commercialValue: 3000000, nextMilestone: null },
        { id: "engagement-red", name: "Red recovery", pod: "MSIM", businessUnit: "Investment Management", health: "RED", commercialValue: 2000000, nextMilestone: null },
      ],
    });
    render(<ExecutiveView pod="All" {...handlers} />);
    await screen.findByRole("button", { name: /Open Green program engagement details/i });
    await user.click(screen.getByRole("button", { name: /RED.*\$2M.*1 projects/i }));
    expect(screen.queryByRole("button", { name: /Open Green program engagement details/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Open Red recovery engagement details/i }));
    expect(handlers.onOpenEngagement).toHaveBeenCalledWith("engagement-red");
  });

  it("opens resourcing in the currently selected executive pod", async () => {
    const user = userEvent.setup();
    const handlers = { ...callbacks(), onOpenResourcing: vi.fn() };
    api.getExecutiveWeekly.mockResolvedValue({ ...weekly, resourcing: { open_demand: 2, onboarding: 1, starting_30_days: 1, roles_over_30_days: 0, blocked: 0 } });
    render(<ExecutiveView pod="ISG" {...handlers} />);
    await user.click(await screen.findByRole("button", { name: /Resourcing & onboarding/i }));
    expect(handlers.onOpenResourcing).toHaveBeenCalledWith("ISG");
  });
});
