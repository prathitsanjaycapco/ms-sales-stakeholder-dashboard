import { expect, test } from "@playwright/test";
import { responseFor } from "./fixtures.js";

const routes = [
  ["executive", "Account Executive View"],
  ["pod", "Morgan Stanley Account Intelligence"],
  ["stakeholders", "Stakeholder Map"],
  ["resourcing", "Resourcing & Onboarding"],
  ["data", "Manage account information"],
  ["settings", "Settings"],
];

const phoneRoutes = routes.filter(([section]) => section !== "stakeholders");
const podForSection = (section) => ["stakeholders", "data"].includes(section) ? "ISG" : "All";

async function expectNoPageOverflow(page) {
  const overflow = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    document: document.documentElement.scrollWidth,
    body: document.body.scrollWidth,
  }));
  expect(overflow.document, JSON.stringify(overflow)).toBeLessThanOrEqual(overflow.viewport + 1);
  expect(overflow.body, JSON.stringify(overflow)).toBeLessThanOrEqual(overflow.viewport + 1);
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    const NativeDate = Date;
    const fixed = new NativeDate("2026-08-31T14:00:00-04:00").valueOf();
    class FixedDate extends NativeDate { constructor(...args) { super(...(args.length ? args : [fixed])); } static now() { return fixed; } }
    FixedDate.parse = NativeDate.parse;
    FixedDate.UTC = NativeDate.UTC;
    window.Date = FixedDate;
  });
  await page.route("**/api/**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(responseFor(route.request().url())) }));
});

for (const [section, heading] of routes) {
  test(`${heading} desktop visual`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(`/?section=${section}&pod=${podForSection(section)}`, { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: heading, exact: true }).first()).toBeVisible();
    if (section === "data") {
      await expect(page.locator(".data-guidance")).toHaveCount(0);
    }
    if (section === "resourcing") {
      await expect(page.getByText("Available after a role is filled")).toBeVisible();
      await expect(page.getByText("Available after a completed start")).toBeVisible();
    }
    await expect(page).toHaveScreenshot(`${section}-desktop.png`, { fullPage: false });
  });
}

test("phone shell and navigation visual", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/?section=executive&pod=All", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "Account Executive View", exact: true })).toBeVisible();
  await expect(page.getByLabel("Select pod:")).toBeInViewport();
  await page.getByRole("button", { name: "Open navigation" }).click();
  await expect(page.getByRole("navigation", { name: "Primary navigation" })).toHaveClass(/open/);
  await expect(page).toHaveScreenshot("phone-navigation.png", { fullPage: false });
});

test("phone map keeps controls within the viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/?section=stakeholders&pod=ISG", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "Stakeholder Map", exact: true })).toBeVisible();
  await expect(page.getByLabel("Select pod:")).toBeInViewport();
  const viewportWidth = await page.evaluate(() => document.documentElement.clientWidth);
  const overflowing = await page.locator(".top-navigation select,.top-navigation>button,.workspace-header button,.workspace-header input,.map-toolbar button").evaluateAll((nodes, width) => nodes.filter((node) => { const box = node.getBoundingClientRect(); return box.left < 0 || box.right > width; }).map((node) => node.outerHTML), viewportWidth);
  expect(overflowing).toEqual([]);
  await expectNoPageOverflow(page);
  await expect(page).toHaveScreenshot("stakeholders-phone.png", { fullPage: false });
});

for (const [section, heading] of phoneRoutes) {
  test(`${heading} phone visual`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`/?section=${section}&pod=${podForSection(section)}`, { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: heading, exact: true }).first()).toBeVisible();
    if (section === "data") await expect(page.locator(".data-guidance")).toHaveCount(0);
    await expectNoPageOverflow(page);
    await expect(page).toHaveScreenshot(`${section}-phone.png`, { fullPage: false });
  });
}

for (const [section, heading] of routes.filter(([name]) => ["pod", "stakeholders", "resourcing", "data"].includes(name))) {
  test(`${heading} tablet visual`, async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(`/?section=${section}&pod=${podForSection(section)}`, { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: heading, exact: true }).first()).toBeVisible();
    if (section === "data") await expect(page.locator(".data-guidance")).toHaveCount(0);
    await expectNoPageOverflow(page);
    await expect(page).toHaveScreenshot(`${section}-tablet.png`, { fullPage: false });
  });
}

test("phone open roles keeps every role metric visible", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/?section=resourcing&pod=All&resourcingTab=Open%20Roles", { waitUntil: "networkidle" });
  const card = page.locator(".res-role-card").first();
  await expect(card).toBeVisible();
  await expect(card.locator(".res-role-stat")).toHaveCount(4);
  for (const stat of await card.locator(".res-role-stat").all()) await expect(stat).toBeVisible();
  await expectNoPageOverflow(page);
  await expect(page).toHaveScreenshot("resourcing-open-roles-phone.png", { fullPage: false });
});

test("phone resource requirement modal stays above persistent UI", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/?section=resourcing&pod=All&resourcingTab=Open%20Roles", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "New role" }).click();
  const modal = page.getByRole("dialog", { name: "Create resource requirement" });
  await expect(modal).toBeVisible();
  await expect(modal).toBeInViewport();
  await expect(page.locator(".account-assistant")).not.toBeVisible();
  await expect(page.locator(".assistant-launcher")).not.toBeVisible();
  await expectNoPageOverflow(page);
  await expect(page).toHaveScreenshot("resourcing-role-modal-phone.png", { fullPage: false });
});

test("phone pod staffing summary scrolls and opens a compact sheet", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/?section=pod&pod=All", { waitUntil: "networkidle" });
  const staffing = page.locator(".pod-staffing-summary");
  await expect(staffing).toBeVisible();
  await expect(staffing.locator(".staffing-summary-metric")).toHaveCount(2);
  expect(await staffing.evaluate((node) => node.parentElement?.classList.contains("pod-scroll"))).toBe(true);
  expect(await page.locator(".pod-view").evaluate((node) => getComputedStyle(node).paddingBottom)).toBe("0px");
  const staffingBox = await staffing.boundingBox();
  const assistantBox = await page.locator(".assistant-launcher").boundingBox();
  expect(staffingBox.x + staffingBox.width).toBeLessThanOrEqual(assistantBox.x);
  await staffing.click();
  await expect(page.getByRole("dialog", { name: "Staffing overview" })).toBeVisible();
  await expect(page.locator(".assistant-launcher")).not.toBeVisible();
  await expect(page).toHaveScreenshot("pod-staffing-sheet-phone.png", { fullPage: false });
});
