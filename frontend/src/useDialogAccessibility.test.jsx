// @vitest-environment jsdom
import React, { useRef, useState } from "react";
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { useDialogAccessibility } from "./useDialogAccessibility";

afterEach(cleanup);

function Harness() {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useDialogAccessibility(ref, () => setOpen(false), open);
  return <><button onClick={() => setOpen(true)}>Open dialog</button>{open && <section ref={ref} role="dialog"><button data-dialog-initial-focus>First</button><button>Last</button></section>}</>;
}

describe("dialog accessibility", () => {
  it("moves focus in, traps tabbing, closes on Escape, and restores focus", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const opener = screen.getByRole("button", { name: "Open dialog" });
    await user.click(opener);
    await waitFor(() => expect(screen.getByRole("button", { name: "First" })).toHaveFocus());
    await user.tab({ shift: true });
    expect(screen.getByRole("button", { name: "Last" })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });
});
