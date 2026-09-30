import {ApiError} from "../../lib/api/client";
import {transport} from "../../lib/transport";
const BASE=(import.meta as {env?:{VITE_API_BASE?:string}}).env?.VITE_API_BASE??"";
export type Skill="reading"|"listening";
export interface Question {stem:string;options?:string[]}
export interface Practice {practiceId:string;skill:Skill;difficulty:string;title:string;passage:string;transcript:string;questions:Question[];repeat:boolean;expiresAt:string}
export interface PracticeResult {savedId:number;practiceId:string;skill:Skill;correct:number;total:number;accuracyPct:number;scoringMethod:string;disclaimer:string;review:{index:number;stem:string;submitted:string;correct:boolean;expected:string;explanation:string}[]}
export interface Evaluation {bands:Record<string,number|string>;cefr:string;corrections?:{original:string;fixed:string;note:string}[];rewrite?:string;modelAnswer?:string;feedback?:string;vocabUpgrades?:{from:string;to:string;note?:string}[];metrics?:Record<string,unknown>;savedId?:number;stub?:boolean;estimateScope?:string}
export interface HistoryItem {id:number;type:string;task:string;cefr:string;overall:number|null;createdAt:string;scoreMethod?:string|null;modelProvider?:string|null;accuracyPct?:number|null}
export interface CardData {id:number;front:string;back:string;due:string;reps:number;interval:number}
export interface LessonData {goal:string;skill:string;warmup?:{instruction:string};teach:{explanation:string;examples:string[]};exercises:{type:string;instruction:string;items:{prompt:string;answer:string;distractor?:string;feedback?:string}[]}[];produce:{instruction:string;prefill?:string};review:{tip:string;collocations:string[]}}
export function request<T>(path:string,body?:unknown,method=body===undefined?"GET":"POST",signal?:AbortSignal){return transport<T>(BASE,path,{method,body:body===undefined?undefined:JSON.stringify(body),signal},ApiError);}
export const api12={
 start:(skill:Skill,band="B1",signal?:AbortSignal)=>request<Practice>("/api/practice/start",{skill,band},"POST",signal),
 submit:(practiceId:string,answers:string[])=>request<PracticeResult>("/api/practice/attempt",{practiceId,answers}),
 close:(id:string)=>request<{ok:boolean}>(`/api/practice/session/${encodeURIComponent(id)}`,undefined,"DELETE"),
 writing:(essay:string,prompt:string)=>request<Evaluation>("/api/writing/evaluate",{taskType:"task2",essay,prompt}),
 speaking:(transcript:string,question:string,asrJobId?:string)=>request<Evaluation>("/api/speaking/evaluate",{part:"part2",transcript,question,asrJobId}),
 history:()=>request<HistoryItem[]>("/api/history/attempts"),
 detail:async(id:number)=>{const r=await request<Evaluation&{practiceResult?:PracticeResult;body?:string;scoreMetadata?:{modelProvider?:string}}>(`/api/history/attempt/${id}`);return {...r,stub:r.stub||r.scoreMetadata?.modelProvider==="stub"};},
 roleplay:(scenario:string,history:{role:string;text:string}[],userText:string)=>request<{reply:string}>("/api/speaking/roleplay",{scenario,history,userText}),
};
export async function transcribe(blob:Blob,signal?:AbortSignal):Promise<{transcript:string;jobId?:string}>{
 const form=new FormData();form.append("audio",blob,"speech.webm");
 const first=await transport<{transcript?:string;queued?:boolean;jobId?:string}>(BASE,"/api/speaking/transcribe",{method:"POST",body:form,signal},ApiError);
 if(!first.queued){if(typeof first.transcript!=="string")throw new Error("Invalid transcript response");return {transcript:first.transcript,jobId:first.jobId};}
 const jobId=first.jobId;if(!jobId)throw new Error("Missing transcription job");
 for(let i=0;i<90;i++){
  if(signal?.aborted)throw new Error("Transcription cancelled");
  await new Promise(r=>setTimeout(r,1000));
  const st=await request<{status:string;result?:{transcript?:string};errorMessage?:string}>(`/api/jobs/${encodeURIComponent(jobId)}`,undefined,"GET",signal);
  if(st.status==="succeeded"&&typeof st.result?.transcript==="string")return {transcript:st.result.transcript,jobId};
  if(["failed","expired","cancelled"].includes(st.status))throw new Error(st.errorMessage||"Transcription failed");
 }
 throw new Error("Transcription is taking too long. Retry later or type your response.");
}
