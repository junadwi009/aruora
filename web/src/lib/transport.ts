/** Same-origin transport. Short control-plane deadlines do not inherit the
 * long deadline required by synchronous scoring and audio uploads. */
export type ErrorFactory = new (code:string,message:string,details?:unknown) => Error;
export type TransportOptions = RequestInit & {timeoutMs?: number};
export function requestTimeoutMs(path:string):number {
  const route=path.split("?")[0];
  if (/^\/api\/(auth\/|account\/|health(?:\/|$))/.test(route)) return 10000;
  if (/^\/api\/(writing\/evaluate|speaking\/(evaluate|roleplay|transcribe)|placement\/submit|lesson\/generate|vocab|pronounce\/(sentence|feedback))$/.test(route)) return 180000;
  return 30000;
}
export async function transport<T>(base:string,path:string,opts:TransportOptions,ErrorType:ErrorFactory):Promise<T>{
  const controller=new AbortController();
  const {timeoutMs, ...requestOpts}=opts;
  const signal=opts.signal;
  const abort=()=>controller.abort();
  if(signal?.aborted)controller.abort();
  signal?.addEventListener("abort",abort,{once:true});
  const deadline=typeof timeoutMs==="number"&&Number.isFinite(timeoutMs)&&timeoutMs>0?timeoutMs:requestTimeoutMs(path);
  let timedOut=false;
  const timer=setTimeout(()=>{timedOut=true;controller.abort();},deadline);
  try{
    const headers=new Headers(opts.headers);
    if(opts.body!==undefined && !(opts.body instanceof FormData) && !headers.has("Content-Type"))headers.set("Content-Type","application/json");
    let lang="en";try{lang=localStorage.getItem("ielts.lang")==="id"?"id":"en";}catch{/* storage is optional */}
    headers.set("X-Lang",lang);
    const unsafe=!["GET","HEAD","OPTIONS"].includes((opts.method||"GET").toUpperCase());
    if(unsafe){
      const m=document.cookie.match(/(?:^|;\s*)ar_csrf=([^;]*)/);
      if(m){try{headers.set("X-CSRF-Token",decodeURIComponent(m[1]));}catch{throw new ErrorType("CSRF_REJECTED","Your security token is unreadable. Reload this page and try again.");}}
    }
    const res=await fetch(base+path,{...requestOpts,headers,credentials:"include",signal:controller.signal});
    const text=await res.text();let body:unknown=null;
    try{body=text?JSON.parse(text):null;}catch{throw new ErrorType("INVALID_RESPONSE","The server returned an unreadable response. Try again.");}
    if(!res.ok){
      const err=(body as {error?:{code?:unknown;message?:unknown;details?:unknown;requestId?:unknown}}|null)?.error;
      const code=typeof err?.code==="string"?err.code:"HTTP_ERROR";
      const message=typeof err?.message==="string"?err.message.slice(0,500):"The request could not be completed.";
      const out=new ErrorType(code,message,err?.details);
      Object.assign(out,{status:res.status,requestId:typeof err?.requestId==="string"?err.requestId:undefined,retryAfter:res.headers.get("Retry-After")});
      if(code==="SESSION_EXPIRED")window.dispatchEvent(new CustomEvent("ielts:session-expired"));
      throw out;
    }
    return body as T;
  }catch(e){
    if(e instanceof ErrorType)throw e;
    throw new ErrorType(controller.signal.aborted?"REQUEST_ABORTED":"NETWORK_ERROR",timedOut?"The server took too long to respond. Try again; no successful result has been confirmed.":controller.signal.aborted?"The request was cancelled. Your work remains on this screen.":"Cannot reach the server. Check your connection and retry.");
  }finally{clearTimeout(timer);signal?.removeEventListener("abort",abort);}
}
