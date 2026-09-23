import { expect, test } from "@playwright/test";

test("resourcing lifecycle drills through demand, authoring, candidates, and onboarding", async ({ page }) => {
  await page.goto("/?section=resourcing&pod=ISG");
  await expect(page.getByRole("heading", { name: "Resourcing & Onboarding" })).toBeVisible();
  await expect(page.getByText("Demand needing attention")).toBeVisible();
  await expect(page.getByText("Readiness matrix")).toBeVisible();

  await page.getByRole("button", { name: "Open Roles" }).click();
  await page.getByRole("button", { name: "New role" }).click();
  await page.getByLabel("Requirement title").fill("Workflow validation role");
  await page.getByLabel("Role", { exact: true }).fill("Workflow Analyst");
  await page.getByRole("checkbox", { name: /created this role in the resourcing app/i }).check();
  await page.getByRole("button", { name: "Create role" }).click();
  await expect(page.getByRole("dialog", { name: "Workflow validation role" })).toBeVisible();
  await page.getByRole("button", { name: "No bench candidate" }).click();
  await page.getByRole("button", { name: "Confirm request submitted" }).click();
  await page.getByRole("button", { name: "Add candidate for this role" }).click();
  await expect(page.getByRole("button", { name: "Resource requirement" })).toContainText("Workflow validation role");
  await page.getByRole("button", { name: "Cancel" }).click();
  await page.getByRole("button", { name: "Open Roles" }).click();

  const role = page.locator(".res-role-card").first();
  await expect(role).toBeVisible();
  await role.click();
  await expect(page.getByRole("dialog", { name: /.+/ })).toBeVisible();
  await page.getByRole("button", { name: "Edit requirement" }).click();
  await expect(page.getByRole("dialog", { name: "Edit resource requirement" })).toBeVisible();
  await page.getByRole("button", { name: "Cancel" }).click();

  await page.getByRole("button", { name: "Candidates", exact: true }).click();
  await expect(page.getByText("Roles needing candidates")).toBeVisible();
  await page.locator(".res-kanban article button").first().click();
  await expect(page.locator(".res-candidate-stepper")).toBeVisible();
  await expect(page.locator(".res-guided-action")).toBeVisible();
  await page.getByRole("button", { name: "Close" }).click();

  await page.getByRole("button", { name: "Onboarding", exact: true }).click();
  await expect(page.getByRole("columnheader", { name: "PT ID Approved" })).toBeVisible();
  await page.locator(".res-onboarding-table tbody tr").first().click();
  await expect(page.getByText("Workflow steps")).toBeVisible();
});
