// @vitest-environment jsdom
import React from "react";
import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import SearchableSelect, { AdaptiveSelect } from "./SearchableSelect";

const people = [
  { id: "1", name: "Jane Smith", title: "Director" },
  { id: "2", name: "Daniel Kim", title: "Managing Director" },
  { id: "3", name: "Priya Nair", title: "Principal" },
];

describe("SearchableSelect", () => {
  it("filters person fields and selects with the keyboard", async () => {
    const user = userEvent.setup(); const onChange = vi.fn();
    render(<SearchableSelect ariaLabel="Owner" value="" options={people} onChange={onChange} />);
    await user.click(screen.getByRole("button", { name: "Owner" }));
    await user.type(screen.getByRole("combobox"), "i{ArrowDown}{Enter}");
    expect(onChange).toHaveBeenCalledWith("2");
  });

  it("supports searchable multi-selection with removable chips", async () => {
    const user = userEvent.setup(); const onChange = vi.fn();
    render(<SearchableSelect multiple ariaLabel="Attendees" value={["1"]} options={people} onChange={onChange} />);
    await user.click(screen.getByRole("button", { name: "Attendees" }));
    await user.click(screen.getByRole("option", { name: /Priya Nair/i }));
    expect(onChange).toHaveBeenCalledWith(["1", "3"]);
  });

  it("keeps small enums native and upgrades lists at fifty choices", () => {
    const { rerender, container } = render(<AdaptiveSelect value="" options={["One", "Two"]} onChange={() => {}} />);
    expect(container.querySelector("select")).toBeInTheDocument();
    rerender(<AdaptiveSelect ariaLabel="Large list" value="" options={Array.from({ length: 50 }, (_, index) => ({ id: String(index), name: `Option ${index}` }))} onChange={() => {}} />);
    expect(screen.getByRole("button", { name: "Large list" })).toBeInTheDocument();
  });
});
