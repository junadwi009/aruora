import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Session } from "./Session";
import { ViewProvider } from "../menu/viewContext";
import { api } from "../../lib/api/client";
import type { LessonToday } from "../../lib/types";

const LESSON: LessonToday = {
  day: 1,
  focus: "writing",
  skill: "writing",
  band: "B1",
  lesson: {
    goal: "Use cohesive devices.",
    skill: "writing",
    teach: { explanation: "Connect your ideas.", examples: ["Despite the cost, it helps."] },
    exercises: [
      {
        type: "multiple_choice",
        instruction: "Choose the linker.",
        items: [{ prompt: "___ the cost", answer: "Despite", feedback: "Use Despite + noun." }],
      },
    ],
    produce: { instruction: "Write a paragraph.", prefill: "Some people believe…" },
    review: { collocations: ["strike a balance"], tip: "Link, don't list." },
  },
};

function renderSession() {
  return render(
    <ViewProvider>
      <Session />
    </ViewProvider>
  );
}

beforeEach(() => vi.restoreAllMocks());

describe("Session", () => {
  it("renders the teach stage from today's lesson", async () => {
    vi.spyOn(api, "lessonToday").mockResolvedValue(LESSON);
    renderSession();
    expect(await screen.findByText("Connect your ideas.")).toBeTruthy();
    expect(screen.getByText("Use cohesive devices.")).toBeTruthy();
  });

  it("checks an exercise answer and shows feedback", async () => {
    vi.spyOn(api, "lessonToday").mockResolvedValue(LESSON);
    renderSession();
    // move to Practice stage via the Teach card's Next button (role=button, not the tab)
    fireEvent.click(await screen.findByRole("button", { name: /Practice/ }));
    const input = screen.getByLabelText("Your answer");
    fireEvent.change(input, { target: { value: "wrong" } });
    fireEvent.click(screen.getByText("Check"));
    await waitFor(() => expect(screen.getByText(/Answer: Despite/)).toBeTruthy());
  });

  it("offers a generate CTA when no lesson is cached", async () => {
    vi.spyOn(api, "lessonToday").mockResolvedValue({ ...LESSON, lesson: null });
    renderSession();
    expect(await screen.findByText("Generate today's lesson")).toBeTruthy();
  });
});
