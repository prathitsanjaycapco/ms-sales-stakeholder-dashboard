import { expect, test } from "@playwright/test";

test("resourcing lifecycle drills through demand, authoring, candidates, and onboarding", async ({ page }) => {
  await page.goto("/?section=resourcing&pod=ISG");
  await expect(page.getByRole("heading", { name: "Resourcing & Onboarding" })).toBeVisible();
  await expect(page.getByText("Resource pipeline")).toBeVisible();

  await page.getByRole("button", { name: "Open Roles" }).click();
  const role = page.locator(".res-role-card").first();
  await expect(role).toBeVisible();
  await role.click();
  await expect(page.getByRole("dialog", { name: /.+/ })).toBeVisible();
  await page.getByRole("button", { name: "Edit requirement" }).click();
  await expect(page.getByRole("dialog", { name: "Edit resource requirement" })).toBeVisible();
  await page.getByRole("button", { name: "Cancel" }).click();

  await page.getByRole("button", { name: "Candidates", exact: true }).click();
  await page.getByRole("button", { name: /Schedule interview/i }).click();
  await expect(page.getByRole("dialog", { name: "Schedule interview" })).toBeVisible();
  await page.getByRole("button", { name: "Cancel" }).click();

  await page.getByRole("button", { name: "Onboarding", exact: true }).click();
  await page.getByRole("button", { name: /Table view/i }).click();
  await expect(page.getByRole("columnheader", { name: "PT ID Approved" })).toBeVisible();
  await page.locator(".res-onboarding-table tbody tr").first().click();
  await expect(page.getByText("Workflow steps")).toBeVisible();
});
