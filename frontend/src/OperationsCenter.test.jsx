// @vitest-environment jsdom
import React from "react";
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  getHealthDetails: vi.fn(), getDataTrust: vi.fn(), getReconciliation: vi.fn(),
  getAuditEvents: vi.fn(), getAssistantDocumentIndex: vi.fn(), reindexAssistantDocuments: vi.fn(),
}));
vi.mock("./api", () => ({ api }));
import OperationsCenter from "./OperationsCenter";

beforeEach(() => {
  api.getHealthDetails.mockResolvedValue({ persistent: true });
  api.getDataTrust.mockResolvedValue({ generated_at: "2026-08-31T12:00:00Z", controls: { identity: "trusted_proxy" }, sources: [{ key: "delivery", label: "Delivery portfolio", record_count: 3, externally_sourced_records: 0, manual_records: 3, latest_synced_at: null, latest_updated_at: null, freshness_status: "untracked" }] });
  api.getReconciliation.mockResolvedValue({ status: "passed", total_checks: 4, failed_checks: 0, as_of: "2026-08-31", checks: [] });
  api.getAuditEvents.mockResolvedValue([{ id: "audit-1", action: "PATCH", actor_subject: "admin", entity_type: "task", occurred_at: "2026-08-31T12:00:00Z" }]);
  api.getAssistantDocumentIndex.mockResolvedValue([]);
});
afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe("trust and operations", () => {
  it("does not present untracked delivery data as current", async () => {
    render(<OperationsCenter session={{ roles: ["Viewer"] }} />);
    expect(await screen.findByText("Delivery portfolio")).toBeInTheDocument();
    expect(screen.getByText("Untracked")).toBeInTheDocument();
    expect(screen.getByText((_value, element) => element.tagName === "FOOTER" && element.textContent.includes("synchronization timestamp"))).toBeInTheDocument();
    expect(api.getAuditEvents).not.toHaveBeenCalled();
  });

  it("shows governed audit evidence to account admins", async () => {
    render(<OperationsCenter session={{ roles: ["Account Admin"] }} />);
    expect(await screen.findByText("Recent audit history")).toBeInTheDocument();
    expect(screen.getByText("Patch")).toBeInTheDocument();
    expect(api.getAuditEvents).toHaveBeenCalledWith({ limit: 25 });
  });
});
