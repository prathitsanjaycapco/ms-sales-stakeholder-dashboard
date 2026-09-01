// @vitest-environment jsdom
import React from "react";
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LiveDrawerSection, SecondaryView, SettingsView } from "./App";
import { DEFAULT_FILTERS } from "./stakeholderViews";

afterEach(cleanup);

const profile = {
  stakeholder: {
    id: "s1", pod: "ISG", name: "Ada Morgan", title: "Managing Director", division: "Institutional Securities",
    business_unit: "Equities", team_type: "Business", location: "New York", level: "Managing Director",
    relationship_strength: "Strong", tags: ["Data"], is_buyer: true, is_influencer: true, is_budget_holder: true,
  },
  team: { manager: null, direct_reports: [], is_primary_technology: false },
  meetings: [], notes: [], documents: [], opportunities: [],
};

describe("dashboard components", () => {
  it("keeps overview meeting dates consistent with canonical meeting history", () => {
    const meetingProfile = {
      ...profile,
      stakeholder: { ...profile.stakeholder, last_meeting: null, next_meeting: null },
      meetings: [
        { id: "past-1", meeting_date: "2020-01-05T14:00:00Z", subject: "Discovery" },
        { id: "past-2", meeting_date: "2021-02-06T14:00:00Z", subject: "Review" },
        { id: "next-1", meeting_date: "2099-03-07T14:00:00Z", subject: "Planning" },
      ],
    };
    render(<LiveDrawerSection tab="Overview" profile={meetingProfile} candidates={[]} editMode={false} canWrite={false} confirmChanges={true} onRefresh={vi.fn()} onChanged={vi.fn()} />);
    expect(screen.getByText("Feb 6, 2021")).toBeInTheDocument();
    expect(screen.getByText("Mar 7, 2099")).toBeInTheDocument();
  });

  it("renders canonical heat-map coverage rather than presentation placeholders", () => {
    render(<SecondaryView type="Heat Map" rows={[]} total={12} pod="ISG" filters={DEFAULT_FILTERS} coverageState={{ status: "ready", data: { divisions: [{ id: "d1", name: "Markets", business_units: [{ id: "u1", name: "Equities", known_stakeholders: 8, total_stakeholders: 10, coverage_score: 82, coverage: "Strong", buyers: 2, budget_holders: 1, open_opportunities: 3 }] }] } }} onRetryCoverage={() => {}} />);
    expect(screen.getByText("Strong · 82%")).toBeInTheDocument();
    expect(screen.getByText("2 buyers · 1 budget holders · 3 opportunities")).toBeInTheDocument();
  });

  it("keeps every stakeholder drawer mutation unavailable to readers", () => {
    const props = { profile, candidates: [], editMode: true, canWrite: false, confirmChanges: true, onRefresh: vi.fn(), onChanged: vi.fn() };
    const { rerender } = render(<LiveDrawerSection {...props} tab="Overview" />);
    expect(screen.queryByRole("button", { name: /edit/i })).not.toBeInTheDocument();
    rerender(<LiveDrawerSection {...props} tab="Meetings" />);
    expect(screen.queryByRole("button", { name: /add/i })).not.toBeInTheDocument();
    rerender(<LiveDrawerSection {...props} tab="Notes" />);
    expect(screen.queryByRole("button", { name: /add|edit|delete/i })).not.toBeInTheDocument();
    rerender(<LiveDrawerSection {...props} tab="Documents" />);
    expect(screen.queryByRole("button", { name: /upload|edit|remove/i })).not.toBeInTheDocument();
    rerender(<LiveDrawerSection {...props} tab="Opportunities" />);
    expect(screen.queryByRole("button", { name: /add/i })).not.toBeInTheDocument();
    rerender(<LiveDrawerSection {...props} tab="Team" />);
    expect(screen.queryByRole("button", { name: /save|make primary/i })).not.toBeInTheDocument();
  });

  it("sends settings changes through the persistent preference interface", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const onReset = vi.fn();
    render(<SettingsView preferences={{ defaultPod: "ISG", compactTooltips: true, confirmChanges: true }} onChange={onChange} onReset={onReset} session={{ subject: "reader", roles: ["Reader"], permissions: { write: false } }} />);
    await user.selectOptions(screen.getByLabelText(/default pod/i), "MSIM");
    await user.click(screen.getByLabelText(/compact hover details/i));
    await user.click(screen.getByRole("button", { name: /reset map preferences/i }));
    expect(onChange).toHaveBeenCalledWith({ defaultPod: "MSIM" });
    expect(onChange).toHaveBeenCalledWith({ compactTooltips: false });
    expect(onReset).toHaveBeenCalledOnce();
  });
});
