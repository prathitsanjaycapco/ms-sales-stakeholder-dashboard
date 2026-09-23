// @vitest-environment jsdom
import React from "react";
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  getResourcingOverview: vi.fn(), getResourceRequirements: vi.fn(), getCandidates: vi.fn(), getOnboarding: vi.fn(),
  getResourcingOptions: vi.fn(), getCandidate: vi.fn(), getResourceRequirement: vi.fn(), getOnboardingRecord: vi.fn(), updateCandidate: vi.fn(), transitionCandidate: vi.fn(), updateOnboardingStep: vi.fn(), createResourceRequirement: vi.fn(), updateResourceRequirement: vi.fn(), createInterview: vi.fn(), updateInterview: vi.fn(), createOffer: vi.fn(), updateOffer: vi.fn(),
  getResourcingTrash: vi.fn(), restoreResourcingItem: vi.fn(), deleteResourceRequirement: vi.fn(), deleteCandidate: vi.fn(), deleteOnboarding: vi.fn(),
}));
vi.mock("./api", () => ({ api }));
import ResourcingView from "./ResourcingView";

const role = { id: "r1", pod_id: "ISG", division: "Front Office", business_unit: "Equities", project_name: "Data Modernization", title: "Senior Data Engineer", role: "Data Engineer", required_skills: ["Python"], priority: "CRITICAL", requested_headcount: 3, filled_headcount: 1, remaining_headcount: 2, candidate_count: 1, target_start_date: "2099-09-20", location: "New York", age_days: 35, owner_name: "Jane Smith", client_name: "Daniel Kim", level: "Principal", status: "SOURCING", sourcing_ready: true, sourcing_state: "CANDIDATE_FOUND", sourcing_next_action: "Candidate pipeline active", bench_checked: true, bench_outcome: "EXISTING_PIPELINE", resourcing_request_submitted: false, resourcing_app_created: true };
const candidate = { id: "c1", name: "Priya Nair", first_name: "Priya", last_name: "Nair", role: "Data Engineer", requirement_title: role.title, project_name: role.project_name, pod_id: "ISG", division: "Front Office", business_unit: "Equities", stage: "RESUME_REVIEW", stage_age_days: 6, match_score: 92, level: "Principal", location: "New York", candidate_type: "EXTERNAL", skills: ["Python"], owner_name: "Jane Smith", ms_owner_name: "Daniel Kim", capco_reviewer_id: "employee-1", ms_reviewer_stakeholder_id: "stakeholder-1", updated_at: "2026-08-20T00:00:00Z", interviews: [], timeline: [{ id: "h1", stage: "RESUME_REVIEW", entered_at: "2026-08-20T00:00:00Z", note: "" }], offer: null, onboarding: null };
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
  api.getResourcingTrash.mockResolvedValue([]); api.restoreResourcingItem.mockResolvedValue({ restored: true }); api.deleteResourceRequirement.mockResolvedValue({ id: role.id, type: "ROLE" }); api.deleteCandidate.mockResolvedValue({ id: candidate.id, type: "CANDIDATE" }); api.deleteOnboarding.mockResolvedValue({ id: board.id, type: "ONBOARDING" });
});
afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe("ResourcingView", () => {
  it("renders critical workflow metrics and drills into open roles", async () => {
    const user = userEvent.setup(); render(<ResourcingView pod="ISG" />);
    expect(await screen.findByText("Critical roles")).toBeInTheDocument();
    expect(screen.getByText("Readiness matrix")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Open Roles/i }));
    expect(await screen.findByText("Senior Data Engineer")).toBeInTheDocument();
    expect(screen.getByText("2 remaining")).toBeInTheDocument();
  });

  it("keeps the overview focused on live workflow work", async () => {
    api.getResourcingOverview.mockResolvedValue({
      ...overview,
      metrics: { ...overview.metrics, avg_time_to_fill: null, avg_onboarding_days: null },
    });
    render(<ResourcingView pod="ISG" />);
    expect(await screen.findByText("Demand needing attention")).toBeInTheDocument();
    expect(screen.getByText("Selection pipeline")).toBeInTheDocument();
    expect(screen.queryByText("Avg time to fill")).not.toBeInTheDocument();
  });

  it("advances a candidate from their profile with the guided next action", async () => {
    const user = userEvent.setup(); api.transitionCandidate.mockResolvedValue({ ...candidate, stage: "CAPCO_INTERVIEW" });
    render(<ResourcingView pod="ISG" canWrite />);
    await user.click(await screen.findByRole("button", { name: "Candidates" }));
    await user.click(await screen.findByRole("button", { name: /Priya Nair/i }));
    await user.click(screen.getByRole("button", { name: "Advance to Capco Interview" }));
    await waitFor(() => expect(api.transitionCandidate).toHaveBeenCalledWith("c1", expect.objectContaining({ action: "ADVANCE" })));
  });

  it("edits candidate profile details from the candidate drawer", async () => {
    const user = userEvent.setup();
    api.updateCandidate.mockResolvedValue({ ...candidate, match_score: 87, skills: ["Python", "AWS"], expected_start_date: "2099-10-01" });
    render(<ResourcingView pod="ISG" canWrite />);
    await user.click(await screen.findByRole("button", { name: "Candidates" }));
    await user.click(await screen.findByRole("button", { name: /Priya Nair/i }));
    await user.click(screen.getByRole("button", { name: "Edit candidate" }));
    expect(screen.getByRole("dialog", { name: "Edit candidate" })).toBeInTheDocument();
    await user.clear(screen.getByLabelText("Match score"));
    await user.type(screen.getByLabelText("Match score"), "87");
    fireEvent.change(screen.getByLabelText("Expected start"), { target: { value: "2099-10-01" } });
    await user.clear(screen.getByLabelText("Skills"));
    await user.type(screen.getByLabelText("Skills"), "Python, AWS");
    await user.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(api.updateCandidate).toHaveBeenCalledWith("c1", expect.objectContaining({ match_score: 87, expected_start_date: "2099-10-01", skills: ["Python", "AWS"] })));
  });

  it("saves interview details without advancing the candidate", async () => {
    const user = userEvent.setup();
    const interviewCandidate = { ...candidate, stage: "MS_INTERVIEW", interviews: [] };
    api.getCandidates.mockResolvedValue([interviewCandidate]); api.getCandidate.mockResolvedValue(interviewCandidate); api.createInterview.mockResolvedValue({ id: "interview-1" });
    render(<ResourcingView pod="ISG" canWrite />);
    await user.click(await screen.findByRole("button", { name: "Candidates" }));
    await user.click(await screen.findByRole("button", { name: /Priya Nair/i }));
    fireEvent.change(screen.getByLabelText("Interview date and time"), { target: { value: "2099-09-15T09:30" } });
    await user.click(screen.getByRole("button", { name: "Save interview details" }));
    await waitFor(() => expect(api.createInterview).toHaveBeenCalledWith("c1", expect.objectContaining({ status: "SCHEDULED" })));
    expect(api.transitionCandidate).not.toHaveBeenCalled();
  });

  it("hands an accepted offer to onboarding and closes the active candidate profile", async () => {
    const user = userEvent.setup();
    const offered = { ...candidate, stage: "OFFER", offer: { offer_status: "OFFER_PENDING", rate_currency: "USD", updated_at: candidate.updated_at } };
    api.getCandidates.mockResolvedValue([offered]);
    api.getCandidate.mockResolvedValue(offered);
    api.updateOffer.mockResolvedValue({ ...offered.offer, offer_status: "OFFER_ACCEPTED" });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<ResourcingView pod="ISG" canWrite canManageCommercial />);
    await user.click(await screen.findByRole("button", { name: "Candidates" }));
    await user.click(await screen.findByRole("button", { name: /Priya Nair/i }));
    await user.click(screen.getByRole("button", { name: "Accept offer & begin onboarding" }));
    await waitFor(() => expect(api.updateOffer).toHaveBeenCalledWith("c1", expect.objectContaining({ offer_status: "OFFER_ACCEPTED" })));
    expect(await screen.findByRole("columnheader", { name: "PT ID Approved" })).toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: "Priya Nair" })).not.toBeInTheDocument();
  });

  it("gates incomplete roles and preselects sourcing-ready roles from the matching queue", async () => {
    const user = userEvent.setup();
    const incomplete = { ...role, id: "r2", title: "Cloud delivery lead", candidate_count: 0, sourcing_ready: false, sourcing_state: "NEEDS_BENCH_CHECK", sourcing_next_action: "Complete the bench check", bench_checked: false, bench_outcome: null };
    api.getResourceRequirements.mockResolvedValue([incomplete, role]);
    render(<ResourcingView pod="ISG" canWrite />);
    await user.click(await screen.findByRole("button", { name: "Open Roles" }));
    const incompleteCard = (await screen.findByText("Cloud delivery lead")).closest("button");
    expect(incompleteCard).toHaveTextContent("Complete the bench check");
    expect(incompleteCard.querySelectorAll(".res-role-stat")).toHaveLength(0);
    await user.click(screen.getByRole("button", { name: "Candidates" }));
    expect(await screen.findByText("Roles needing candidates")).toBeInTheDocument();
    expect(screen.queryByText("Cloud delivery lead")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Senior Data Engineer.*remaining/i }));
    expect(screen.getByRole("dialog", { name: "Add candidate" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Resource requirement" })).toHaveTextContent("Senior Data Engineer");
  });

  it("completes the sourcing handoff inline and preserves the role context", async () => {
    const user = userEvent.setup();
    const incomplete = { ...role, id: "r2", title: "Cloud delivery lead", candidate_count: 0, filled_headcount: 0, sourcing_ready: false, sourcing_state: "NEEDS_BENCH_CHECK", sourcing_next_action: "Complete the bench check", bench_checked: false, bench_outcome: null, candidates: [] };
    const requestNeeded = { ...incomplete, bench_checked: true, bench_outcome: "NO_CANDIDATE", sourcing_state: "NEEDS_RESOURCING_REQUEST", sourcing_next_action: "Confirm the resourcing request", updated_at: "2026-08-21T00:00:00Z" };
    const ready = { ...requestNeeded, resourcing_request_submitted: true, sourcing_ready: true, sourcing_state: "SOURCING_IN_PROGRESS", sourcing_next_action: "Match a sourced candidate", updated_at: "2026-08-22T00:00:00Z" };
    api.getResourceRequirements.mockResolvedValue([incomplete]);
    api.getResourceRequirement.mockResolvedValue(incomplete);
    api.updateResourceRequirement.mockResolvedValueOnce(requestNeeded).mockResolvedValueOnce(ready);
    render(<ResourcingView pod="ISG" canWrite />);
    await user.click(await screen.findByRole("button", { name: "Open Roles" }));
    await user.click(await screen.findByRole("button", { name: /Cloud delivery lead/i }));
    await user.click(screen.getByRole("button", { name: "No bench candidate" }));
    await waitFor(() => expect(api.updateResourceRequirement).toHaveBeenCalledWith("r2", expect.objectContaining({ bench_checked: true, bench_outcome: "NO_CANDIDATE" })));
    await user.click(await screen.findByRole("button", { name: "Confirm request submitted" }));
    await waitFor(() => expect(api.updateResourceRequirement).toHaveBeenLastCalledWith("r2", expect.objectContaining({ resourcing_request_submitted: true })));
    await user.click(await screen.findByRole("button", { name: "Add candidate for this role" }));
    expect(screen.getByRole("dialog", { name: "Add candidate" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Resource requirement" })).toHaveTextContent("Cloud delivery lead");
  });

  it("supports both onboarding pipeline and table views with structured status icons", async () => {
    const user = userEvent.setup(); render(<ResourcingView pod="ISG" />);
    await user.click(await screen.findByRole("button", { name: "Onboarding" }));
    expect((await screen.findAllByText("Profile missing"))[0]).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "PT ID Approved" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "PW Opened" })).toBeInTheDocument();
  });

  it("offers the next onboarding action without editing the full step", async () => {
    const user = userEvent.setup();
    api.updateOnboardingStep.mockResolvedValue({ ...board, blocker: null, next_step: { ...steps[1], status: "IN_PROGRESS" } });
    render(<ResourcingView pod="ISG" canWrite />);
    await user.click(await screen.findByRole("button", { name: "Onboarding" }));
    await user.click(screen.getAllByText("John Lee")[0]);
    await user.click(await screen.findByRole("button", { name: "Resume this step" }));
    await waitFor(() => expect(api.updateOnboardingStep).toHaveBeenCalledWith("o1", "s2", expect.objectContaining({ status: "IN_PROGRESS", blocker_reason: null })));
  });

  it("creates a resource requirement from canonical project and owner options", async () => {
    const user = userEvent.setup(); api.createResourceRequirement.mockResolvedValue({ ...role, id: "r2" });
    render(<ResourcingView pod="ISG" canWrite />);
    await user.click(await screen.findByRole("button", { name: "Open Roles" }));
    await user.click(screen.getByRole("button", { name: /New role/i }));
    await user.type(screen.getByLabelText("Requirement title"), "Cloud delivery lead");
    await user.type(screen.getByLabelText("Role", { selector: "input" }), "Cloud Engineer");
    await user.click(screen.getByRole("checkbox", { name: /created this role in the resourcing app/i }));
    await user.click(screen.getByRole("button", { name: "Create role" }));
    await waitFor(() => expect(api.createResourceRequirement).toHaveBeenCalledWith(expect.objectContaining({ engagement_id: "e1", pod_id: "ISG", division_id: "d1", business_unit_id: "u1", role: "Cloud Engineer", resourcing_app_created: true })));
    expect(screen.getByRole("dialog", { name: "Senior Data Engineer" })).toBeInTheDocument();
  });

  it("archives a role through its profile without exposing Trash in the workflow", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true); vi.spyOn(window, "prompt").mockReturnValue("Duplicate role");
    render(<ResourcingView pod="ISG" canWrite />);
    await user.click(await screen.findByRole("button", { name: "Open Roles" }));
    expect(screen.queryByRole("button", { name: "Trash" })).not.toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: /Senior Data Engineer/i }));
    await user.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(api.deleteResourceRequirement).toHaveBeenCalledWith("r1", "Duplicate role"));
  });
});
