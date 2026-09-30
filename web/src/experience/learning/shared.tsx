import React,{useCallback,useEffect,useRef,useState} from "react";
import {Icon} from "../views";
export type Locale="en"|"id";
export type Nav=(path:string)=>void;
export const text=(l:Locale,en:string,id:string)=>l==="id"?id:en;
export function useLoad<T>(load:()=>Promise<T>,key:string){
 const [data,setData]=useState<T|null>(null),[error,setError]=useState(""),[busy,setBusy]=useState(true),[rev,setRev]=useState(0);
 const ref=useRef(load);ref.current=load;
 useEffect(()=>{let alive=true;setBusy(true);setError("");setData(null);Promise.resolve().then(()=>ref.current()).then(v=>{if(alive)setData(v);}).catch(e=>{if(alive)setError(e instanceof Error?e.message:"Request failed");}).finally(()=>{if(alive)setBusy(false);});return()=>{alive=false;};},[key,rev]);
 return {data,error,busy,retry:useCallback(()=>setRev(v=>v+1),[]),setData};
}
export function useUnsaved(active:boolean,lang:Locale){
 useEffect(()=>{if(!active)return;
  const unload=(e:BeforeUnloadEvent)=>{e.preventDefault();e.returnValue="";};
  const navigate=(e:Event)=>{if(!window.confirm(text(lang,"Leave this screen? Unsaved text or answers will be lost.","Tinggalkan halaman? Teks atau jawaban yang belum disimpan akan hilang.")))e.preventDefault();};
  window.addEventListener("beforeunload",unload);window.addEventListener("aruora:before-navigate",navigate);
  return()=>{window.removeEventListener("beforeunload",unload);window.removeEventListener("aruora:before-navigate",navigate);};
 },[active,lang]);
}
export function Heading({title,description,icon,tag,nav,lang}:{title:string;description:string;icon:string;tag?:string;nav:Nav;lang:Locale}){
 return <header className="learn-heading"><div><button className="aru-text-button learn-back" onClick={()=>nav("/app/practice")}>{text(lang,"Practice library","Pustaka latihan")}<span aria-hidden="true"> / </span></button><h1><span className={`learn-icon learn-${icon}`}><Icon name={icon} size={25}/></span>{title}</h1><p>{description}</p></div>{tag&&<span className="learn-tag">{tag}</span>}</header>;
}
export function Panel({title,children,className=""}:{title?:string;children:React.ReactNode;className?:string}){return <section className={`learn-panel ${className}`}>{title&&<h2>{title}</h2>}{children}</section>;}
export function Notice({children,tone="info"}:{children:React.ReactNode;tone?:"info"|"error"|"success"}){return <div className={`learn-notice learn-${tone}`} role={tone==="error"?"alert":"status"}><Icon name={tone==="success"?"check":tone==="error"?"info":"shield"} size={18}/><div>{children}</div></div>;}
export function LoadState({busy,error,onRetry,lang}:{busy:boolean;error:string;onRetry:()=>void;lang:Locale}){return <Panel><div className="learn-state">{busy?<><span className="learn-loading"/><p role="status">{text(lang,"Loading your workspace…","Memuat ruang belajarmu…")}</p></>:<><Icon name="info" size={30}/><h2>{text(lang,"This information could not be loaded.","Informasi belum dapat dimuat.")}</h2><p role="alert">{error}</p><button className="aru-button" onClick={onRetry}>{text(lang,"Try again","Coba lagi")}</button></>}</div></Panel>;}
export function Dialog({title,onClose,children}:{title:string;onClose:()=>void;children:React.ReactNode}){
 const ref=useRef<HTMLDialogElement>(null);
 useEffect(()=>{const d=ref.current;if(d&&!d.open)d.showModal();return()=>{if(d?.open)d.close();};},[]);
 return <dialog className="learn-dialog" ref={ref} aria-labelledby="learn-dialog-title" onCancel={onClose}><div className="learn-dialog-header"><h2 id="learn-dialog-title">{title}</h2><button className="learn-icon-button" onClick={onClose} aria-label="Close / Tutup"><Icon name="close"/></button></div>{children}</dialog>;
}
export function Tabs({items,value,onChange,label}:{items:{id:string;label:string}[];value:string;onChange:(v:string)=>void;label:string}){return <div className="learn-tabs" role="group" aria-label={label}>{items.map(i=><button key={i.id} aria-pressed={value===i.id} onClick={()=>onChange(i.id)}>{i.label}</button>)}</div>;}
export function Button({children,onClick,busy=false,disabled=false,secondary=false}:{children:React.ReactNode;onClick:()=>void;busy?:boolean;disabled?:boolean;secondary?:boolean}){return <button className={`aru-button ${secondary?"aru-button-secondary":""}`} onClick={onClick} disabled={busy||disabled}>{busy&&<span className="learn-loading"/>}{children}</button>;}
