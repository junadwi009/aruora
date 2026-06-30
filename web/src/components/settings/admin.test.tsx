import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AdminSection } from "./AdminSection";
import { Settings } from "./Settings";
import { api } from "../../lib/api/client";
import type { AdminUser, AdminStats, AccountUser } from "../../lib/types";

const USERS: AdminUser[] = [
  { id: 1, email: "boss@x.com", name: "Boss", targetBand: 7, attempts: 3 },
  { id: 2, email: "alice@x.com", name: "Alice", targetBand: 6, attempts: 1 },
];
const STATS: AdminStats = {
  totalAccounts: 2, totalProfiles: 3, anonymousProfiles: 1,
  totalAttempts: 4, totalMocks: 0, totalCards: 5,
};

beforeEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("AdminSection", () => {
  it("lists accounts, shows the self badge, and hides self-delete", async () => {
    vi.spyOn(api, "adminUsers").mockResolvedValue(USERS);
    vi.spyOn(api, "adminStats").mockResolvedValue(STATS);
    render(<AdminSection selfId={1} />);

    expect(await screen.findByText("boss@x.com")).toBeTruthy();
    expect(screen.getByText("alice@x.com")).toBeTruthy();
    // self (id 1) gets no delete button; alice (id 2) does
    expect(screen.queryByRole("button", { name: /delete user — boss@x.com/i })).toBeNull();
    expect(screen.getByRole("button", { name: /delete user — alice@x.com/i })).toBeTruthy();
  });

  it("deletes a user after confirm and reloads", async () => {
    vi.spyOn(api, "adminUsers").mockResolvedValue(USERS);
    vi.spyOn(api, "adminStats").mockResolvedValue(STATS);
    const del = vi.spyOn(api, "adminDeleteUser").mockResolvedValue({ ok: true });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<AdminSection selfId={1} />);

    fireEvent.click(await screen.findByRole("button", { name: /delete user — alice@x.com/i }));
    await waitFor(() => expect(del).toHaveBeenCalledWith(2));
  });

  it("sends a reset link", async () => {
    vi.spyOn(api, "adminUsers").mockResolvedValue(USERS);
    vi.spyOn(api, "adminStats").mockResolvedValue(STATS);
    const reset = vi.spyOn(api, "adminResetUser").mockResolvedValue({ ok: true });
    render(<AdminSection selfId={1} />);

    fireEvent.click(await screen.findByRole("button", { name: /send reset link — alice@x.com/i }));
    await waitFor(() => expect(reset).toHaveBeenCalledWith(2));
  });
});

describe("Settings admin gating", () => {
  const base: AccountUser = { id: 1, email: "boss@x.com", name: "Boss", goal: "other", targetBand: 7 };

  it("renders the admin panel only for admins", async () => {
    vi.spyOn(api, "milestones").mockResolvedValue([]);
    vi.spyOn(api, "adminUsers").mockResolvedValue(USERS);
    vi.spyOn(api, "adminStats").mockResolvedValue(STATS);
    vi.spyOn(api, "accountMe").mockResolvedValue({ ...base, isAdmin: true });
    render(<Settings />);
    expect(await screen.findByText(/master admin/i)).toBeTruthy();
  });

  it("hides the admin panel for non-admins", async () => {
    vi.spyOn(api, "milestones").mockResolvedValue([]);
    vi.spyOn(api, "accountMe").mockResolvedValue({ ...base, isAdmin: false });
    render(<Settings />);
    // let the effect resolve
    await screen.findByText(/settings/i);
    expect(screen.queryByText(/master admin/i)).toBeNull();
  });
});
