import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Vocab } from "./Vocab";
import { api } from "../../lib/api/client";
import type { VocabSet } from "../../lib/types";

const VSET: VocabSet = {
  topic: "environment",
  words: [{ word: "sustainable", definition: "able to continue", example: "x" }],
};

beforeEach(() => vi.restoreAllMocks());

describe("Vocab", () => {
  it("generates a vocab list in Build mode", async () => {
    vi.spyOn(api, "cardsList").mockResolvedValue({ cards: [], stats: { total: 0, due: 0 } });
    vi.spyOn(api, "vocab").mockResolvedValue(VSET);
    render(<Vocab />);
    fireEvent.click(screen.getByText("Generate"));
    await waitFor(() => expect(screen.getByText("sustainable")).toBeTruthy());
  });

  it("shows the caught-up state in Review when nothing is due", async () => {
    vi.spyOn(api, "cardsList").mockResolvedValue({ cards: [], stats: { total: 0, due: 0 } });
    vi.spyOn(api, "cardsDue").mockResolvedValue([]);
    render(<Vocab />);
    fireEvent.click(screen.getByText(/Review/));
    await waitFor(() => expect(screen.getByText(/All caught up/)).toBeTruthy());
  });
});
