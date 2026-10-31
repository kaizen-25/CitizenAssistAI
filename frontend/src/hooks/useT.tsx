import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { setApiLanguage } from "../api/client";
import en from "../i18n/en.json";
import hi from "../i18n/hi.json";

export type Language = "en" | "hi";
export type StringKey = Exclude<keyof typeof en, "_reviewed">;
type Vars = Record<string, string | number>;

const STRINGS: Record<Language, Record<string, string | boolean>> = { en, hi };
const STORAGE_KEY = "citizenassist.language";

function readStoredLanguage(): Language {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === "hi" ? stored : "en";
  } catch {
    return "en";
  }
}

interface I18n {
  lang: Language;
  setLang: (lang: Language) => void;
  t: (key: StringKey, vars?: Vars) => string;
}

const I18nContext = createContext<I18n | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Language>(readStoredLanguage);

  setApiLanguage(lang);

  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch {
      // The choice simply lasts for this page view.
    }
  }, [lang]);

  const value = useMemo<I18n>(
    () => ({
      lang,
      setLang,
      t: (key, vars = {}) => {
        const text = (STRINGS[lang][key] as string) || en[key];
        return text.replace(/\{(\w+)\}/g, (match, name) => String(vars[name] ?? match));
      },
    }),
    [lang],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useT(): I18n {
  const i18n = useContext(I18nContext);
  if (!i18n) throw new Error("useT must be used inside I18nProvider");
  return i18n;
}
