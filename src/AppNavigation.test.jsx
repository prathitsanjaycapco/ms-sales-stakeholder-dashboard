// @vitest-environment jsdom
import React from "react";
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  getSession: vi.fn(), getMap: vi.fn(), getFilterOptions: vi.fn(),
  getStakeholders: vi.fn(), getEmployees: vi.fn(), getPodMeetingOptions: vi.fn(),
  getOpportunities: vi.fn(), getPodDashboard: vi.fn(),
  getResourcingOverview: vi.fn(), getResourceRequirements: vi.fn(), getCandidates: vi.fn(), getOnboarding: vi.fn(),
  createStakeholder: vi.fn(), getStakeholderProfile: vi.fn(),
}));
vi.mock("./api", () => ({ api }));
vi.mock("./ExecutiveView", () => ({
  default: ({ onOpenMeeting, onOpenOpportunity }) => <div>
    <button onClick={() => onOpenMeeting("meeting-wm", "Wealth Management")}>Open WM meeting</button>
    <button onClick={() => onOpenOpportunity("opportunity-msim", "MSIM")}>Open MSIM opportunity</button>
  </div>,
}));
import App from "./App";

beforeEach(() => {
  localStorage.clear();
  window.history.replaceState({}, "", "/?section=settings&pod=All");
  api.getSession.mockResolvedValue({ subject: "reader", roles: ["Reader"], permissions: { write: false } });
  api.getMap.mockResolvedValue({ pod: "ISG", stakeholders: [], reporting_lines: [], divisions: [], enterprise_functions: [] });
  api.getFilterOptions.mockResolvedValue({});
  api.getStakeholders.mockResolvedValue([]);
  api.getEmployees.mockResolvedValue([]);
  api.getPodMeetingOptions.mockResolvedValue([]);
  api.getOpportunities.mockResolvedValue([]);
  api.getPodDashboard.mockResolvedValue({ view_model: { criticalItems: [] } });
  api.getResourcingOverview.mockResolvedValue({ metrics: {}, funnel: [], critical_items: [], starting_soon: [], open_demand: [], analytics: [] });
  api.getResourceRequirements.mockResolvedValue([]);
  api.getCandidates.mockResolvedValue([]);
  api.getOnboarding.mockResolvedValue([]);
});
afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe("global pod navigation", () => {
  it("renders every canonical stakeholder and keeps reporting context muted for filters", async () => {
    window.history.replaceState({}, "", "/?section=stakeholders&pod=ISG");
    api.getMap.mockResolvedValue({
      pod: "ISG",
      stakeholders: [
        { id: "head", name: "Division Head", title: "Head", pod: "ISG", division: "Front Office", business_unit: "Division Leadership", team_type: "Business", organizational_role: "Division Head", level: "Managing Director", location: "New York", country_code: "US", is_buyer: true, is_influencer: true, is_budget_holder: true, relationship_strength: "Strong", capco_contingents: 1, capco_owner: "Owner", opportunity_count: 0, tags: [] },
        { id: "business", name: "Business Lead", title: "Lead", pod: "ISG", division: "Front Office", business_unit: "Equities", team_type: "Business", organizational_role: "Business Unit Head", manager_id: "head", level: "Managing Director", location: "New York", country_code: "US", is_buyer: true, is_influencer: true, is_budget_holder: false, relationship_strength: "Medium", capco_contingents: 1, capco_owner: "Owner", opportunity_count: 0, tags: [] },
        { id: "tech", name: "Technology Lead", title: "Technology Lead", pod: "ISG", division: "Front Office", business_unit: "Equities", team_type: "Technology", organizational_role: "Primary Technology Stakeholder", is_primary_technology: true, manager_id: "business", level: "Vice President", location: "New York", country_code: "US", is_buyer: false, is_influencer: true, is_budget_holder: false, relationship_strength: "Medium", capco_contingents: 1, capco_owner: "Owner", opportunity_count: 0, tags: [] },
      ],
      reporting_lines: [{ manager_id: "head", report_id: "business" }, { manager_id: "business", report_id: "tech" }], divisions: [], enterprise_functions: [],
    });
    render(<App />);
    await waitFor(() => expect(document.querySelector('[data-stakeholder-id="tech"]')).toBeInTheDocument());
    expect(document.querySelector(".map-completeness")).not.toBeInTheDocument();
    expect(document.querySelectorAll("[data-stakeholder-id]")).toHaveLength(3);
    await userEvent.setup().selectOptions(screen.getByLabelText("Business / Technology"), "Technology");
    expect(document.querySelector('[data-stakeholder-id="tech"]')).not.toHaveClass("muted");
    expect(document.querySelector('[data-stakeholder-id="head"]')).toHaveClass("muted");
  });

  it("refreshes and focuses the canonical map after adding a stakeholder", async () => {
    window.history.replaceState({}, "", "/?section=stakeholders&pod=ISG");
    const person = (id, name, extras = {}) => ({ id, name, title: "Director", pod: "ISG", division: "Front Office", business_unit: "Equities", team_type: "Business", organizational_role: "Business Stakeholder", level: "Director", location: "New York", country_code: "US", is_buyer: false, is_influencer: true, is_budget_holder: false, relationship_strength: "Developing", capco_contingents: 0, opportunity_count: 0, tags: [], ...extras });
    const head = person("head", "Existing Lead", { organizational_role: "Business Unit Head" });
    const added = person("added", "New Report", { manager_id: "head" });
    api.getSession.mockResolvedValue({ subject: "editor", roles: ["Editor"], permissions: { write: true } });
    api.getMap.mockReset();
    api.getMap.mockResolvedValueOnce({ pod: "ISG", stakeholders: [head], reporting_lines: [], divisions: [], enterprise_functions: [] })
      .mockResolvedValueOnce({ pod: "ISG", stakeholders: [head, added], reporting_lines: [{ manager_id: "head", report_id: "added" }], divisions: [], enterprise_functions: [] });
    api.createStakeholder.mockResolvedValue(added);
    api.getStakeholderProfile.mockResolvedValue({ stakeholder: added, team: { manager: head, direct_reports: [] }, meetings: [], notes: [], documents: [], opportunities: [], resourcing: {} });
    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(document.querySelector('[data-stakeholder-id="head"]')).toBeInTheDocument());
    await user.click(screen.getAllByRole("button", { name: "Add person" })[0]);
    const dialog = screen.getByRole("dialog", { name: "Add stakeholder" });
    await user.type(within(dialog).getByLabelText("Full name"), "New Report");
    await user.type(within(dialog).getByLabelText("Title"), "Director");
    await user.click(within(dialog).getByRole("button", { name: "Add person" }));
    await waitFor(() => expect(document.querySelector('[data-stakeholder-id="added"]')).toBeInTheDocument());
    expect(document.querySelector('[data-stakeholder-id="added"]')).toBeInTheDocument();
    expect(api.getMap).toHaveBeenCalledTimes(2);
  });

  it("uses a dismissible primary menu and keeps map chrome out of Settings", async () => {
    const user = userEvent.setup();
    render(<App />);
    expect(screen.queryByRole("button", { name: "Map View" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open control rail" })).not.toBeInTheDocument();
    const menu = screen.getByRole("button", { name: "Open navigation" });
    await user.click(menu);
    expect(menu).toHaveAttribute("aria-expanded", "true");
    await waitFor(() => expect(screen.getByRole("button", { name: "Settings" })).toHaveFocus());
    await user.keyboard("{Escape}");
    expect(menu).toHaveAttribute("aria-expanded", "false");
    expect(menu).toHaveFocus();
    await user.click(menu);
    await user.click(screen.getByRole("button", { name: "Stakeholder Map" }));
    expect(menu).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByRole("button", { name: "Map View" })).toBeInTheDocument();
  });

  it("keeps secondary map filters collapsed until requested", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Stakeholder Map" }));
    expect(screen.queryByLabelText("Buyer / Influencer")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Advanced filters" }));
    expect(screen.getByLabelText("Buyer / Influencer")).toBeInTheDocument();
  });

  it("keeps All selected while switching views and consolidates account records", async () => {
    const user = userEvent.setup();
    render(<App />);
    const podSelect = screen.getByLabelText("Select pod:");
    expect(podSelect).toHaveValue("All");
    await user.click(screen.getByRole("button", { name: "Stakeholder Map" }));
    expect(podSelect).toHaveValue("All");
    expect(screen.getByRole("heading", { name: "Stakeholder Map", level: 1 })).toBeInTheDocument();
    expect(screen.getByText("Reporting structure, relationship coverage, and technology ownership.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Meetings" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Opportunities" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Account Data" }));
    expect(podSelect).toHaveValue("All");
    expect(screen.getByRole("button", { name: "Resourcing & Onboarding" })).toBeInTheDocument();
  });

  it("carries the Executive View record pod into Account Data without legacy section state", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Executive View" }));
    await user.click(screen.getByRole("button", { name: "Open MSIM opportunity" }));
    expect(screen.getByLabelText("Select pod:")).toHaveValue("MSIM");
    expect(screen.getByRole("button", { name: "Account Data" })).toHaveClass("active");
    expect(new URLSearchParams(window.location.search).get("section")).toBe("data");
    expect(new URLSearchParams(window.location.search).get("opportunity")).toBe("opportunity-msim");
  });

  it("lets entity deep links override a conflicting section and opens the matching record tab", async () => {
    window.history.replaceState({}, "", "/?section=executive&pod=Wealth%20Management&meeting=meeting-wm");
    render(<App />);
    expect(screen.getByRole("button", { name: "Account Data" })).toHaveClass("active");
    expect(screen.getByRole("button", { name: "Meetings" })).toHaveClass("active");
    expect(screen.getByLabelText("Select pod:")).toHaveValue("Wealth Management");
  });
});
