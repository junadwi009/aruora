import React, { createContext, useCallback, useContext, useMemo, useState } from "react";

// Lightweight in-house i18n. Strings live in DICT; `t(key)` falls back to the
// English string, then the key itself. Language persists in localStorage and is
// applied at boot. Coverage starts with the high-visibility surfaces (nav,
// welcome, settings) and is migrated incrementally.

export type Lang = "en" | "id";
const LANG_KEY = "ielts.lang";

type Dict = Record<string, string>;

const EN: Dict = {
  // nav
  "nav.home": "Home", "nav.reading": "Reading", "nav.listening": "Listening",
  "nav.speaking": "Speaking", "nav.writing": "Writing", "nav.pronounce": "Pronounce",
  "nav.vocab": "Vocab", "nav.test": "Test", "nav.tips": "Tips", "nav.progress": "Progress",
  "nav.settings": "Settings", "nav.practice": "Practice", "nav.roleplay": "Roleplay",
  // welcome
  "welcome.title": "Find your level, then improve it.",
  "welcome.subtitle": "Expert feedback on Writing & Speaking you can't grade yourself — plus Reading, Listening, and a personalised study plan.",
  "welcome.getStarted": "Get started",
  "welcome.haveAccount": "I already have an account",
  // settings sections
  "settings.title": "Settings",
  "settings.appearance": "Appearance", "settings.font": "Reading font",
  "settings.profile": "Profile", "settings.targets": "Targets", "settings.security": "Security",
  "settings.milestones": "Milestones", "settings.data": "Data & privacy",
  "settings.help": "Help", "settings.language": "Language",
  "common.light": "Light", "common.dark": "Dark", "common.signOut": "Sign out",
  "common.save": "Save", "common.cancel": "Cancel", "common.back": "Back", "common.next": "Next",
  "common.loading": "Loading…", "common.saved": "Saved", "common.estimate": "estimate",
  // auth
  "auth.welcomeBack": "Welcome back", "auth.createAccount": "Create your account",
  "auth.signinSub": "Sign in to continue your prep.",
  "auth.registerSub": "Save your progress and pick up on any device.",
  "auth.email": "Email", "auth.password": "Password",
  "auth.signIn": "Sign in", "auth.createBtn": "Create account",
  "auth.toRegister": "New here? Create an account", "auth.toLogin": "Already have an account? Sign in",
  "auth.forgot": "Forgot your password?", "auth.maybeLater": "Maybe later — continue without an account",
  "auth.badCreds": "Enter an email and a password of at least 6 characters.",
  "auth.passcodeTitle": "Enter passcode", "auth.passcodeSub": "This IELTS Coach instance is passcode-protected.",
  "auth.unlock": "Unlock", "auth.wrongPasscode": "Incorrect passcode. Try again.",
  "auth.resetTitle": "Reset your password", "auth.resetSub": "Enter your account email and we'll send a reset link.",
  "auth.sendLink": "Send reset link", "auth.backToSignin": "Back to sign in",
  "auth.newPassword": "Choose a new password", "auth.resetBtn": "Reset password",
  "auth.resetDone": "Password updated. You can sign in now.", "auth.goSignin": "Go to sign in",
  // onboarding
  "onb.name": "What's your name?", "onb.goal": "Why are you taking IELTS?",
  "onb.target": "Your target band", "onb.startPlacement": "Start placement",
  "onb.goalWork": "Work", "onb.goalStudy": "Study abroad", "onb.goalOther": "Other",
  // results / program
  "results.saveCta": "Save your results",
  "program.choose": "Choose your program",
  // home
  "home.dashboard": "Dashboard", "home.today": "Today", "home.todaySub": "Start today's guided session",
  "home.start": "Start", "home.yourSkills": "Your Skills", "home.targeting": "Targeting",
  "home.notAssessed": "Not assessed yet", "home.milestones": "Program Milestones",
  "home.quickAccess": "Quick Access", "home.streak": "day streak",
  "home.goalDone": "Today's goal done — nice!", "home.goalTodo": "Do one task today to keep it going.",
  "home.examCountdown": "Exam countdown", "home.daysToGo": "days to go", "home.examToday": "Exam is today — good luck!",
  // settings sections
  "set.dataDownload": "Download all your data as JSON", "set.export": "Export",
  "set.deleteAccount": "Delete account & all data", "set.delete": "Delete",
  "set.reminder": "Study reminder", "set.reminderDaily": "Daily email reminder",
  "set.targetsOverall": "Overall band target", "set.targetsPerSkill": "Per-skill CEFR target",
  "set.changePassword": "Change password", "set.signedIn": "Signed in",
  "set.help": "Help",
  // admin (master admin — Manage users)
  "settings.admin": "Admin", "admin.title": "Master admin",
  "admin.sub": "Manage accounts on this instance.",
  "admin.accounts": "Accounts", "admin.attempts": "Attempts", "admin.anon": "Anonymous",
  "admin.user": "User", "admin.usage": "Usage", "admin.actions": "Actions",
  "admin.resetPw": "Send reset link", "admin.delete": "Delete user",
  "admin.resetSent": "Reset link sent", "admin.you": "you",
  "admin.confirmDelete": "Delete this user and ALL their data? This cannot be undone.",
  "admin.empty": "No accounts yet.",
};

const ID: Dict = {
  "nav.home": "Beranda", "nav.reading": "Membaca", "nav.listening": "Menyimak",
  "nav.speaking": "Berbicara", "nav.writing": "Menulis", "nav.pronounce": "Pelafalan",
  "nav.vocab": "Kosakata", "nav.test": "Ujian", "nav.tips": "Tips", "nav.progress": "Kemajuan",
  "nav.settings": "Pengaturan", "nav.practice": "Latihan", "nav.roleplay": "Roleplay",
  "welcome.title": "Temukan levelmu, lalu tingkatkan.",
  "welcome.subtitle": "Umpan balik pakar untuk Menulis & Berbicara yang tak bisa kamu nilai sendiri — plus Membaca, Menyimak, dan rencana belajar personal.",
  "welcome.getStarted": "Mulai",
  "welcome.haveAccount": "Saya sudah punya akun",
  "settings.title": "Pengaturan",
  "settings.appearance": "Tampilan", "settings.font": "Font bacaan",
  "settings.profile": "Profil", "settings.targets": "Target", "settings.security": "Keamanan",
  "settings.milestones": "Milestone", "settings.data": "Data & privasi",
  "settings.help": "Bantuan", "settings.language": "Bahasa",
  "common.light": "Terang", "common.dark": "Gelap", "common.signOut": "Keluar",
  "common.save": "Simpan", "common.cancel": "Batal", "common.back": "Kembali", "common.next": "Lanjut",
  "common.loading": "Memuat…", "common.saved": "Tersimpan", "common.estimate": "perkiraan",
  "auth.welcomeBack": "Selamat datang kembali", "auth.createAccount": "Buat akun Anda",
  "auth.signinSub": "Masuk untuk melanjutkan persiapan.",
  "auth.registerSub": "Simpan progres dan lanjutkan dari perangkat mana pun.",
  "auth.email": "Email", "auth.password": "Kata sandi",
  "auth.signIn": "Masuk", "auth.createBtn": "Buat akun",
  "auth.toRegister": "Baru di sini? Buat akun", "auth.toLogin": "Sudah punya akun? Masuk",
  "auth.forgot": "Lupa kata sandi?", "auth.maybeLater": "Nanti saja — lanjut tanpa akun",
  "auth.badCreds": "Masukkan email dan kata sandi minimal 6 karakter.",
  "auth.passcodeTitle": "Masukkan passcode", "auth.passcodeSub": "Instance IELTS Coach ini dilindungi passcode.",
  "auth.unlock": "Buka", "auth.wrongPasscode": "Passcode salah. Coba lagi.",
  "auth.resetTitle": "Atur ulang kata sandi", "auth.resetSub": "Masukkan email akun Anda, kami kirim tautan reset.",
  "auth.sendLink": "Kirim tautan reset", "auth.backToSignin": "Kembali ke Masuk",
  "auth.newPassword": "Pilih kata sandi baru", "auth.resetBtn": "Atur ulang kata sandi",
  "auth.resetDone": "Kata sandi diperbarui. Silakan masuk.", "auth.goSignin": "Ke halaman Masuk",
  "onb.name": "Siapa nama Anda?", "onb.goal": "Mengapa Anda mengambil IELTS?",
  "onb.target": "Target band Anda", "onb.startPlacement": "Mulai placement",
  "onb.goalWork": "Kerja", "onb.goalStudy": "Studi ke luar negeri", "onb.goalOther": "Lainnya",
  "results.saveCta": "Simpan hasil Anda",
  "program.choose": "Pilih program Anda",
  "home.dashboard": "Dasbor", "home.today": "Hari Ini", "home.todaySub": "Mulai sesi terpandu hari ini",
  "home.start": "Mulai", "home.yourSkills": "Skill Anda", "home.targeting": "Target",
  "home.notAssessed": "Belum dinilai", "home.milestones": "Milestone Program",
  "home.quickAccess": "Akses Cepat", "home.streak": "hari berturut",
  "home.goalDone": "Target hari ini selesai — mantap!", "home.goalTodo": "Lakukan satu tugas hari ini agar tetap lanjut.",
  "home.examCountdown": "Hitung mundur ujian", "home.daysToGo": "hari lagi", "home.examToday": "Ujian hari ini — semangat!",
  "set.dataDownload": "Unduh semua data Anda sebagai JSON", "set.export": "Ekspor",
  "set.deleteAccount": "Hapus akun & semua data", "set.delete": "Hapus",
  "set.reminder": "Pengingat belajar", "set.reminderDaily": "Pengingat email harian",
  "set.targetsOverall": "Target band keseluruhan", "set.targetsPerSkill": "Target CEFR per skill",
  "set.changePassword": "Ganti kata sandi", "set.signedIn": "Sudah masuk",
  "set.help": "Bantuan",
};

const DICT: Record<Lang, Dict> = { en: EN, id: ID };

export function getLang(): Lang {
  return localStorage.getItem(LANG_KEY) === "id" ? "id" : "en";
}

interface I18nValue {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: string) => string;
}

const I18nContext = createContext<I18nValue | null>(null);

export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [lang, setLangState] = useState<Lang>(getLang());
  const setLang = useCallback((l: Lang) => {
    localStorage.setItem(LANG_KEY, l);
    setLangState(l);
  }, []);
  const t = useCallback((key: string) => DICT[lang][key] ?? DICT.en[key] ?? key, [lang]);
  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
};

export function useT(): I18nValue {
  const ctx = useContext(I18nContext);
  // Fallback (e.g. components rendered outside the provider in tests): English.
  if (!ctx) return { lang: "en", setLang: () => {}, t: (k) => EN[k] ?? k };
  return ctx;
}
