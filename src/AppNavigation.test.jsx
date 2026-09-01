// @vitest-environment jsdom
import React from "react";
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  getSession: vi.fn(), getMap: vi.fn(), getFilterOptions: vi.fn(),
  getStakeholders: vi.fn(), getEmployees: vi.fn(), getPodMeetingOptions: vi.fn(),
  getOpportunities: vi.fn(), getPodDashboard: vi.fn(),
  getResourcingOverview: vi.fn(), getResourceRequirements: vi.fn(), getCandidates: vi.fn(), getOnboarding: vi.fn(),
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
