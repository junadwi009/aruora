import {afterEach,beforeEach,describe,it,expect,vi} from "vitest";
import {startScore,pollScore,loadReceipt,storeReceipt,storageKey} from "./scoring";

const result={savedId:42,bands:{overall:6},cefr:"B2",stub:true};
const json=(body:unknown,status=200)=>new Response(JSON.stringify(body),{status,headers:{"Content-Type":"application/json"}});
beforeEach(()=>sessionStorage.clear());
afterEach(()=>{vi.unstubAllGlobals();vi.useRealTimers();});

describe("queued evaluations",()=>{
 it("submits one keyed request then consumes the existing saved result",async()=>{
  const fetcher=vi.fn().mockResolvedValueOnce(json({queued:true,jobId:"job-1"},202)).mockResolvedValueOnce(json({id:"job-1",status:"succeeded",result}));
  vi.stubGlobal("fetch",fetcher);
  const receipt={key:"request-0001"};
  expect(await startScore("writing",{essay:"synthetic"},{receipt})).toEqual(result);
  expect(fetcher).toHaveBeenCalledTimes(2);
  expect((fetcher.mock.calls[0][1].headers as Headers).get("Idempotency-Key")).toBe("request-0001");
  expect(fetcher.mock.calls[1][1].method).toBeUndefined();
 });
 it("recovers an unknown job id via owner-scoped lookup without a second POST",async()=>{
  const fetcher=vi.fn().mockResolvedValue(json({id:"job-1",status:"succeeded",result}));
  vi.stubGlobal("fetch",fetcher);
  expect(await pollScore("speaking",{receipt:{key:"request-0002"}})).toEqual(result);
  expect(fetcher.mock.calls[0][0]).toContain("/api/jobs/lookup?type=score_speaking");
  expect(fetcher.mock.calls[0][1].method).toBeUndefined();
 });
 it("does not silently create new work after terminal failure",async()=>{
  const fetcher=vi.fn().mockResolvedValue(json({id:"job-1",status:"failed",errorCode:"JOB_OUTCOME_UNCERTAIN",errorMessage:"Check Progress"}));
  vi.stubGlobal("fetch",fetcher);
  await expect(pollScore("writing",{receipt:{key:"request-0003",jobId:"job-1"}})).rejects.toMatchObject({code:"JOB_OUTCOME_UNCERTAIN"});
  expect(fetcher).toHaveBeenCalledTimes(1);
 });
 it("keeps a request key after a network failure for later lookup",async()=>{
  vi.stubGlobal("fetch",vi.fn().mockRejectedValue(new TypeError("network")));
  const receipt={key:"request-0004"};
  await expect(startScore("writing",{essay:"synthetic"},{receipt})).rejects.toMatchObject({code:"NETWORK_ERROR"});
  expect(receipt.key).toBe("request-0004");
 });
 it("isolates stored receipts by account and skill and stores no draft",()=>{
  storeReceipt(storageKey(1,"writing"),{key:"request-0005",jobId:"job-1"});
  expect(loadReceipt(storageKey(2,"writing"))).toBeNull();
  expect(loadReceipt(storageKey(1,"speaking"))).toBeNull();
  expect(JSON.parse(sessionStorage.getItem(storageKey(1,"writing"))!)).toEqual({key:"request-0005",jobId:"job-1"});
 });
 it("rejects success without a saved result",async()=>{
  vi.stubGlobal("fetch",vi.fn().mockResolvedValue(json({id:"job-1",status:"succeeded",result:{bands:{overall:6}}})));
  await expect(pollScore("writing",{receipt:{key:"request-0006",jobId:"job-1"}})).rejects.toMatchObject({code:"INVALID_RESPONSE"});
 });
});
