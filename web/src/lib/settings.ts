export type Theme="light"|"dark";
export type Font="default"|"dyslexic"|"hyperlegible";
function read(key:string){try{return localStorage.getItem(key);}catch{return null;}}
function save(key:string,value:string){try{localStorage.setItem(key,value);}catch{/* preferences still apply this session */}}
export function getTheme():Theme{return read("ielts.theme")==="dark"?"dark":"light";}
export function getFont():Font{const v=read("ielts.font");return v==="dyslexic"||v==="hyperlegible"?v:"default";}
export function applyTheme(t:Theme){document.documentElement.classList.toggle("dark",t==="dark");}
export function applyFont(f:Font){const s=document.documentElement.style;for(const k of ["--font-ui","--font-reading","--font-display"]){if(f==="default")s.removeProperty(k);else s.setProperty(k,f==="dyslexic"?'"OpenDyslexic", "Atkinson Hyperlegible", system-ui, sans-serif':'"Atkinson Hyperlegible", system-ui, sans-serif');}}
export function setTheme(t:Theme){save("ielts.theme",t);applyTheme(t);}
export function setFont(f:Font){save("ielts.font",f);applyFont(f);}
export function applySettings(){applyTheme(getTheme());applyFont(getFont());}
