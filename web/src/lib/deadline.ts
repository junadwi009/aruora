/** Pure deadline model; interval ticks are never a measurement of elapsed time. */
export class Deadline {
  private end:number;
  private pausedRemaining:number|null=null;
  private delivered=false;
  constructor(seconds:number,now:number){
    if(!Number.isFinite(seconds)||seconds<0||!Number.isFinite(now))throw new RangeError("Invalid timer input");
    this.end=now+seconds*1000;
  }
  remaining(now:number):number{return Math.max(0,Math.ceil((this.pausedRemaining??(this.end-now))/1000));}
  pause(now:number):void{if(this.pausedRemaining===null)this.pausedRemaining=Math.max(0,this.end-now);}
  resume(now:number):void{if(this.pausedRemaining!==null){this.end=now+this.pausedRemaining;this.pausedRemaining=null;}}
  expireOnce(now:number):boolean{if(this.remaining(now)>0||this.delivered)return false;this.delivered=true;return true;}
}
export const clockText=(seconds:number)=>`${String(Math.floor(seconds/60)).padStart(2,"0")}:${String(seconds%60).padStart(2,"0")}`;
