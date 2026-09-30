import {useEffect,useState,useRef} from "react";
import {PracticeScreen} from "./PracticeScreen";
import {ResponseScreen} from "./ResponseScreen";
import {RoleplayScreen} from "./RoleplayScreen";
import {VocabularyScreen} from "./VocabularyScreen";
import {LessonScreen} from "./LessonScreen";
import {TipsScreen} from "./TipsScreen";
import {ProgressScreen} from "./ProgressScreen";
import {MockScreen} from "./MockScreen";
import {PronounceScreen} from "./PronounceScreen";
import {SettingsScreen} from "./SettingsScreen";
import type {Locale,Nav} from "./shared";
import "./learning.css";
export function LearningWorkspace({page,lang,nav,onProduce,consumePrefill}:{page:string;lang:Locale;nav:Nav;onProduce?:(skill:string,value:string)=>void;consumePrefill?:(skill:string)=>string|null}){
 const [prefill,setPrefill]=useState("");const consumed=useRef("");
 useEffect(()=>{if(consumed.current!==page){consumed.current=page;setPrefill(consumePrefill?.(page)||"");}},[page,consumePrefill]);
 switch(page){
 case "reading":case "listening":return <PracticeScreen key={page} skill={page} lang={lang} nav={nav}/>;
 case "writing":case "speaking":return <ResponseScreen key={page+prefill} kind={page} lang={lang} nav={nav} prefill={prefill}/>;
 case "roleplay":return <RoleplayScreen lang={lang} nav={nav}/>;
 case "vocab":return <VocabularyScreen lang={lang} nav={nav}/>;
 case "session":return <LessonScreen lang={lang} nav={nav} onProduce={onProduce}/>;
 case "tips":return <TipsScreen lang={lang} nav={nav}/>;
 case "progress":return <ProgressScreen lang={lang} nav={nav}/>;
 case "test":return <MockScreen lang={lang} nav={nav}/>;
 case "pronounce":return <PronounceScreen lang={lang} nav={nav}/>;
 case "settings":return <SettingsScreen lang={lang} nav={nav}/>;
 default:return <p role="alert">Unknown learning screen.</p>;
 }
}
