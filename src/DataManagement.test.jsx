// @vitest-environment jsdom
import React from "react";
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  getStakeholders: vi.fn(), getEmployees: vi.fn(), getPodMeetingOptions: vi.fn(), getOpportunities: vi.fn(), getPodDashboard: vi.fn(),
  createCriticalItem: vi.fn(), updateCriticalItem: vi.fn(),
}));
vi.mock("./api", () => ({ api }));
import DataManagement from "./DataManagement";

afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe("Data Management permissions", () => {
  it("allows record inspection but never submits mutations for a reader", async () => {
    api.getStakeholders.mockResolvedValue([{ id: "s1", name: "Ada Morgan", title: "Managing Director" }]);
    api.getEmployees.mockResolvedValue([{ id: "e1", name: "Priya Shah", role: "Partner" }]);
    api.getPodMeetingOptions.mockResolvedValue([]);
    api.getOpportunities.mockResolvedValue([]);
    api.getPodDashboard.mockResolvedValue({ view_model: { criticalItems: [{ id: "c1", title: "Decision needed", description: "Confirm scope", type: "ACCOUNT", severity: "AMBER", capcoOwner: "Priya Shah", capcoOwnerEmployeeId: "e1", msOwner: "Ada Morgan", due: "2026-09-03", stakeholderId: "s1", tags: [] }] } });
    render(<DataManagement pod="ISG" canWrite={false} />);
    expect(await screen.findByText("Read-only access")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "View" })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "View" }));
    expect(screen.getByDisplayValue("Decision needed")).toBeInTheDocument();
    const submit = screen.getByRole("button", { name: /save critical item/i });
    expect(submit).toBeDisabled();
    fireEvent.submit(submit.closest("form"));
    expect(api.createCriticalItem).not.toHaveBeenCalled();
    expect(api.updateCriticalItem).not.toHaveBeenCalled();
  });
});
