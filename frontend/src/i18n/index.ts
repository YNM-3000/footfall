import i18next from "i18next";
import { initReactI18next } from "react-i18next";

import { en } from "./locales/en";
import { zh } from "./locales/zh";

export const SUPPORTED_LANGUAGES = [
  { code: "zh", label: "中文" },
  { code: "en", label: "English" },
] as const;

export type LanguageCode = (typeof SUPPORTED_LANGUAGES)[number]["code"];

/** Chinese unless the operator has chosen otherwise on this machine. */
export const DEFAULT_LANGUAGE: LanguageCode = "zh";
const STORAGE_KEY = "footfall.language";

const isSupported = (value: string | null): value is LanguageCode =>
  SUPPORTED_LANGUAGES.some((language) => language.code === value);

function storedLanguage(): LanguageCode {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return isSupported(stored) ? stored : DEFAULT_LANGUAGE;
  } catch {
    // Private browsing and similar can deny storage access.
    return DEFAULT_LANGUAGE;
  }
}

export function rememberLanguage(language: LanguageCode): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // A language that cannot be persisted still applies for this session.
  }
}

void i18next.use(initReactI18next).init({
  resources: {
    zh: { translation: zh },
    en: { translation: en },
  },
  lng: storedLanguage(),
  fallbackLng: DEFAULT_LANGUAGE,
  interpolation: { escapeValue: false },
});

/** Keeps `<html lang>` truthful, for screen readers and font selection. */
export function applyDocumentLanguage(language: string): void {
  document.documentElement.lang = language === "zh" ? "zh-CN" : language;
}

applyDocumentLanguage(i18next.language);
i18next.on("languageChanged", applyDocumentLanguage);

export default i18next;
