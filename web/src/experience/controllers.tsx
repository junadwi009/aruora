import React, {useCallback, useEffect, useState} from "react";
import {api} from "../lib/api/client";
import {useT} from "../lib/i18n";
import {useJourney} from "../lib/journey";
import {pushUrl} from "../lib/urlSync";
import type {AccountUser, Goal} from "../lib/types";
import {SKILLS, band, parseReadiness, examMonth, errorMessage, type DashboardData, type Readiness, type Locale} from "./model";
import {Logo, Link, Icon, LanguageControl, ResultView, PageState} from "./views";

export const navigate = (path:string) => pushUrl(path);
const tr=(lang:Locale,en:string,id:string)=>lang==="id"?id:en;
/** Each endpoint owns its own error state. A failure never becomes an empty success. */
export function useWorkspaceData(user:AccountUser, refreshKey:string="") {
  const [revision,setRevision]=useState(0);
  const [data,setData]=useState<DashboardData>(()=>({profile:user,readiness:null,readinessState:"loading",milestones:[],milestonesState:"loading",activity:null,activityState:"loading"}));
  const retry=useCallback(()=>setRevision(x=>x+1),[]);
  useEffect(()=>{
    let alive=true;
    setData({profile:user,readiness:null,readinessState:"loading",milestones:[],milestonesState:"loading",activity:null,activityState:"loading"});
    api.historyReadiness().then(parseReadiness).then(r=>{if(alive)setData(d=>({...d,readiness:r,readinessState:"ready"}));}).catch(()=>{if(alive)setData(d=>({...d,readiness:null,readinessState:"error"}));});
    api.milestones().then(rows=>{
      if(!Array.isArray(rows)||rows.some(r=>!Number.isFinite(r.idx)||!Number.isFinite(r.dayTarget)||typeof r.title!=="string"||!r.targets||typeof r.targets!=="object"))throw new Error("INVALID_MILESTONES");
      if(alive)setData(d=>({...d,milestones:rows,milestonesState:"ready"}));
    }).catch(()=>{if(alive)setData(d=>({...d,milestones:[],milestonesState:"error"}));});
    api.statsActivity().then(a=>{
      if(!a||[a.current,a.longest,a.today,a.daysActive].some(v=>!Number.isInteger(v)||v<0))throw new Error("INVALID_ACTIVITY");
      if(alive)setData(d=>({...d,activity:a,activityState:"ready"}));
    }).catch(()=>{if(alive)setData(d=>({...d,activity:null,activityState:"error"}));});
    return()=>{alive=false;};
  },[user.id,user.name,user.goal,user.targetBand,user.examDate,user.emailVerified,revision,refreshKey]);
  return {data,retry};
}

export function SetupPage({user,onProfile}:{user:AccountUser;onProfile:(u:AccountUser)=>void}) {
  const {lang,setLang}=useT();
  const [name,setName]=useState(user.name||"");
  const [goal,setGoal]=useState<Goal>((["work","study_abroad","other"].includes(user.goal)?user.goal:"") as Goal);
  const [target,setTarget]=useState(user.targetBand||6.5);
  const [month,setMonth]=useState(user.examDate?.slice(0,7)||"");
  const [busy,setBusy]=useState(false),[error,setError]=useState("");
  async function submit(e:React.FormEvent) {
    e.preventDefault();setError("");
    if(!name.trim()||!goal){setError(tr(lang,"Add your name and choose a goal.","Isi nama dan pilih tujuanmu."));return;}
    if(month&&!examMonth(month,lang)){setError(tr(lang,"Choose a valid month.","Pilih bulan yang valid."));return;}
    setBusy(true);
    try {
      await api.onboarding({name:name.trim(),goal,targetBand:target,examDate:month||undefined});
      const updated=await api.accountMe();onProfile({...updated,isNew:false});navigate("/placement");
    }catch(e){setError(errorMessage(e,lang));}finally{setBusy(false);}
  }
  return <div className="aru-setup-page"><header className="aru-setup-header"><Logo nav={navigate}/><div className="aru-header-actions"><Link href="/app" nav={navigate} className="aru-text-link">{tr(lang,"Back to workspace","Kembali ke ruang belajar")}</Link><LanguageControl lang={lang} onChange={setLang}/></div></header><main className="aru-setup-card"><span className="aru-eyebrow">{tr(lang,"FIRST, A LITTLE DIRECTION","PERTAMA, TENTUKAN ARAH")}</span><h1>{tr(lang,"What are you working toward?","Apa yang ingin kamu capai?")}</h1><p>{tr(lang,"Start with your goal and target. Your exam month is optional—you can refine the details later.","Mulai dari tujuan dan targetmu. Bulan ujian opsional—rinciannya dapat dilengkapi nanti.")}</p><form onSubmit={submit}><label className="aru-field"><span>{tr(lang,"What should we call you?","Siapa nama panggilanmu?")}</span><input autoComplete="given-name" maxLength={100} required value={name} onChange={e=>setName(e.target.value)}/></label><fieldset><legend>{tr(lang,"Your learning goal","Tujuan belajarmu")}</legend><div className="aru-option-grid">{([
        ["study_abroad",tr(lang,"Study & scholarships","Studi & beasiswa"),tr(lang,"Prepare for your next academic step.","Persiapkan langkah akademik berikutnya.")],
        ["work",tr(lang,"Career opportunities","Peluang karier"),tr(lang,"Work toward your professional goal.","Persiapkan tujuan profesionalmu.")],
        ["other",tr(lang,"My own goal","Tujuanku sendiri"),tr(lang,"A retake or another personal milestone.","Ujian ulang atau pencapaian pribadi lainnya.")]
      ] as const).map(([g,label,desc])=><label key={g} className="aru-radio-card"><input type="radio" name="goal" value={g} checked={goal===g} onChange={()=>setGoal(g)} required/><span><b>{label}</b><small>{desc}</small></span></label>)}</div></fieldset><div className="aru-form-grid"><label className="aru-field"><span>{tr(lang,"Overall IELTS target","Target overall IELTS")}</span><select value={target} onChange={e=>setTarget(Number(e.target.value))}>{Array.from({length:11},(_,i)=>4+i/2).map(v=><option key={v} value={v}>{v.toFixed(1)}</option>)}</select><small>{tr(lang,"Use a requirement you have checked; ARUORA does not infer institutional requirements.","Gunakan persyaratan yang sudah kamu periksa; ARUORA tidak menebak syarat institusi.")}</small></label><label className="aru-field"><span>{tr(lang,"Exam month · optional","Bulan ujian · opsional")}</span><input type="month" min="2020-01" max="2200-12" value={month} onChange={e=>setMonth(e.target.value)}/><small>{tr(lang,"Shown as a month, not an exact-day countdown.","Ditampilkan sebagai bulan, bukan hitung mundur tanggal pasti.")}</small></label></div>{error&&<p role="alert" className="aru-form-error">{error}</p>}<div className="aru-actions"><button type="submit" disabled={busy} className="aru-button">{busy?tr(lang,"Saving…","Menyimpan…"):tr(lang,"Continue to placement","Lanjut ke penempatan")}<Icon name="arrow" size={17}/></button><Link href="/app" nav={navigate} className="aru-text-link">{tr(lang,"Do this later","Lakukan nanti")}</Link></div></form></main></div>;
}

export function PlanPage({user}:{user:AccountUser}) {
  const {lang}=useT();const {setMilestones}=useJourney();
  const [days,setDays]=useState(90),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const month=examMonth(user.examDate,lang);
  async function submit(e:React.FormEvent){e.preventDefault();setBusy(true);setError("");try{const r=await api.program(days);setMilestones(r.milestones);navigate("/app/journey");}catch(e){setError(errorMessage(e,lang));}finally{setBusy(false);}}
  return <div className="aru-setup-page"><header className="aru-setup-header"><Logo nav={navigate}/><Link href="/app/journey" nav={navigate} className="aru-text-link">{tr(lang,"Back to my journey","Kembali ke perjalanan")}</Link></header><main className="aru-setup-card"><span className="aru-eyebrow">{tr(lang,"GIVE YOUR PRACTICE A SHAPE","SUSUN ARAH LATIHANMU")}</span><h1>{tr(lang,"Build a plan you can revisit.","Buat rencana yang bisa ditinjau.")}</h1><p>{tr(lang,"Choose a planning horizon for your checkpoints. This is not an estimate of how long a band improvement will take.","Pilih rentang rencana untuk checkpoint-mu. Ini bukan estimasi waktu yang dibutuhkan untuk meningkatkan band.")}</p><form onSubmit={submit}><p className="aru-contract-note"><Icon name="calendar" size={16}/> {tr(lang,"Your target month:","Bulan targetmu:")} <b>{month??tr(lang,"Not set","Belum ditentukan")}</b>. {tr(lang,"The existing planner does not yet schedule around exact exam dates or study capacity.","Perencana saat ini belum menjadwalkan berdasarkan tanggal ujian pasti atau kapasitas belajar.")}</p><fieldset><legend>{tr(lang,"Planning horizon","Rentang rencana")}</legend><div className="aru-option-grid">{[30,90,180].map(n=><label key={n} className="aru-radio-card"><input name="horizon" type="radio" checked={n===days} onChange={()=>setDays(n)}/><span><b>{n} {tr(lang,"days","hari")}</b><small>{n===30?tr(lang,"A near-term structure","Struktur jangka dekat"):n===90?tr(lang,"A broader learning plan","Rencana belajar yang lebih luas"):tr(lang,"A longer planning horizon","Rentang perencanaan lebih panjang")}</small></span></label>)}</div></fieldset><p className="aru-contract-note">{tr(lang,"Creating a plan can replace your existing plan and checkpoints. Check your current journey before continuing. Milestones describe intentions, not verified achievements.","Membuat rencana dapat mengganti rencana dan checkpoint yang ada. Periksa perjalananmu sebelum melanjutkan. Milestone adalah rencana, bukan pencapaian terverifikasi.")}</p>{error&&<p role="alert" className="aru-form-error">{error}</p>}<button className="aru-button" type="submit" disabled={busy}>{busy?tr(lang,"Creating plan…","Membuat rencana…"):tr(lang,"Create my planning horizon","Buat rentang rencanaku")}<Icon name="arrow" size={17}/></button></form></main></div>;
}

/** Current placement remains in memory: refresh never invents an old result. */
export function AssessmentResults({user}:{user:AccountUser}) {
  const {placementResult}=useJourney();const {lang}=useT();
  if(!placementResult)return <PageState lang={lang} title={tr(lang,"This snapshot is no longer open.","Snapshot ini tidak lagi terbuka.")} message={tr(lang,"Placement snapshots live in this session. Open your workspace for saved evidence, or take a new placement.","Snapshot penempatan berada di sesi ini. Buka ruang belajar untuk bukti tersimpan, atau ikuti penempatan baru.")} onRetry={()=>navigate("/app")} nav={navigate}/>;
  const rows={} as Readiness["perSkill"];
  for(const skill of SKILLS){const p=placementResult.perSkill?.[skill];const estimate=p?.assessed===false?null:band(p?.ieltsApprox??p?.ielts);const rawTarget=user.skillTargets?.[skill] as unknown;const target=band(rawTarget)??user.targetBand;rows[skill]={estimate,target,assessed:estimate!==null,gap:estimate===null?null:target-estimate,confidence:p?.confidence};}
  const missing=SKILLS.filter(s=>!rows[s].assessed);
  const r:Readiness={method:"placement-snapshot",generatedAt:null,targetBand:user.targetBand,currentEstimate:missing.length?null:band(placementResult.overallBand),perSkill:rows,evidenceCoverage:{assessed:4-missing.length,total:4,complete:!missing.length,missing}};
  return <ResultView r={r} lang={lang} nav={navigate}/>;
}
