import React,{useEffect,useRef,useState} from "react";
import {Deadline,clockText} from "../../lib/deadline";
export interface TimerProps {seconds:number;onExpire?:()=>void;running?:boolean;resetKey?:string|number;className?:string}
export const Timer:React.FC<TimerProps>=({seconds,onExpire,running=true,resetKey,className=""})=>{
 const [left,setLeft]=useState(seconds),[announcement,setAnnouncement]=useState("");
 const model=useRef<{seconds:number;key?:string|number;clock:Deadline;announced:boolean}|null>(null);
 const callback=useRef(onExpire);callback.current=onExpire;
 useEffect(()=>{
  // Reuse the same clock across StrictMode effect replay and pause/resume.
  if(!model.current||model.current.seconds!==seconds||model.current.key!==resetKey){
   model.current={seconds,key:resetKey,clock:new Deadline(seconds,Date.now()),announced:false};setAnnouncement("");
  }
  const m=model.current,d=m.clock;
  if(running)d.resume(Date.now());else d.pause(Date.now());
  const tick=()=>{const remaining=d.remaining(Date.now());setLeft(remaining);
   if(remaining<=60&&remaining>0&&!m.announced){m.announced=true;setAnnouncement("One minute or less remaining.");}
   if(running&&d.expireOnce(Date.now())){setAnnouncement("Time is up.");callback.current?.();}
  };
  const id=window.setInterval(tick,250);
  document.addEventListener("visibilitychange",tick);tick();
  return()=>{clearInterval(id);document.removeEventListener("visibilitychange",tick);};
 },[seconds,resetKey,running]);
 return <span className={`aru-timer ${left<=60?"aru-timer-urgent":""} ${className}`}><span role="timer" aria-live="off" aria-label="Time remaining">{clockText(left)}</span><span className="aru-sr-only" role="status">{announcement}</span></span>;
};
