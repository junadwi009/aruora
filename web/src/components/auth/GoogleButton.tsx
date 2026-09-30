import {useEffect,useRef,useState} from "react";
import type {AccountUser} from "../../lib/types";
import {request} from "../../experience/learning/api";
interface GsiId{initialize:(o:{client_id:string;callback:(r:{credential:string})=>void})=>void;renderButton:(el:HTMLElement,o:Record<string,unknown>)=>void}
declare global{interface Window{google?:{accounts?:{id?:GsiId}}}}
let pending:Promise<void>|null=null;
function load(){if(window.google?.accounts?.id)return Promise.resolve();if(pending)return pending;pending=new Promise<void>((resolve,reject)=>{const s=document.createElement("script");s.src="https://accounts.google.com/gsi/client";s.async=true;s.defer=true;s.onload=()=>window.google?.accounts?.id?resolve():reject(new Error("Google sign-in unavailable"));s.onerror=()=>{s.remove();reject(new Error("Google sign-in unavailable"));};document.head.appendChild(s);}).catch(e=>{pending=null;throw e;});return pending;}
export function GoogleButton(props:{clientId:string;totp?:string;onSuccess:(u:AccountUser)=>void;onError?:(m:string)=>void;onGoogleAuthed?:(u:AccountUser,isNew:boolean)=>void}){
 const ref=useRef<HTMLDivElement>(null),callbacks=useRef(props),[retry,setRetry]=useState(0),[failed,setFailed]=useState(false);callbacks.current=props;
 useEffect(()=>{let active=true;setFailed(false);load().then(()=>{if(!active||!ref.current)return;const gid=window.google?.accounts?.id;if(!gid)return;gid.initialize({client_id:props.clientId,callback:async response=>{if(!active)return;try{const u=await request<AccountUser>("/api/account/google",{credential:response.credential,totp:callbacks.current.totp||""});if(!active)return;const c=callbacks.current;if(c.onGoogleAuthed)c.onGoogleAuthed(u,!!u.isNew);else c.onSuccess(u);}catch(e){if(active)callbacks.current.onError?.(e instanceof Error?e.message:"Google sign-in failed");}}});gid.renderButton(ref.current,{type:"standard",theme:"outline",size:"large",text:"continue_with",shape:"pill",width:Math.max(200,Math.min(320,ref.current.clientWidth))});}).catch(()=>{if(active)setFailed(true);});return()=>{active=false;};},[props.clientId,retry]);
 return <div className="aru-google-slot"><div ref={ref}/>{failed&&<button type="button" className="aru-text-button" onClick={()=>setRetry(x=>x+1)}>Retry Google sign-in</button>}</div>;
}
