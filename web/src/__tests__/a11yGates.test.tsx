/** Automated accessibility regression, not a WCAG conformance certificate.
 * Existing Welcome/Home gates remain. The new Landing and authenticated shell
 * are covered too. Only color-contrast stays disabled in jsdom (no layout).
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, waitFor } from "@testing-library/react";
import axe from "axe-core";
import { JourneyProvider } from "../lib/journey";
import { I18nProvider } from "../lib/i18n";
import { ViewProvider } from "../components/menu/viewContext";
import { Welcome } from "../components/welcome/Welcome";
import { Home } from "../components/menu/Home";
import { AppShell } from "../components/menu/AppShell";
import { LandingView } from "../experience/views";
import type { CefrBand } from "../components/ui/LevelChip";

vi.mock("../lib/api/client",()=>({
  api:{
    skillLevels:vi.fn().mockResolvedValue([{skill:"reading",band:"B2"},{skill:"listening",band:"B1"}]),
    milestones:vi.fn().mockResolvedValue([]),
    accountMe:vi.fn().mockResolvedValue({id:1,email:"learner@example.invalid",name:"A",goal:"work",targetBand:6.5,examDate:null}),
    statsActivity:vi.fn().mockResolvedValue({current:1,longest:1,today:0,daysActive:1}),
    historyReadiness:vi.fn().mockResolvedValue({method:"test",targetBand:6.5,currentEstimate:null,
      perSkill:Object.fromEntries(["reading","listening","writing","speaking"].map(s=>[s,{estimate:null,target:6.5,assessed:false}]))}),
  }, ApiError:class extends Error{},
}));
async function expectNoCriticalViolations(container:HTMLElement){
  const results=await axe.run(container,{rules:{"color-contrast":{enabled:false}}});
  const serious=results.violations.filter(v=>v.impact==="critical"||v.impact==="serious");
  expect(serious.map(v=>`${v.id}: ${v.nodes.length} nodes`)).toEqual([]);
}
describe("WS13 accessibility gates",()=>{
  beforeEach(()=>{vi.clearAllMocks();window.history.replaceState({},"","/");});
  it("retained Welcome has no serious/critical violations",async()=>{
    const {container}=render(<I18nProvider><JourneyProvider><Welcome/></JourneyProvider></I18nProvider>);
    await waitFor(()=>expect(container.querySelector("main, header")).toBeTruthy());
    await expectNoCriticalViolations(container);
  });
  it("retained Home has no serious/critical violations",async()=>{
    const {container}=render(<I18nProvider><JourneyProvider><ViewProvider><Home levels={{reading:"B2",listening:"B1"} as Record<string,CefrBand>}/></ViewProvider></JourneyProvider></I18nProvider>);
    await waitFor(()=>expect(container.textContent).toMatch(/journey/i));
    await expectNoCriticalViolations(container);
  });
  it("authenticated AppShell keeps navigation and main landmarks",async()=>{
    const {container}=render(<AppShell user={{id:1,email:"learner@example.invalid",name:"A",goal:"work",targetBand:6.5}}/>);
    await waitFor(()=>expect(container.querySelector("nav")).toBeTruthy());
    await waitFor(()=>expect(container.querySelector("main")).toBeTruthy());
    await expectNoCriticalViolations(container);
  });
  it("new public landing has no serious/critical violations",async()=>{
    const {container}=render(<LandingView lang="en" nav={()=>{}} onLanguage={()=>{}}/>);
    await expectNoCriticalViolations(container);
  });
});
