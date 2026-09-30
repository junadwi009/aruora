import {describe,it,expect} from "vitest";
import {Deadline,clockText} from "../../lib/deadline";
describe("v1.2 absolute deadline",()=>{
 it("catches up after a delayed browser callback",()=>{const d=new Deadline(60,0);expect(d.remaining(59000)).toBe(1);expect(d.remaining(90000)).toBe(0);});
 it("emits expiry once",()=>{const d=new Deadline(1,0);expect(d.expireOnce(1000)).toBe(true);expect(d.expireOnce(2000)).toBe(false);});
 it("preserves time on pause and resume",()=>{const d=new Deadline(10,0);d.pause(3000);expect(d.remaining(50000)).toBe(7);d.resume(100000);expect(d.remaining(106000)).toBe(1);});
 it("formats the display without negative time",()=>{expect(clockText(0)).toBe("00:00");expect(clockText(65)).toBe("01:05");});
});
