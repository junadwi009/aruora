import {afterEach,describe,expect,it,vi} from "vitest";
import {transport,requestTimeoutMs} from "./transport";

class TestError extends Error {
  constructor(public code:string,message:string,public details?:unknown){super(message);}
}
afterEach(()=>{vi.useRealTimers();vi.unstubAllGlobals();document.cookie="ar_csrf=; Max-Age=0; path=/";});
describe("bounded transport",()=>{
  it("keeps authentication deadlines separate from scoring",()=>{
    expect(requestTimeoutMs("/api/auth/status")).toBe(10000);
    expect(requestTimeoutMs("/api/account/me?refresh=1")).toBe(10000);
    expect(requestTimeoutMs("/api/writing/evaluate")).toBe(180000);
    expect(requestTimeoutMs("/api/jobs/job-id")).toBe(30000);
  });
  it("aborts a stalled bootstrap request and clears its timer",async()=>{
    vi.useFakeTimers();
    vi.stubGlobal("fetch",vi.fn((_url:unknown,opts:RequestInit)=>new Promise((_resolve,reject)=>{
      opts.signal?.addEventListener("abort",()=>reject(new DOMException("Aborted","AbortError")),{once:true});
    })));
    const result=transport("","/api/auth/status",{},TestError);
    const checked=expect(result).rejects.toMatchObject({code:"REQUEST_ABORTED"});
    await vi.advanceTimersByTimeAsync(10000);
    await checked;
    expect(vi.getTimerCount()).toBe(0);
  });
  it("honors caller cancellation without dropping cookies or custom headers",async()=>{
    document.cookie="ar_csrf=regression-token; path=/";
    const fetcher=vi.fn(async()=>new Response(JSON.stringify({ok:true}),{status:200}));
    vi.stubGlobal("fetch",fetcher);
    const controller=new AbortController();
    await transport("","/api/account/logout",{method:"POST",body:"{}",headers:{"X-Request-ID":"synthetic"},signal:controller.signal},TestError);
    const opts=(fetcher.mock.calls as unknown as [string,RequestInit][])[0][1];
    expect(opts.credentials).toBe("include");
    expect(new Headers(opts.headers).get("X-CSRF-Token")).toBe("regression-token");
    expect(new Headers(opts.headers).get("X-Request-ID")).toBe("synthetic");
    expect(opts.signal).toBeInstanceOf(AbortSignal);
  });
  it("preserves 429 and retry metadata even for a legacy error code",async()=>{
    vi.stubGlobal("fetch",vi.fn(async()=>new Response(JSON.stringify({error:{code:"UNAUTHORIZED",message:"Try later",details:{retryAfter:42}}}),{status:429,headers:{"Retry-After":"42"}})));
    await expect(transport("","/api/account/login",{method:"POST",body:"{}"},TestError)).rejects.toMatchObject({code:"UNAUTHORIZED",status:429,retryAfter:"42",details:{retryAfter:42}});
  });
  it("does not render an HTML error page as an account error",async()=>{
    vi.stubGlobal("fetch",vi.fn(async()=>new Response("<h1>private proxy detail</h1>",{status:502})));
    await expect(transport("","/api/account/me",{},TestError)).rejects.toMatchObject({code:"INVALID_RESPONSE"});
  });
});
