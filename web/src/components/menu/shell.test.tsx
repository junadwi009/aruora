import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AppShell } from "./AppShell";
import { api } from "../../lib/api/client";

vi.mock("../../lib/api/client", () => ({
  api: {
    skillLevels: vi.fn().mockResolvedValue([{ skill: "reading", band: "C1" }]),
    milestones: vi.fn().mockResolvedValue([]),
    historyReadiness: vi.fn().mockResolvedValue({ method:"test", targetBand:7, currentEstimate:null,
      perSkill: Object.fromEntries(["reading","listening","writing","speaking"].map(s => [s,{estimate:null,target:7,assessed:false}])) }),
    accountMe: vi.fn().mockResolvedValue({ id:1,email:"learner@example.invalid",name:"Learner",goal:"work",targetBand:7 }),
    statsActivity: vi.fn().mockResolvedValue({ current:0,longest:0,today:0,daysActive:0 }),
    tips: vi.fn().mockResolvedValue({ title:"Reading strategy",bullets:["Skim for the main idea."] }),
    practiceSet: vi.fn().mockResolvedValue({title:"Practice",passage:"A sample passage.",questions:[{stem:"A question",options:["A","B"],answer:"A"}]}),
  },
  ApiError: class extends Error {},
}));
const USER={id:1,email:"learner@example.invalid",name:"Learner",goal:"work",targetBand:7};
beforeEach(()=>{vi.clearAllMocks();window.history.replaceState({},"","/app");});

describe("AppShell: authenticated existing learning modules",()=>{
  it("requires an account supplied by the parent boundary",()=>{
    render(<AppShell />);
    expect(screen.getByRole("status")).toHaveTextContent("Account verification required");
    expect(screen.queryByRole("navigation",{name:"Main navigation"})).toBeNull();
    expect(api.historyReadiness).not.toHaveBeenCalled();
  });
  it("shows actual fetched level in the retained Reading screen",async()=>{
    window.history.replaceState({},"","/app/reading");
    render(<AppShell user={USER}/>);
    expect((await screen.findAllByText("C1")).length).toBeGreaterThan(0);
    expect(
	  await screen.findByRole("heading", { name: "Reading practice" })
	).toBeTruthy();
  });
  it("switches from Today to the retained Tips module",async()=>{
    render(<AppShell user={USER}/>);
    fireEvent.click(await screen.findByRole("link",{name:/Learning support/}));
    await waitFor(()=>expect(window.location.pathname).toBe("/app/tips"));
    expect(
	  await screen.findByRole("heading", { name: "A little guidance" })
	).toBeTruthy();
  });
  it("opens a real practice library, not Reading directly",async()=>{
    render(<AppShell user={USER}/>);
    fireEvent.click(screen.getAllByRole("link",{name:/^Practice$/})[0]);
    await waitFor(()=>expect(screen.getByRole("searchbox")).toBeTruthy());
    expect(window.location.pathname).toBe("/app/practice");
  });
});
