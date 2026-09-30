import {useState} from "react";
import {request} from "./api";
import {Heading,Panel,Tabs,LoadState,useLoad,text,type Locale,type Nav} from "./shared";
export function TipsScreen({lang,nav}:{lang:Locale;nav:Nav}){
 const [skill,setSkill]=useState("reading");const r=useLoad(()=>request<{title:string;bullets:string[]}>(`/api/tips/${skill}`),`${skill}:${lang}`);
 return <div className="learn-page"><Heading title={text(lang,"A little guidance","Panduan belajar")} description={text(lang,"Practical strategies you can use in your next session.","Strategi praktis yang bisa kamu terapkan pada sesi berikutnya.")} icon="help" tag="LEARNING SUPPORT" nav={nav} lang={lang}/><Tabs label="Skill guidance" value={skill} onChange={setSkill} items={["reading","listening","writing","speaking"].map(id=>({id,label:id[0].toUpperCase()+id.slice(1)}))}/>{r.busy||r.error?<LoadState busy={r.busy} error={r.error} onRetry={r.retry} lang={lang}/>:r.data&&<Panel title={r.data.title}><ol className="learn-guide-list">{r.data.bullets.map((b,i)=><li key={i}><span>{String(i+1).padStart(2,"0")}</span><p>{b}</p></li>)}</ol></Panel>}</div>;
}
