import React,{useEffect,useRef,useState} from "react";
import {request} from "../../experience/learning/api";
import {api} from "../../lib/api/client";
import type {AccountUser} from "../../lib/types";
import {useT} from "../../lib/i18n";
import {GoogleButton} from "./GoogleButton";
import {Icon} from "../../experience/views";
import {authFailure} from "./authFailure";

interface AuthFormProps {
  mode:"login"|"register";
  onSuccess:(u:AccountUser)=>void;
  onSwitch?:()=>void;
  onSkip?:()=>void;
  onForgot?:()=>void;
  onGoogleAuthed?:(u:AccountUser,isNew:boolean)=>void;
}
export const AuthForm:React.FC<AuthFormProps>=({mode,onSuccess,onSwitch,onSkip,onForgot,onGoogleAuthed})=>{
  const {lang}=useT();
  const c=(en:string,id:string)=>lang==="id"?id:en;
  const login=mode==="login";
  const [totp,setTotp]=useState(""),[email,setEmail]=useState(""),[password,setPassword]=useState("");
  const [remember,setRemember]=useState(false),[visible,setVisible]=useState(false);
  const [error,setError]=useState(""),[busy,setBusy]=useState(false),[googleClientId,setGoogleClientId]=useState("");
  const [retryUntil,setRetryUntil]=useState(0),[remaining,setRemaining]=useState(0);
  const [invalid,setInvalid]=useState(false);
  const mfaDetails=useRef<HTMLDetailsElement>(null),mfaInput=useRef<HTMLInputElement>(null);
  const submitting=useRef(false),alive=useRef(true);
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
  useEffect(()=>{
    let active=true;
    api.health().then(h=>{if(active)setGoogleClientId(h.googleClientId||"");}).catch(()=>{});
    return()=>{active=false;};
  },[]);
  useEffect(()=>{
    if(!retryUntil){setRemaining(0);return;}
    const tick=()=>setRemaining(Math.max(0,Math.ceil((retryUntil-Date.now())/1000)));
    tick();const id=setInterval(tick,1000);return()=>clearInterval(id);
  },[retryUntil]);

  async function submit(e:React.FormEvent){
    e.preventDefault();
    if(submitting.current||busy||Date.now()<retryUntil)return;
    setError("");setInvalid(false);
    if(!email.trim()||password.length<(login?1:15)){
      setError(login?c("Enter your email and password.","Isi email dan kata sandimu."):c("Use a password of at least 15 characters.","Gunakan kata sandi minimal 15 karakter."));
      setInvalid(true);return;
    }
    submitting.current=true;setBusy(true);
    try{
      const u=login
        ?await request<AccountUser>("/api/account/login",{email:email.trim(),password,remember,totp})
        :await api.accountRegister({email:email.trim(),password});
      if(!u||!Number.isInteger(u.id)||typeof u.name!=="string")throw new Error("INVALID_ACCOUNT");
      if(!alive.current)return;
      setPassword("");setTotp("");onSuccess(u);
    }catch(e){
      if(!alive.current)return;
      const failure=authFailure(e,lang);
      setError(failure.message);setInvalid(failure.credentials);
      if(failure.retrySeconds){setRemaining(failure.retrySeconds);setRetryUntil(Date.now()+failure.retrySeconds*1000);}
      if(failure.mfa){
        if(mfaDetails.current)mfaDetails.current.open=true;
        mfaInput.current?.focus();
      }
    }finally{
      submitting.current=false;
      if(alive.current)setBusy(false);
    }
  }
  const blocked=busy||remaining>0;
  return <form className="aru-auth-form" onSubmit={submit} aria-busy={busy}>
    <div>
      <span className="aru-eyebrow">{login?c("PICK UP WHERE YOU LEFT OFF","LANJUTKAN PERJALANANMU"):c("YOUR FIRST STEP","LANGKAH PERTAMAMU")}</span>
      <h1>{login?c("Welcome back.","Selamat datang kembali."):c("A new chapter starts here.","Babak baru dimulai di sini.")}</h1>
      <p>{login?c("Log in to open your learning workspace.","Masuk untuk membuka ruang belajarmu."):c("Create your account, then set a goal at your own pace.","Buat akun, lalu tetapkan tujuan dengan ritmemu sendiri.")}</p>
    </div>
    <label className="aru-field"><span>Email</span><input type="email" required autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@example.com" disabled={busy} aria-invalid={invalid||undefined} aria-describedby={error?"aru-auth-error":undefined}/></label>
    <label className="aru-field"><span>{c("Password","Kata sandi")}</span>
      <span className="aru-password-row"><input type={visible?"text":"password"} autoComplete={login?"current-password":"new-password"} required minLength={login?1:15} value={password} onChange={e=>setPassword(e.target.value)} disabled={busy} aria-invalid={invalid||undefined} aria-describedby={error?"aru-auth-error":undefined}/>
        <button type="button" className="aru-password-toggle" aria-label={visible?c("Hide password","Sembunyikan kata sandi"):c("Show password","Tampilkan kata sandi")} aria-pressed={visible} onClick={()=>setVisible(x=>!x)}>{visible?c("Hide","Tutup"):c("Show","Lihat")}</button>
      </span>
      {!login&&<small>{c("At least 15 characters. A memorable passphrase works well.","Minimal 15 karakter. Frasa sandi yang mudah diingat bisa digunakan.")}</small>}
    </label>
    {login&&<label className="aru-check-field"><input type="checkbox" checked={remember} onChange={e=>setRemember(e.target.checked)} disabled={busy}/>{c("Keep me signed in on this device","Tetap masuk di perangkat ini")}</label>}
    {login&&<details className="aru-mfa-details" ref={mfaDetails}>
      <summary>{c("Administrator verification code","Kode verifikasi administrator")}</summary>
      <label className="aru-field"><span>{c("MFA code · only when configured","Kode MFA · hanya bila dikonfigurasi")}</span><input ref={mfaInput} inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={totp} onChange={e=>setTotp(e.target.value.replace(/\D/g,""))} aria-describedby={error?"aru-auth-error":undefined}/></label>
    </details>}
    {error&&<p id="aru-auth-error" className="aru-form-error" role="alert">{error}</p>}
    <button type="submit" className="aru-button" disabled={blocked}>
      {busy?c("Please wait…","Mohon tunggu…"):remaining>0?c(`Retry in ${remaining}s`,`Coba lagi dalam ${remaining} detik`):login?c("Log in to my workspace","Masuk ke ruang belajarku"):c("Create my account","Buat akunku")}<Icon name="arrow" size={17}/>
    </button>
    {googleClientId&&<div><div className="aru-form-divider">{c("or continue with","atau lanjut dengan")}</div><div className="aru-google-slot"><GoogleButton totp={totp} clientId={googleClientId} onSuccess={onSuccess} onGoogleAuthed={onGoogleAuthed} onError={()=>setError(c("Google sign-in did not complete. Try again.","Masuk dengan Google belum berhasil. Coba lagi."))}/></div></div>}
    {login&&onForgot&&<button type="button" className="aru-text-button aru-auth-switch" onClick={onForgot}>{c("Forgot your password?","Lupa kata sandi?")}</button>}
    {onSwitch&&<button type="button" className="aru-text-button aru-auth-switch" onClick={onSwitch}>{login?c("New here? Create an account","Baru di sini? Buat akun"):c("Already have an account? Log in","Sudah punya akun? Masuk")}</button>}
    {onSkip&&<button type="button" className="aru-text-button aru-auth-switch" onClick={onSkip}>{c("Return to website","Kembali ke website")}</button>}
  </form>;
};
