// @vitest-environment jsdom
import React from "react";
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AccountEntityDialog } from "./App";

const detail = {
  type: "engagement",
  data: {
    engagement: { id: "project-1", name: "Equities modernization", pod_id: "ISG", division: "Institutional Securities", business_unit: "Equities", health: "AMBER", commercial_value: 2500000, start_date: "2026-01-01", end_date: "2026-12-31", renewal_date: "2026-11-30" },
    team: [{ id: "employee-1", name: "Priya Shah", role: "Delivery Lead", level: "Director", allocation_percent: 80 }],
    stakeholders: [{ id: "stakeholder-1", name: "Emily Davis", title: "Managing Director", relationship_role: "Executive sponsor", is_primary: true }],
    meetings: [{ id: "meeting-1", subject: "Program checkpoint", meeting_date: "2026-08-25" }],
    milestones: [{ id: "milestone-1", title: "Design sign-off", due_date: "2026-09-15", status: "On Track" }],
    revenue: [{ id: "revenue-1", amount: 500000, recognized_on: "2026-08-20" }],
    risks: [{ id: "risk-1", title: "Data readiness", description: "Source remediation is late.", severity: "AMBER", status: "Open", due_date: "2026-09-10" }],
    opportunity: { id: "opportunity-1", name: "Equities expansion", stage: "Proposal", estimated_value: 1000000, probability: 60 },
    resourcing: { requirements: [{ id: "role-1", title: "Data Engineer", status: "OPEN", requested_headcount: 2, target_start_date: "2026-10-01" }], candidates: [], onboarding: [] },
  },
};

afterEach(cleanup);

describe("connected account entity detail", () => {
  it("navigates from a project to people, meetings, opportunities, and resourcing records", async () => {
    const user = userEvent.setup();
    const handlers = { onClose: vi.fn(), onStakeholder: vi.fn(), onEmployee: vi.fn(), onEngagement: vi.fn(), onMeeting: vi.fn(), onOpportunity: vi.fn(), onResourcing: vi.fn() };
    render(<AccountEntityDialog detail={detail} {...handlers} />);

    expect(screen.getByRole("heading", { name: "Equities modernization" })).toBeInTheDocument();
    expect(screen.getByText("$2.5M")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "People" }));
    await user.click(screen.getByRole("button", { name: /Priya Shah/i }));
    expect(handlers.onEmployee).toHaveBeenCalledWith("employee-1");

    await user.click(screen.getByRole("button", { name: "Delivery" }));
    await user.click(screen.getByRole("button", { name: /Program checkpoint/i }));
    expect(handlers.onMeeting).toHaveBeenCalledWith("meeting-1", "ISG");

    await user.click(screen.getByRole("button", { name: "Commercial & staffing" }));
    await user.click(screen.getByRole("button", { name: /Equities expansion/i }));
    expect(handlers.onOpportunity).toHaveBeenCalledWith("opportunity-1", "ISG");
    await user.click(screen.getByRole("button", { name: /Data Engineer/i }));
    expect(handlers.onResourcing).toHaveBeenCalledWith("ISG");
  });
});
