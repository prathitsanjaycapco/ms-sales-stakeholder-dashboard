import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const css = readFileSync(new URL("./styles.css", import.meta.url), "utf8");
const desktopReadability = readFileSync(new URL("./desktopReadability.css", import.meta.url), "utf8");
const entry = readFileSync(new URL("./main.jsx", import.meta.url), "utf8");

describe("shared dashboard visual system", () => {
  it("applies the same page palette to every primary view", () => {
    expect(css).toContain(".workspace,.pod-view,.data-management,.executive-weekly-view,.secondary-view");
    expect(css).toContain("--ui-page:");
    expect(css).toContain("--ui-text:");
    expect(css).toContain("--ui-text-strong:");
    expect(css).toContain("--ui-success:");
  });

  it("uses one surface treatment for cards, tables, and settings", () => {
    expect(css).toContain(".pod-card,.weekly-card,.settings-card,.list-table,.coverage-grid>div,.influence-view button,.data-summary,.data-tabs,.data-management-body");
    expect(css).toContain("box-shadow:var(--ui-shadow)");
    expect(css).toContain("--ui-radius-lg:");
    expect(css).toContain("--ui-shadow-raised:");
  });

  it("keeps full-width page headers and responsive spacing consistent", () => {
    expect(css).toContain(".pod-view-head,.data-management-head,.weekly-hero");
    expect(css).toContain("@media(max-width:700px)");
    expect(css).toContain("@media(max-width:1100px)");
    expect(css).toContain("@media(max-width:850px)");
    expect(css).toContain("--ui-topbar:");
  });

  it("defines readable typography and consistent control sizing", () => {
    expect(css).toContain("--ui-font-xs: 10px");
    expect(css).toContain("--ui-font-sm: 11px");
    expect(css).toContain("--ui-control: 36px");
    expect(css).toContain(".pod-card :is(small,em,p),.weekly-card :is(small,em,p,dt)");
  });

  it("adds a balanced wide-desktop type scale after the corrective layers", () => {
    expect(entry.indexOf('import "./desktopReadability.css"')).toBeGreaterThan(entry.indexOf('import "./visualFixes.css"'));
    expect(desktopReadability).toContain("@media (min-width: 1600px)");
    expect(desktopReadability).toContain("--ui-font-xs: 12px");
    expect(desktopReadability).toContain("--ui-font-sm: 13px");
    expect(desktopReadability).toContain("--ui-content: 2048px");
    expect(desktopReadability).not.toMatch(/font-size:\s*[5-9](?:\.\d+)?px/);
  });

  it("normalizes drawers and dialogs", () => {
    expect(css).toContain(".stakeholder-drawer,.pod-detail,.exec-detail-drawer,.weekly-detail-drawer");
  });

  it("provides responsive navigation and contextual map panels", () => {
    expect(css).toContain(".mobile-nav-trigger,.mobile-nav-backdrop,.map-panel-backdrop");
    expect(css).toContain(".top-navigation nav.open");
    expect(css).toContain(".advanced-filter-toggle");
  });

  it("keeps the executive scale in the shared cascade with readable operational text", () => {
    expect(entry).not.toContain("executiveReadable.css");
    expect(css).toContain("Executive and connected entity detail scale");
    const executiveScale = css.slice(css.indexOf("Executive and connected entity detail scale"), css.indexOf("Connected resource demand"));
    expect(executiveScale).not.toMatch(/font-size:\s*[5-9]px/);
  });
});
