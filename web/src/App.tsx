import {ExperienceBoundary} from "./experience/ExperienceBoundary";
import {lazy,Suspense,useEffect,useState} from "react";
import {api,ApiError} from "./lib/api/client";
import type {AccountUser} from "./lib/types";
import {JourneyProvider,useJourney} from "./lib/journey";
import {useT} from "./lib/i18n";
import {useGate} from "./lib/gate";
import {currentPath,pushUrl,replaceUrl,safeAppReturn,stepFromPath} from "./lib/urlSync";
import {LandingView,AuthLayout,PageState} from "./experience/views";
import {AuthForm} from "./components/auth/AuthForm";
import {PasscodeGate} from "./components/auth/PasscodeGate";
import {FeedbackGate} from "./components/gate/FeedbackGate";
import {ForgotForm,RecoveryForm,type OneTimeLink} from "./experience/Recovery";
import {SetupPage,PlanPage,AssessmentResults} from "./experience/controllers";
import "./experience/experience.css";
import "./experience/learning/learning.css";
const AppShell=lazy(()=>import("./components/menu/AppShell").then(m=>({default:m.AppShell})));
const PlacementScreen=lazy(()=>import("./experience/learning/PlacementScreen").then(m=>({default:m.PlacementScreen})));


function useLocation(){
 const [location,setLocation]=useState(()=>({path:currentPath().replace(/\/+$/, "")||"/",search:window.location.search}));
 useEffect(()=>{const update=()=>setLocation({path:currentPath().replace(/\/+$/, "")||"/",search:window.location.search});window.addEventListener("popstate",update);window.addEventListener("aruora:navigate",update);return()=>{window.removeEventListener("popstate",update);window.removeEventListener("aruora:navigate",update);};},[]);
 return location;
}
function Busy(){const {lang}=useT();return <main className="aru-state-page" role="status">{lang==="id"?"Memeriksa sesi…":"Checking your session…"}</main>;}
function ProtectedContent({path,user,onProfile,onLogout}:{path:string;user:AccountUser;onProfile:(u:AccountUser)=>void;onLogout:()=>Promise<void>}){
 const gate=useGate();const {lang}=useT();const {setPlacementResult}=useJourney();
 if(path==="/app/settings")return <Suspense fallback={<Busy/>}><AppShell user={user} onLogout={onLogout} onProfile={onProfile}/></Suspense>;
 if(gate.loading)return <Busy/>;
 if(gate.error)return <PageState lang={lang} title={lang==="id"?"Status akses belum dapat dikonfirmasi.":"Access could not be confirmed."} message={gate.error} onRetry={()=>void gate.refresh()} nav={pushUrl}/>;
 if(gate.locked)return <FeedbackGate onUnlocked={gate.markUnlocked}/>;
 const step=stepFromPath(path);
 return <Suspense fallback={<Busy/>}>{step==="app"?<AppShell user={user} onLogout={onLogout} onProfile={onProfile}/>:step==="onboarding"?<SetupPage user={user} onProfile={onProfile}/>:step==="placement"?<PlacementScreen lang={lang} nav={pushUrl} onResult={r=>{setPlacementResult(r);replaceUrl("/placement/results");}}/>:step==="generating"?<AssessmentResults user={user}/>:step==="results"?<AssessmentResults user={user}/>:step==="program"?<PlanPage user={user}/>:step==="milestones"?<AppShell user={user} onLogout={onLogout} onProfile={onProfile}/>:null}</Suspense>;
}
function AccessRouter({path,search,link,onLinkDone}:{path:string;search:string;link:OneTimeLink|null;onLinkDone:()=>void}){
 const {lang,setLang}=useT();const c=(en:string,id:string)=>lang==="id"?id:en;
 const {setPlacementResult,setMilestones}=useJourney();
 const [phase,setPhase]=useState<"loading"|"passcode"|"anonymous"|"account"|"error">("loading");
 const [user,setUser]=useState<AccountUser|null>(null),[attempt,setAttempt]=useState(0);
 const authScreen=["/login","/register","/forgot-password"].includes(path);
 const wanted=safeAppReturn(new URLSearchParams(search).get("next"));
 useEffect(()=>{
  let active=true;setPhase("loading");
  (async()=>{
   try {
    const status=await api.authStatus();
    if(!active)return;
    if(!status||typeof status.authRequired!=="boolean"||typeof status.authenticated!=="boolean")throw new Error("INVALID_AUTH_STATUS");
    if(status.authRequired&&!status.authenticated){setPhase("passcode");return;}
    // Global passcode state is NOT account authentication.
    try{const u=await api.accountMe();if(!active)return;if(!u||!Number.isInteger(u.id)||typeof u.name!=="string")throw new Error("INVALID_ACCOUNT");setUser(u);setPhase("account");}
    catch(e){if(!active)return;if(e instanceof ApiError&&(e.code==="UNAUTHORIZED"||e.code==="SESSION_EXPIRED")){setUser(null);setPhase("anonymous");}else throw e;}
   }catch{if(active){setUser(null);setPhase("error");}}
  })();return()=>{active=false;};
 },[attempt]);
 useEffect(()=>{
  if(link)return;
  if(phase==="anonymous"&&!authScreen)replaceUrl(`/login?next=${safeAppReturn(path)}`);
  if(phase==="account"&&(path==="/login"||path==="/register"))replaceUrl(wanted);
  if(phase==="account"&&path==="/milestones")replaceUrl("/app/journey");
 },[phase,path,authScreen,wanted,link]);
 useEffect(()=>{const expire=()=>{setUser(null);setPlacementResult(null);setMilestones([]);setPhase("anonymous");replaceUrl(`/login?next=${safeAppReturn(currentPath())}`);};window.addEventListener("ielts:session-expired",expire);return()=>window.removeEventListener("ielts:session-expired",expire);},[setPlacementResult,setMilestones]);
 const success=(u:AccountUser)=>{setPlacementResult(null);setMilestones([]);setUser(u);setPhase("account");replaceUrl(wanted);};
 async function logout(){await api.accountLogout();setPlacementResult(null);setMilestones([]);setUser(null);setPhase("anonymous");replaceUrl("/");}
 if(phase==="loading")return <Busy/>;
 if(phase==="error")return <PageState lang={lang} title={c("We can't confirm your session.","Sesi belum dapat dikonfirmasi.")} message={c("Your workspace stays closed until account verification succeeds. Your data has not been replaced with sample values.","Ruang belajar tetap tertutup sampai pemeriksaan akun berhasil. Datamu tidak diganti dengan nilai contoh.")} onRetry={()=>setAttempt(n=>n+1)} nav={pushUrl}/>;
 if(phase==="passcode")return <AuthLayout lang={lang} onLanguage={setLang} nav={pushUrl}><PasscodeGate onUnlock={()=>setAttempt(n=>n+1)}/></AuthLayout>;
 if(link)return <AuthLayout lang={lang} onLanguage={setLang} nav={pushUrl}><RecoveryForm link={link} onDone={()=>{setUser(null);setPlacementResult(null);setMilestones([]);onLinkDone();setAttempt(n=>n+1);}}/></AuthLayout>;
 if(path==="/forgot-password")return <AuthLayout lang={lang} onLanguage={setLang} nav={pushUrl}><ForgotForm onBack={()=>pushUrl("/login")}/></AuthLayout>;
 if(phase==="anonymous")return <AuthLayout lang={lang} onLanguage={setLang} nav={pushUrl}><AuthForm key={path} mode={path==="/register"?"register":"login"} onSuccess={success} onGoogleAuthed={(u,isNew)=>success({...u,isNew})} onSwitch={()=>pushUrl(`${path==="/register"?"/login":"/register"}?next=${wanted}`)} onForgot={()=>pushUrl("/forgot-password")} onSkip={()=>pushUrl("/")}/></AuthLayout>;
 if(!user)return <Busy/>;
 return <ProtectedContent path={path} user={user} onProfile={(u)=>setUser(prev=>({...u,isNew:u.isNew??prev?.isNew}))} onLogout={logout}/>;
}

function AppContent(){
 const {path,search}=useLocation(),{lang,setLang}=useT();
 const [link,setLink]=useState<OneTimeLink|null>(()=>{
  const q=new URLSearchParams(window.location.search);const reset=q.get("reset_token"),verify=q.get("verify_token");
  const token=reset||verify;return token&&token.length<=512?{kind:reset?"reset":"verify",token}:null;
 });
 useEffect(()=>{if(link)replaceUrl("/");},[]); // strip one-time token before third-party auth UI loads
 useEffect(()=>{document.documentElement.lang=lang;document.title=path.startsWith("/app")?"Your workspace · ARUORA IELTS":path==="/login"?"Log in · ARUORA":path==="/register"?"Get started · ARUORA":"ARUORA · Your journey starts with language";},[path,lang]);
 useEffect(()=>{let icon=document.querySelector<HTMLLinkElement>('link[rel="icon"]');if(!icon){icon=document.createElement("link");icon.rel="icon";document.head.appendChild(icon);}icon.href="/brand/favicon.png";},[]);
 // Marketing renders independently of backend/passcode availability.
 if(path==="/"&&!link)return <LandingView lang={lang} nav={pushUrl} onLanguage={setLang}/>;
 if(!stepFromPath(path)&&!link)return <PageState lang={lang} title={lang==="id"?"Halaman tidak ditemukan.":"This page isn't here."} message={lang==="id"?"Kembali ke website untuk melanjutkan.":"Return to the website to find your next step."} nav={pushUrl}/>;
 return <JourneyProvider><AccessRouter path={path} search={search} link={link} onLinkDone={()=>{setLink(null);replaceUrl("/login");}}/></JourneyProvider>;
}

export default function App(){return <ExperienceBoundary><AppContent/></ExperienceBoundary>;}
