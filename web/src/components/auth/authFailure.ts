/** Safe authentication messages. HTTP 429 takes precedence over a legacy
 * UNAUTHORIZED code; never show server payloads or account-existence hints. */
import {ApiError} from "../../lib/api/client";
export function authFailure(error:unknown,lang:string):{message:string;retrySeconds:number;mfa:boolean;credentials:boolean}{
  const c=(en:string,id:string)=>lang==="id"?id:en;
  const e=error instanceof ApiError?error as ApiError&{status?:number;retryAfter?:string|null}:null;
  const throttled=e?.status===429||e?.code==="RATE_LIMITED";
  if(throttled){
    const details=e?.details as {retryAfter?:unknown}|undefined;
    const raw=e?.retryAfter??details?.retryAfter;
    let delay=typeof raw==="number"?raw:typeof raw==="string"&&/^\d+(\.\d+)?$/.test(raw.trim())?Number(raw):NaN;
    if(!Number.isFinite(delay)&&typeof raw==="string")delay=(Date.parse(raw)-Date.now())/1000;
    // The countdown is a UX aid, not an authorization boundary; the server
    // remains authoritative if the page is reloaded or the delay changes.
    const retrySeconds=Number.isFinite(delay)?Math.max(1,Math.min(86400,Math.ceil(delay))):60;
    return {message:c("Too many sign-in attempts. Wait before trying again.","Terlalu banyak percobaan masuk. Tunggu sebelum mencoba lagi."),retrySeconds,mfa:false,credentials:false};
  }
  const code=e?.code;
  const mfa=code==="ADMIN_MFA_REQUIRED";
  const credentials=code==="UNAUTHORIZED";
  const message=mfa?c("Enter your current administrator verification code.","Masukkan kode verifikasi administrator saat ini.")
    :credentials?c("Sign-in was not completed. Check your credentials and any account requirements.","Masuk belum berhasil. Periksa kredensial dan persyaratan akunmu.")
    :code==="VALIDATION"?c("Check your details. The password must meet the account policy; an existing email should use Log in.","Periksa isianmu. Kata sandi harus memenuhi kebijakan akun; gunakan Masuk untuk email yang sudah terdaftar.")
    :code==="CSRF_REJECTED"?c("Your security token has changed. Reload this page before trying again.","Token keamanan berubah. Muat ulang halaman sebelum mencoba lagi.")
    :["NETWORK_ERROR","REQUEST_ABORTED"].includes(code||"")?c("The server could not be reached in time. Check your connection and retry.","Server belum dapat dijangkau tepat waktu. Periksa koneksi dan coba lagi.")
    :c("Your account is temporarily unavailable. Please try again.","Akun sementara belum dapat diakses. Silakan coba lagi.");
  return {message,retrySeconds:0,mfa,credentials};
}
