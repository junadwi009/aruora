/**
 * WS13-01/03/04 — URL deep-link mapping and safe failure-UX mapping.
 */
import { describe, expect, it } from "vitest";
import {
  pathForStep, stepFromPath, pathForView, viewFromPath,
} from "./urlSync";
import { describeApiError, API_ERROR_COPY } from "./apiErrors";
import { ApiError } from "./api/client";

describe("urlSync (deep links)", () => {
  it("maps journey steps to canonical paths and back", () => {
    expect(pathForStep("onboarding")).toBe("/onboarding");
    expect(pathForStep("results")).toBe("/placement/results");
    expect(stepFromPath("/placement/results")).toBe("results");
    expect(stepFromPath("/login")).toBe("login");
    expect(stepFromPath("/nope")).toBeNull();
  });

  it("maps shell views under /app and back", () => {
    expect(pathForView("home")).toBe("/app");
    expect(pathForView("writing")).toBe("/app/writing");
    expect(viewFromPath("/app/writing")).toBe("writing");
    expect(viewFromPath("/app")).toBe("home");
    expect(viewFromPath("/app/unknown-view")).toBeNull();
    expect(viewFromPath("/login")).toBeNull();
  });

  it("trailing slashes and unknown routes never crash mapping", () => {
    expect(stepFromPath("/onboarding/")).toBe("onboarding");
    expect(viewFromPath("/app/settings/")).toBe("settings");
  });
});

describe("describeApiError (failure UX)", () => {
  it("prefers the known-code copy", () => {
    const e = new ApiError("GEN_CAP_REACHED", "server says something");
    expect(describeApiError(e)).toBe(API_ERROR_COPY.GEN_CAP_REACHED);
  });

  it("falls back to the server's safe authored message for unknown codes", () => {
    const e = new ApiError("WORD_LIMIT", "Essay must be at least 250 words.");
    expect(describeApiError(e)).toBe("Essay must be at least 250 words.");
  });

  it("maps network failures offline-safe", () => {
    expect(describeApiError(new TypeError("fetch failed")))
      .toBe(API_ERROR_COPY.NETWORK);
    expect(describeApiError(new ApiError("NETWORK", "offline")))
      .toBe(API_ERROR_COPY.NETWORK);
  });

  it("never leaks unknown internals", () => {
    expect(describeApiError(new Error("stack trace of doom at net.js:1"))).not
      .toContain("net.js");
  });
});
