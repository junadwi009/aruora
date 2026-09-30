import {describe,it,expect} from "vitest";
import {SKILLS,parseReadiness,recommend,type DashboardData} from "../model";
import {stepFromPath,safeAppReturn} from "../../lib/urlSync";
const evidence=()=>({method:"test",targetBand:7,currentEstimate:6,perSkill:Object.fromEntries(SKILLS.map(skill=>[skill,{estimate:skill==="writing"?5.5:6.5,target:7,assessed:true}]))});
describe("ARUORA product experience",()=>{
 it("preserves nested app routes and rejects external redirects",()=>{expect(stepFromPath("/app/writing")).toBe("app");expect(safeAppReturn("//evil.invalid")).toBe("/app");});
 it("computes actual per-skill gaps without percentages",()=>{const r=parseReadiness(evidence());expect(r.perSkill.writing.gap).toBe(1.5);expect(r.perSkill.reading.gap).toBe(.5);expect(r).not.toHaveProperty("percentage");});
 it("recommends by positive gap",()=>{const d:DashboardData={profile:{id:1,name:"Test",goal:"work",targetBand:7},readiness:parseReadiness(evidence()),readinessState:"ready",milestones:[],milestonesState:"ready",activity:null,activityState:"ready"};expect(recommend(d).skill).toBe("writing");});
 it("does not substitute an empty state for an API error",()=>{expect(()=>parseReadiness({})).toThrow();});
});
