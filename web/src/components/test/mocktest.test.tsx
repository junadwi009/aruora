import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MockTest } from "./MockTest";
import { ViewProvider } from "../menu/viewContext";
import { api } from "../../lib/api/client";
import type { QuizSet } from "../../lib/types";

const SET: QuizSet = {
  title: "T",
  questions: [{ stem: "2+2?", answer: "4", options: ["3", "4"] }],
} as QuizSet;

beforeEach(() => vi.restoreAllMocks());

describe("MockTest", () => {
  it("shows the intro and starts into the listening section", async () => {
    vi.spyOn(api, "practiceSet").mockResolvedValue(SET);
    render(
      <ViewProvider>
        <MockTest />
      </ViewProvider>
    );
    expect(screen.getByText("Listening + Reading mock")).toBeTruthy();
    fireEvent.click(screen.getByText("Start mock"));
    await waitFor(() => expect(screen.getByText(/Section 1 — Listening/)).toBeTruthy());
  });
});
