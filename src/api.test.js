import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("API error responses", () => {
  it("surfaces a plain-text failure without reading the response twice", async () => {
    const response = new Response("Stakeholder database connection failed", {
      status: 503,
      headers: { "Content-Type": "text/plain" },
    });
    const textSpy = vi.spyOn(response, "text");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));

    await expect(api.getMap("ISG")).rejects.toMatchObject({
      message: "Stakeholder database connection failed",
      status: 503,
    });
    expect(textSpy).toHaveBeenCalledTimes(1);
  });

  it("extracts FastAPI validation details from the cached response body", async () => {
    const response = new Response(JSON.stringify({
      detail: [{ msg: "Manager is required" }, { msg: "Manager must be in the same pod" }],
    }), { status: 422, headers: { "Content-Type": "application/json" } });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));

    await expect(api.getMap("ISG")).rejects.toMatchObject({
      message: "Manager is required; Manager must be in the same pod",
      status: 422,
    });
  });
});
