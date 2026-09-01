// @vitest-environment jsdom
import React from "react";
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  getResourcingOverview: vi.fn(), getResourceRequirements: vi.fn(), getCandidates: vi.fn(), getOnboarding: vi.fn(),
  getResourcingOptions: vi.fn(), getCandidate: vi.fn(), getResourceRequirement: vi.fn(), getOnboardingRecord: vi.fn(), updateCandidate: vi.fn(), updateOnboardingStep: vi.fn(), createResourceRequirement: vi.fn(),
}));
vi.mock("./api", () => ({ api }));
import ResourcingView from "./ResourcingView";

const role = { id: "r1", pod_id: "ISG", division: "Front Office", business_unit: "Equities", project_name: "Data Modernization", title: "Senior Data Engineer", role: "Data Engineer", required_skills: ["Python"], priority: "CRITICAL", requested_headcount: 3, filled_headcount: 1, remaining_headcount: 2, candidate_count: 1, target_start_date: "2099-09-20", location: "New York", age_days: 35, owner_name: "Jane Smith", client_name: "Daniel Kim", level: "Principal" };
const candidate = { id: "c1", name: "Priya Nair", first_name: "Priya", last_name: "Nair", role: "Data Engineer", requirement_title: role.title, project_name: role.project_name, pod_id: "ISG", division: "Front Office", business_unit: "Equities", stage: "MS_REVIEW", stage_age_days: 6, match_score: 92, level: "Principal", location: "New York", candidate_type: "EXTERNAL", skills: ["Python"], owner_name: "Jane Smith", ms_owner_name: "Daniel Kim", interviews: [], timeline: [{ id: "h1", stage: "MS_REVIEW", entered_at: "2026-08-20T00:00:00Z", note: "" }], offer: null, onboarding: null };
const steps = [
  { id: "s1", step_order: 1, step_label: "PT ID Approved", responsible_party: "MORGAN_STANLEY", owner_name: "Daniel Kim", status: "COMPLETE", days_blocked: 0 },
  { id: "s2", step_order: 2, step_label: "Profile Worker Opened", responsible_party: "CAPCO", owner_name: "Jane Smith", status: "BLOCKED", blocker_reason: "Profile missing", notes: "Resolve profile", days_blocked: 3 },
];
const board = { id: "o1", candidate_id: "c2", name: "John Lee", pod_id: "ISG", business_unit: "Equities", role: "Data Engineer", project_name: role.project_name, expected_start_date: "2099-09-08", overall_status: "BLOCKED", completed_steps: 1, total_steps: 2, blocked_steps: 1, responsible_party: "CAPCO", owner_name: "Jane Smith", blocker: "Profile missing", risk: "START_AT_RISK", risk_explanation: { remaining_steps: 1, historical_average_remaining_days: 2, days_until_expected_start: 7 }, next_step: steps[1], steps };
const overview = { metrics: { open_demand: 2, critical_roles: 1, candidates: 1, with_ms: 1, offers: 0, pending_offers: 0, onboarding: 1, blocked: 1, starting_30_days: 0, starting_at_risk: 0, avg_time_to_fill: 24, avg_onboarding_days: 16, roles_over_30_days: 1, waiting_on_ms: 0, waiting_on_capco: 1, progressing: 0 }, funnel: [{ stage: "Demand", count: 2 }, { stage: "Sourcing", count: 1 }], critical_items: [], starting_soon: [], open_demand: [{ role: "Data Engineer", count: 2 }], analytics: [{ stage: "MS Review", average_days: 5.8, target_days: 3, waiting: 1, status: "OVER_TARGET" }] };

beforeEach(() => {
  window.history.replaceState({}, "", "/?section=resourcing");
  api.getResourcingOverview.mockResolvedValue(overview); api.getResourceRequirements.mockResolvedValue([role]); api.getCandidates.mockResolvedValue([candidate]); api.getOnboarding.mockResolvedValue([board]);
  api.getResourcingOptions.mockResolvedValue({ engagements: [{ id: "e1", name: role.project_name, pod_id: "ISG", division_id: "d1", business_unit_id: "u1", division: role.division, business_unit: role.business_unit }], employees: [{ id: "employee-1", name: "Jane Smith" }], stakeholders: [{ id: "stakeholder-1", name: "Daniel Kim" }], priorities: ["CRITICAL", "HIGH", "MEDIUM", "LOW"], levels: ["Principal"], locations: ["New York"] });
  api.getCandidate.mockResolvedValue(candidate); api.getResourceRequirement.mockResolvedValue({ ...role, candidates: [candidate] }); api.getOnboardingRecord.mockResolvedValue(board);
});
afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe("ResourcingView", () => {
  it("renders calculated lifecycle metrics and drills into open demand", async () => {
    const user = userEvent.setup(); render(<ResourcingView pod="ISG" />);
    expect(await screen.findByText("Open demand")).toBeInTheDocument();
    expect(screen.getByText("24 days")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Open Roles/i }));
    expect(await screen.findByText("Senior Data Engineer")).toBeInTheDocument();
    expect(screen.getByText("2 remaining")).toBeInTheDocument();
  });

  it("explains unavailable duration metrics instead of rendering empty units", async () => {
    api.getResourcingOverview.mockResolvedValue({
      ...overview,
      metrics: { ...overview.metrics, avg_time_to_fill: null, avg_onboarding_days: null },
    });
    render(<ResourcingView pod="ISG" />);
    expect(await screen.findByText("Available after a role is filled")).toBeInTheDocument();
    expect(screen.getByText("Available after a completed start")).toBeInTheDocument();
    expect(screen.getAllByText("—")).toHaveLength(2);
    expect(screen.queryByText(/^days$/i)).not.toBeInTheDocument();
  });

  it("requires an explicit save and confirmation for candidate stage changes", async () => {
    const user = userEvent.setup(); vi.spyOn(window, "confirm").mockReturnValue(true);
    api.updateCandidate.mockResolvedValue({ ...candidate, stage: "INTERVIEWING" });
    render(<ResourcingView pod="ISG" canWrite />);
    await user.click(await screen.findByRole("button", { name: "Candidates" }));
    await user.click(await screen.findByRole("button", { name: /Priya Nair/i }));
    await user.selectOptions(await screen.findByLabelText("Current stage"), "INTERVIEWING");
    expect(api.updateCandidate).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Save stage" }));
    await waitFor(() => expect(api.updateCandidate).toHaveBeenCalledWith("c1", expect.objectContaining({ stage: "INTERVIEWING" })));
  });

  it("supports both onboarding pipeline and table views with structured status icons", async () => {
    const user = userEvent.setup(); render(<ResourcingView pod="ISG" />);
    await user.click(await screen.findByRole("button", { name: "Onboarding" }));
    expect(await screen.findByText("Profile missing")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Table view/i }));
    expect(screen.getByRole("columnheader", { name: "PT ID Approved" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "PW Opened" })).toBeInTheDocument();
  });

  it("creates a resource requirement from canonical project and owner options", async () => {
    const user = userEvent.setup(); api.createResourceRequirement.mockResolvedValue({ ...role, id: "r2" });
    render(<ResourcingView pod="ISG" canWrite />);
    await user.click(await screen.findByRole("button", { name: "Open Roles" }));
    await user.click(screen.getByRole("button", { name: /New role/i }));
    await user.type(screen.getByLabelText("Requirement title"), "Cloud delivery lead");
    await user.type(screen.getByLabelText("Role", { selector: "input" }), "Cloud Engineer");
    await user.click(screen.getByRole("button", { name: "Create role" }));
    await waitFor(() => expect(api.createResourceRequirement).toHaveBeenCalledWith(expect.objectContaining({ engagement_id: "e1", pod_id: "ISG", division_id: "d1", business_unit_id: "u1", role: "Cloud Engineer" })));
  });
});
