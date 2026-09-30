import {describe,it,expect,vi} from "vitest";
import {render,screen,fireEvent} from "@testing-library/react";
import {LandingView,PracticeView,SkillEvidenceGrid} from "../views";
import {SKILLS,parseReadiness} from "../model";
describe("ARUORA experience views",()=>{
 it("uses the approved wordmark and a real login route",()=>{const nav=vi.fn();render(<LandingView lang="en" nav={nav} onLanguage={()=>{}}/>);expect(screen.getAllByAltText("ARUORA").length).toBeGreaterThan(0);fireEvent.click(screen.getAllByRole("link",{name:/^Log in$/})[0]);expect(nav).toHaveBeenCalledWith("/login");});
 it("offers a real practice hub rather than redirecting practice to reading",()=>{render(<PracticeView lang="en" nav={()=>{}} query="writing" onQuery={()=>{}}/>);expect(screen.getByRole("heading",{name:/^Writing$/})).toBeTruthy();expect(screen.queryByRole("heading",{name:/^Listening$/})).toBeNull();});
 it("shows separate skill gaps",()=>{const r=parseReadiness({method:"test",targetBand:7,currentEstimate:6,perSkill:Object.fromEntries(SKILLS.map(skill=>[skill,{estimate:skill==="writing"?5.5:6.5,target:7,assessed:true}]))});render(<SkillEvidenceGrid r={r} lang="en" nav={()=>{}}/>);expect(screen.getByText("1.5 band to target")).toBeTruthy();expect(screen.getAllByText("0.5 band to target")).toHaveLength(3);});
});
