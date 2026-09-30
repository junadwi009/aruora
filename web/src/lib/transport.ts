/** Bounded transport shared by legacy and v1.2 clients.
 * Headers are merged AFTER request options; custom headers cannot drop CSRF.
 * JSON/HTML error pages never get rendered as raw server payloads.
 */
export type ErrorFactory = new (code:string,message:string,details?:unknown) => Error;
export async function transport<T>(base:string,path:string,opts:RequestInit,ErrorType:ErrorFactory):Promise<T>{
  const controller=new AbortController();
  const signal=opts.signal;
  const abort=()=>controller.abort();
  if(signal?.aborted)controller.abort();
  signal?.addEventListener("abort",abort,{once:true});
  const timer=setTimeout(abort,180000);
  try{
    const headers=new Headers(opts.headers);
    if(opts.body!==undefined && !(opts.body instanceof FormData) && !headers.has("Content-Type"))headers.set("Content-Type","application/json");
    let lang="en";try{lang=localStorage.getItem("ielts.lang")==="id"?"id":"en";}catch{/* storage is optional */}
    headers.set("X-Lang",lang);
    const unsafe=!["GET","HEAD","OPTIONS"].includes((opts.method||"GET").toUpperCase());
    if(unsafe){const m=document.cookie.match(/(?:^|;\s*)ar_csrf=([^;]*)/);if(m)headers.set("X-CSRF-Token",decodeURIComponent(m[1]));}
    const res=await fetch(base+path,{...opts,headers,credentials:"include",signal:controller.signal});
    const text=await res.text();let body:unknown=null;
    try{body=text?JSON.parse(text):null;}catch{throw new ErrorType("INVALID_RESPONSE","The server returned an unreadable response. Try again.");}
    if(!res.ok){
      const err=(body as {error?:{code?:unknown;message?:unknown;details?:unknown;requestId?:unknown}}|null)?.error;
      const code=typeof err?.code==="string"?err.code:"HTTP_ERROR";
      // Only the API's documented error envelope is eligible for display.
      const message=typeof err?.message==="string"?err.message.slice(0,500):"The request could not be completed.";
      const out=new ErrorType(code,message,err?.details);
      Object.assign(out,{status:res.status,requestId:typeof err?.requestId==="string"?err.requestId:undefined,retryAfter:res.headers.get("Retry-After")});
      if(code==="SESSION_EXPIRED")window.dispatchEvent(new CustomEvent("ielts:session-expired"));
      throw out;
    }
    return body as T;
  }catch(e){
    if(e instanceof ErrorType)throw e;
    throw new ErrorType(controller.signal.aborted?"REQUEST_ABORTED":"NETWORK_ERROR",controller.signal.aborted?"The request timed out or was cancelled. Your work remains on this screen.":"Cannot reach the server. Check your connection and retry.");
  }finally{clearTimeout(timer);signal?.removeEventListener("abort",abort);}
}
