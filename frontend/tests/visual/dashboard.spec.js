import { expect, test } from "@playwright/test";
import { mapResponse, responseFor } from "./fixtures.js";

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
      await expect(page.getByText("Critical roles")).toBeVisible();
      await expect(page.getByText("Readiness matrix")).toBeVisible();
    }
    await expect(page).toHaveScreenshot(`${section}-desktop.png`, { fullPage: false });
  });
}

for (const [section, heading] of routes) {
  test(`${heading} wide desktop readability`, async ({ page }) => {
    await page.setViewportSize({ width: 2560, height: 1440 });
    await page.goto(`/?section=${section}&pod=${podForSection(section)}`, { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: heading, exact: true }).first()).toBeVisible();
    await expectNoPageOverflow(page);

    const renderedMinimum = section === "stakeholders" ? 9.5 : 12;
    const undersizedText = await page.locator("body *").evaluateAll((elements, minimumSize) => elements.flatMap((element) => {
      const style = getComputedStyle(element);
      const hasDirectText = [...element.childNodes].some((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
      if (!hasDirectText || style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) return [];
      const box = element.getBoundingClientRect();
      if (box.width === 0 || box.height === 0) return [];
      const size = Number.parseFloat(style.fontSize);
      let renderedScale = 1;
      for (let node = element; node instanceof Element; node = node.parentElement) {
        const transform = getComputedStyle(node).transform;
        if (transform !== "none") {
          const matrix = new DOMMatrixReadOnly(transform);
          renderedScale *= Math.hypot(matrix.a, matrix.b);
        }
      }
      const renderedSize = size * renderedScale;
      return renderedSize < minimumSize ? [{ element: element.tagName.toLowerCase(), className: element.className, size, renderedSize, minimumSize, text: element.textContent.trim().slice(0, 80) }] : [];
    }), renderedMinimum);

    expect(undersizedText, JSON.stringify(undersizedText, null, 2)).toEqual([]);
    await expect(page).toHaveScreenshot(`${section}-wide-desktop.png`, { fullPage: false });
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

test("stakeholder map renders the full business hierarchy and only primary technology managers", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/?section=stakeholders&pod=ISG", { waitUntil: "networkidle" });
  await expect(page.locator('[data-stakeholder-id="s0"]')).toBeVisible();
  await expect(page.locator(".map-completeness")).toHaveCount(0);
  await expect(page.locator('[data-stakeholder-id="s6"]')).toHaveCount(0);
  await expect(page.locator("[data-stakeholder-id]")).toHaveCount(mapResponse.stakeholders.length - 1);
  await expect(page.locator(".canvas-toolbar span")).toHaveText("80%");
  await page.getByRole("button", { name: "Zoom out" }).click();
  await expect(page.locator(".canvas-toolbar span")).toHaveText("71%");
  await expect(page).toHaveScreenshot("stakeholders-zoomed-out-desktop.png", { fullPage: false });
});

test("pod-head Team drawer remains usable", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/?section=stakeholders&pod=ISG", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Open Dan Simkowitz" }).click();
  await page.getByRole("button", { name: "Team", exact: true }).click();
  await expect(page.getByText("Top of pod hierarchy")).toBeVisible();
  await expect(page.locator(".team-tab .report-list")).toBeVisible();
  await page.getByRole("button", { name: "Collapse stakeholder drawer" }).click();
});

test("stakeholder map keeps nodes clamped, unique, legible, and connector-aligned", async ({ page }) => {
  await page.setViewportSize({ width: 2560, height: 1440 });
  await page.goto("/?section=stakeholders&pod=ISG", { waitUntil: "networkidle" });
  const audit = await page.evaluate(() => {
    const nodes = [...document.querySelectorAll("[data-stakeholder-id]")];
    const ids = nodes.map((node) => node.dataset.stakeholderId);
    const textOverflow = nodes.flatMap((node) => [...node.querySelectorAll(".node-copy strong,.node-copy small")]
      .filter((text) => {
        const textBox = text.getBoundingClientRect();
        const nodeBox = node.getBoundingClientRect();
        return textBox.left < nodeBox.left - 1 || textBox.right > nodeBox.right + 1;
      }).map((text) => text.textContent));
    const fontSizes = nodes.flatMap((node) => [...node.querySelectorAll(".node-copy strong,.node-copy small")]
      .filter((text) => getComputedStyle(text).display !== "none")
      .map((text) => Number.parseFloat(getComputedStyle(text).fontSize)));
    const clamps = nodes.flatMap((node) => [...node.querySelectorAll(".node-copy strong,.node-copy small")]
      .filter((text) => getComputedStyle(text).display !== "none")
      .map((text) => getComputedStyle(text).webkitLineClamp));
    const connectors = [...document.querySelectorAll("[data-division-connector]")];
    const lanes = [...document.querySelectorAll(".division-lane")];
    const alignment = connectors.map((connector, index) => {
      const connectorBox = connector.getBoundingClientRect();
      const laneBox = lanes[index].getBoundingClientRect();
      return Math.abs(connectorBox.left - (laneBox.left + laneBox.width / 2));
    });
    return { ids, textOverflow, fontSizes, clamps, alignment };
  });
  expect(new Set(audit.ids).size).toBe(audit.ids.length);
  expect(audit.textOverflow).toEqual([]);
  expect(Math.min(...audit.fontSizes)).toBeGreaterThanOrEqual(12);
  expect(audit.clamps.every((value) => value === "2")).toBe(true);
  expect(audit.alignment.every((delta) => delta <= 1)).toBe(true);
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

test("candidate scores are prominent and overview cards keep content inset", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/?section=resourcing&pod=All&resourcingTab=Candidates", { waitUntil: "networkidle" });
  const match = page.locator(".res-match").first();
  await expect(match).toBeVisible();
  const matchMetrics = await match.evaluate((node) => ({
    badgeHeight: node.getBoundingClientRect().height,
    labelFontSize: Number.parseFloat(getComputedStyle(node).fontSize),
    scoreFontSize: Number.parseFloat(getComputedStyle(node.querySelector("b")).fontSize),
  }));
  expect(matchMetrics.badgeHeight).toBeGreaterThanOrEqual(28);
  expect(matchMetrics.badgeHeight).toBeLessThanOrEqual(30);
  expect(matchMetrics.labelFontSize).toBeGreaterThanOrEqual(12);
  expect(matchMetrics.scoreFontSize).toBeGreaterThanOrEqual(14);
  expect(matchMetrics.scoreFontSize).toBeLessThanOrEqual(15);
  const stageTypography = await page.locator(".res-kanban").evaluate((kanban) => ({
    header: Number.parseFloat(getComputedStyle(kanban.querySelector("article > header")).fontSize),
    count: Number.parseFloat(getComputedStyle(kanban.querySelector("article > header b")).fontSize),
    name: Number.parseFloat(getComputedStyle(kanban.querySelector("article button p strong")).fontSize),
    detail: Number.parseFloat(getComputedStyle(kanban.querySelector("article button small")).fontSize),
    footer: Number.parseFloat(getComputedStyle(kanban.querySelector("article button footer")).fontSize),
  }));
  expect(stageTypography).toEqual({ header: 12, count: 12, name: 13, detail: 12, footer: 12 });
  await expect(page).toHaveScreenshot("resourcing-candidates-desktop.png", { fullPage: false });

  await page.goto("/?section=resourcing&pod=All&resourcingTab=Overview", { waitUntil: "networkidle" });
  const cardInsets = await page.locator(".res-overview-mini").evaluateAll((cards) => cards.flatMap((card) => {
    const frame = card.getBoundingClientRect();
    return [...card.querySelectorAll(":scope > .overview-mini-summary, :scope > .overview-role-list, :scope > .overview-candidate-stages")].map((content) => {
      const box = content.getBoundingClientRect();
      return { left: box.left - frame.left, right: frame.right - box.right };
    });
  }));
  expect(cardInsets.length).toBeGreaterThanOrEqual(4);
  for (const inset of cardInsets) {
    expect(inset.left).toBeGreaterThanOrEqual(14);
    expect(inset.right).toBeGreaterThanOrEqual(14);
  }
});

test("phone resource requirement modal stays above persistent UI", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/?section=resourcing&pod=All&resourcingTab=Open%20Roles", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "New role" }).click();
  const modal = page.getByRole("dialog", { name: "Create resource requirement" });
  await expect(modal).toBeVisible();
  await expect(modal).toBeInViewport();
  await expectNoPageOverflow(page);
  await expect(page).toHaveScreenshot("resourcing-role-modal-phone.png", { fullPage: false });
});

test("onboarding uses a readable scrollable matrix and responsive records", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/?section=resourcing&pod=All&resourcingTab=Onboarding", { waitUntil: "networkidle" });
  await expect(page.locator(".res-onboarding-table")).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Resource / role" })).toBeVisible();
  const matrix = await page.locator(".res-onboarding-table").evaluate((node) => ({
    overflow: node.scrollWidth - node.clientWidth,
    narrowestHeader: Math.min(...[...node.querySelectorAll("th")].map((header) => header.getBoundingClientRect().width)),
  }));
  expect(matrix.overflow).toBeGreaterThan(100);
  expect(matrix.narrowestHeader).toBeGreaterThanOrEqual(85);
  const stickyColumns = await page.locator(".res-onboarding-table").evaluate((node) => {
    node.scrollLeft = 300;
    const frame = node.getBoundingClientRect();
    const first = node.querySelector("tbody td:first-child").getBoundingClientRect();
    const second = node.querySelector("tbody td:nth-child(2)").getBoundingClientRect();
    return { frameLeft: frame.left, firstLeft: first.left, firstRight: first.right, secondLeft: second.left };
  });
  expect(Math.abs(stickyColumns.firstLeft - stickyColumns.frameLeft)).toBeLessThanOrEqual(2);
  expect(Math.abs(stickyColumns.secondLeft - stickyColumns.firstRight)).toBeLessThanOrEqual(2);
  await page.locator(".res-onboarding-table").evaluate((node) => { node.scrollLeft = 0; });
  await expectNoPageOverflow(page);
  await expect(page).toHaveScreenshot("resourcing-onboarding-desktop.png", { fullPage: false });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator(".res-onboarding-table")).not.toBeVisible();
  await expect(page.locator(".res-onboarding-compact details")).toBeVisible();
  await expectNoPageOverflow(page);
  await expect(page).toHaveScreenshot("resourcing-onboarding-phone.png", { fullPage: false });
});

test("resourcing record workflows keep the next action in context", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/?section=resourcing&pod=ISG&resourcingTab=Open%20Roles", { waitUntil: "networkidle" });
  await page.locator(".res-role-card").first().click();
  await expect(page.getByRole("button", { name: "Add candidate for this role" })).toBeVisible();
  await expect(page).toHaveScreenshot("resourcing-role-workflow-desktop.png", { fullPage: false });
  await page.getByRole("button", { name: "Close" }).click();
  await page.getByRole("button", { name: "Candidates", exact: true }).click();
  await page.locator(".res-kanban article button").first().click();
  await expect(page.getByRole("button", { name: "Advance to Capco Interview" })).toBeVisible();
  await expect(page).toHaveScreenshot("resourcing-candidate-workflow-desktop.png", { fullPage: false });
  await page.getByRole("button", { name: "Edit candidate" }).click();
  await expect(page.getByRole("dialog", { name: "Edit candidate" })).toBeVisible();
  await expect(page.getByLabel("Match score")).toHaveValue("92");
  await expect(page.getByLabel("Skills")).toHaveValue("Python");
  await expect(page).toHaveScreenshot("resourcing-candidate-edit-desktop.png", { fullPage: false });
});

test("master data keeps active and archived records in a separate register", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/?section=data&pod=ISG", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Master data" }).click();
  await expect(page.getByRole("heading", { name: "Account master data" })).toBeVisible();
  await expect(page.getByText("Legacy Cloud Engineer")).toBeVisible();
  await expect(page.getByText("Active role")).toHaveCount(0);
  await expectNoPageOverflow(page);
  await expect(page).toHaveScreenshot("master-data-desktop.png", { fullPage: false });
});

test("phone pod staffing summary scrolls and opens a compact sheet", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/?section=pod&pod=All", { waitUntil: "networkidle" });
  const staffing = page.locator(".pod-staffing-summary");
  await expect(staffing).toBeVisible();
  await expect(staffing.locator(".staffing-summary-metric")).toHaveCount(2);
  expect(await staffing.evaluate((node) => node.parentElement?.classList.contains("pod-scroll"))).toBe(true);
  expect(await page.locator(".pod-view").evaluate((node) => getComputedStyle(node).paddingBottom)).toBe("0px");
  await staffing.click();
  await expect(page.getByRole("dialog", { name: "Staffing overview" })).toBeVisible();
  await expect(page).toHaveScreenshot("pod-staffing-sheet-phone.png", { fullPage: false });
});
