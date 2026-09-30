import {useCallback,useEffect,useRef,useState} from "react";
import {api,type GateStatus} from "./api/client";
export function computeShouldBeat(s:{visible:boolean;focused:boolean;unlocked:boolean;isAdmin:boolean}){return s.visible&&s.focused&&!s.unlocked&&!s.isAdmin;}
export function useGate(){
 const [status,setStatus]=useState<GateStatus|null>(null),[loading,setLoading]=useState(true),[error,setError]=useState("");
 const alive=useRef(false),inflight=useRef(false);
 const refresh=useCallback(async()=>{setLoading(true);setError("");try{const s=await api.gateStatus();if(typeof s.locked!=="boolean"||typeof s.unlocked!=="boolean"||!Number.isFinite(s.heartbeatSec))throw new Error("Invalid access status");if(alive.current)setStatus(s);}catch(e){if(alive.current){setStatus(null);setError(e instanceof Error?e.message:"Access status unavailable");}}finally{if(alive.current)setLoading(false);}},[]);
 useEffect(()=>{alive.current=true;void refresh();return()=>{alive.current=false;};},[refresh]);
 useEffect(()=>{if(!status||status.unlocked||status.isAdmin||status.locked)return;const id=window.setInterval(async()=>{if(inflight.current||!computeShouldBeat({visible:document.visibilityState==="visible",focused:document.hasFocus(),unlocked:status.unlocked,isAdmin:status.isAdmin}))return;inflight.current=true;try{const result=await api.gateHeartbeat(status.heartbeatSec);if(alive.current)setStatus(s=>s?{...s,...result}:s);}catch(e){if(alive.current)setError(e instanceof Error?e.message:"Access status unavailable");}finally{inflight.current=false;}},Math.max(15,status.heartbeatSec)*1000);return()=>clearInterval(id);},[status]);
 const markUnlocked=useCallback(()=>{setStatus(s=>s?{...s,locked:false,unlocked:true}:s);setError("");},[]);
 return {locked:!!status?.locked,loading,error,refresh,markUnlocked};
}
