import React, {useEffect, useState} from "react";
import {api} from "../../lib/api/client";
import {useT} from "../../lib/i18n";
import {pushUrl} from "../../lib/urlSync";
import type {AccountUser} from "../../lib/types";
import {ViewProvider,useView} from "./viewContext";
import {WorkspaceFrame, DashboardView, JourneyView, PracticeView} from "../../experience/views";
import {useWorkspaceData} from "../../experience/controllers";
import {LearningWorkspace} from "../../experience/learning/LearningWorkspace";
import "../../experience/experience.css";

interface Props { user?:AccountUser; onLogout?:()=>Promise<void>; onProfile?:(u:AccountUser)=>void }
function ShellInner({user,onLogout,onProfile}:Props&{user:AccountUser}) {
  const {view,goWithPrefill,consumePrefill}=useView(),{lang,setLang}=useT();
  const [query,setQuery]=useState(""),[logoutError,setLogoutError]=useState("");
  const {data,retry}=useWorkspaceData(user,view==="home"?"home":"other");
  // Returning from profile edits refreshes the authoritative profile; no profile in localStorage.
  useEffect(()=>{let active=true;if(view==="home")api.accountMe().then(u=>{if(active)onProfile?.(u);}).catch(()=>{});return()=>{active=false;};},[view,user.id]);
  useEffect(()=>{document.getElementById("aruora-content")?.focus({preventScroll:true});},[view]);
  async function logout(){setLogoutError("");try{if(onLogout)await onLogout();else {await api.accountLogout();pushUrl("/");}}catch{setLogoutError(lang==="id"?"Keluar belum berhasil. Coba lagi; sesi belum dianggap berakhir.":"Sign-out did not complete. Try again; your session is not assumed to be ended.");}}
  let content:React.ReactNode;
  switch(view){
    case "home":content=<DashboardView data={data} lang={lang} nav={pushUrl} onRetry={retry}/>;break;
    case "journey":content=<JourneyView data={data} lang={lang} nav={pushUrl} onRetry={retry}/>;break;
    case "practice":content=<PracticeView lang={lang} nav={pushUrl} query={query} onQuery={setQuery}/>;break;
    default:content=<LearningWorkspace key={view} page={view} lang={lang} nav={pushUrl} onProduce={goWithPrefill} consumePrefill={consumePrefill}/>;break;
  }
  return <WorkspaceFrame lang={lang} page={view} name={user.name} nav={pushUrl} onLanguage={setLang} onLogout={()=>void logout()}>{logoutError&&<p className="aru-form-error" role="alert">{logoutError}</p>}{view==="settings"&&<div className="aru-mobile-account-actions"><button className="aru-text-button" onClick={()=>void logout()}>{lang==="id"?"Keluar dari akun":"Log out of your account"}</button></div>}{content}</WorkspaceFrame>;
}
/** Parent authentication boundary supplies the account. No fake preview identity in production. */
export function AppShell(props:Props){
  if(!props.user)return <main role="status" className="aru-state-page">Account verification required.</main>;
  return <ViewProvider><ShellInner {...props} user={props.user}/></ViewProvider>;
}
