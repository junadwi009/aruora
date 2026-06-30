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
  "nav.settings": "Settings", "nav.practice": "Practice",
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
};

const ID: Dict = {
  "nav.home": "Beranda", "nav.reading": "Membaca", "nav.listening": "Menyimak",
  "nav.speaking": "Berbicara", "nav.writing": "Menulis", "nav.pronounce": "Pelafalan",
  "nav.vocab": "Kosakata", "nav.test": "Ujian", "nav.tips": "Tips", "nav.progress": "Kemajuan",
  "nav.settings": "Pengaturan",
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
