import {ApiError} from "../../lib/api/client";
import {transport} from "../../lib/transport";
import type {Evaluation} from "./api";
const BASE=(import.meta as {env?:{VITE_API_BASE?:string}}).env?.VITE_API_BASE??"";
export interface Receipt {key:string;jobId?:string}
export interface ScoreOptions {receipt:Receipt;signal?:AbortSignal;onReceipt?:(r:Receipt)=>void;onState?:(s:string)=>void}
interface Status {id:string;status:string;result?:Evaluation;errorCode?:string;errorMessage?:string}
export function newReceipt():Receipt{return {key:crypto.randomUUID()};}
export function storageKey(uid:number,kind:string){return `aruora.evaluation:${uid}:${kind}`;}
export function loadReceipt(key:string):Receipt|null{
 try{const r=JSON.parse(sessionStorage.getItem(key)||"null");return r&&typeof r.key==="string"&&/^[A-Za-z0-9_-]{8,64}$/.test(r.key)&&(!r.jobId||typeof r.jobId==="string")?r:null;}catch{return null;}
}
export function storeReceipt(key:string,r:Receipt|null){try{if(r)sessionStorage.setItem(key,JSON.stringify(r));else sessionStorage.removeItem(key);}catch{/* Recovery is best-effort when browser storage is unavailable. */}}
function resultOf(value:unknown):Evaluation{
 const v=value as Evaluation;
 if(!v||!v.bands||!Number.isInteger(v.savedId))throw new ApiError("INVALID_RESPONSE","Assessment did not return a saved result. Check Progress before starting new work.");
 return v;
}
function delay(ms:number,signal?:AbortSignal){return new Promise<void>((resolve,reject)=>{
 const stop=()=>{clearTimeout(id);signal?.removeEventListener("abort",stop);reject(new ApiError("REQUEST_ABORTED","Stopped checking. Your evaluation continues on the server."));};
 const id=setTimeout(()=>{signal?.removeEventListener("abort",stop);resolve();},ms);
 if(signal?.aborted)stop();else signal?.addEventListener("abort",stop,{once:true});
});}
export async function pollScore(kind:"writing"|"speaking",opts:ScoreOptions):Promise<Evaluation>{
 for(let i=0;i<90;i++){
  const path=opts.receipt.jobId?`/api/jobs/${encodeURIComponent(opts.receipt.jobId)}`:`/api/jobs/lookup?type=score_${kind}&key=${encodeURIComponent(opts.receipt.key)}`;
  const st=await transport<Status>(BASE,path,{signal:opts.signal,timeoutMs:10000},ApiError);
  if(!st||typeof st.id!=="string"||!["queued","running","succeeded","failed","cancelled","expired"].includes(st.status))throw new ApiError("INVALID_RESPONSE","Invalid evaluation status.");
  if(!opts.receipt.jobId){opts.receipt.jobId=st.id;opts.onReceipt?.({...opts.receipt});}
  opts.onState?.(st.status);
  if(st.status==="succeeded")return resultOf(st.result);
  if(["failed","cancelled","expired"].includes(st.status))throw new ApiError(st.errorCode||"EVALUATION_FAILED",st.errorMessage||"Evaluation did not complete. Check Progress before starting a new request.");
  await delay(2000,opts.signal);
 }
 throw new ApiError("JOB_PENDING","Evaluation is still pending. Check the existing request instead of submitting it again.");
}
export async function startScore(kind:"writing"|"speaking",body:unknown,opts:ScoreOptions):Promise<Evaluation>{
 const first=await transport<Evaluation&{queued?:boolean;jobId?:string}>(BASE,`/api/${kind}/evaluate`,{
  method:"POST",body:JSON.stringify(body),headers:{"Idempotency-Key":opts.receipt.key},signal:opts.signal,timeoutMs:15000,
 },ApiError);
 if(!first.queued)return resultOf(first); // Old inline development server compatibility.
 if(typeof first.jobId!=="string")throw new ApiError("INVALID_RESPONSE","Missing evaluation job reference.");
 opts.receipt.jobId=first.jobId;opts.onReceipt?.({...opts.receipt});
 return pollScore(kind,opts);
}
// Legacy callers (e.g. roleplay) keep a stable key for identical retries during
// this page lifetime. The bounded map stores fingerprints, never learner text.
const keys=new Map<string,Receipt>();
export async function legacyScore(kind:"writing"|"speaking",body:unknown){
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(JSON.stringify(body))))).map(b=>b.toString(16).padStart(2,"0")).join("");
 const k=kind+":"+hash;let receipt=keys.get(k);
 if(!receipt){receipt=newReceipt();keys.set(k,receipt);if(keys.size>20)keys.delete(keys.keys().next().value!);}
 const result=await startScore(kind,body,{receipt});keys.delete(k);return result;
}
