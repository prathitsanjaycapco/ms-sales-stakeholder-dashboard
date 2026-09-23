import { expect, test } from "@playwright/test";

test("stakeholder map opens zoomed out and reset restores the default", async ({ page }) => {
  await page.goto("/?section=stakeholders&pod=ISG", { waitUntil: "networkidle" });
  const zoom = page.locator(".canvas-toolbar span");
  await expect(zoom).toHaveText("80%");

  await page.getByRole("button", { name: "Zoom in" }).click();
  await expect(zoom).toHaveText("90%");
  await page.getByTitle("Reset view").click();
  await expect(zoom).toHaveText("80%");
});

test("pod meeting details are viewport-bound, scrollable, and keyboard-dismissible", async ({ page, request }) => {
  const dashboard = await request.get("/api/pods/ISG/dashboard");
  expect(dashboard.ok()).toBeTruthy();
  const [meeting] = (await dashboard.json()).view_model.meetings;
  expect(meeting).toBeTruthy();

  await page.goto(`/?section=pod&pod=ISG&meeting=${encodeURIComponent(meeting.meetingId || meeting.id)}`, { waitUntil: "networkidle" });
  const drawer = page.getByRole("dialog", { name: /meeting intelligence$/i });
  await expect(drawer).toBeVisible();
  await expect(drawer.getByRole("button", { name: "Close" })).toBeFocused();

  const geometry = await drawer.evaluate((node) => {
    const box = node.getBoundingClientRect();
    const style = getComputedStyle(node);
    return { bottom: box.bottom, height: box.height, overflowY: style.overflowY, viewport: window.innerHeight };
  });
  expect(geometry.overflowY).toBe("scroll");
  expect(geometry.bottom).toBeLessThanOrEqual(geometry.viewport + 1);
  expect(geometry.height).toBeGreaterThan(200);

  await page.keyboard.press("Escape");
  await expect(drawer).toBeHidden();
});
