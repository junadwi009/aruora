import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QuizRunner } from "./QuizRunner";

vi.mock("../../lib/api/client", () => ({
  api: {
    practiceSet: vi.fn().mockResolvedValue({
      title: "Set", passage: "A passage.",
      questions: [{ stem: "Sky color?", options: ["Blue","Green"], answer: "Blue", explanation: "It is blue." }],
    }),
    practiceAttempt: vi.fn().mockResolvedValue({ savedId: 1 }),
  },
  ApiError: class extends Error {},
}));

describe("QuizRunner", () => {
  it("grades a correct answer locally and shows the score", async () => {
    render(<QuizRunner skill="reading" band="B2" mode="reading" />);
    const blue = await screen.findByText("Blue");
    fireEvent.click(blue);                          // select correct option
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));
    await waitFor(() => expect(screen.getByText(/1\s*\/\s*1/)).toBeTruthy());  // score card
  });
});
