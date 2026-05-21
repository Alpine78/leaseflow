import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import { en } from "./en";
import { fi } from "./fi";

export const SUPPORTED_LANGUAGES = ["en", "fi"] as const;
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

export const LOCALE_STORAGE_KEY = "leaseflow.locale";

export const DATE_LOCALES: Record<SupportedLanguage, string> = {
  en: "en-GB",
  fi: "fi-FI",
};

export function isSupportedLanguage(value: string): value is SupportedLanguage {
  return SUPPORTED_LANGUAGES.includes(value as SupportedLanguage);
}

export function readStoredLanguage(storage: Storage | undefined = window.localStorage) {
  try {
    const stored = storage?.getItem(LOCALE_STORAGE_KEY);
    return stored && isSupportedLanguage(stored) ? stored : "en";
  } catch {
    return "en";
  }
}

i18n.use(initReactI18next).init({
  fallbackLng: "en",
  interpolation: {
    escapeValue: false,
  },
  lng: readStoredLanguage(),
  react: {
    useSuspense: false,
  },
  resources: {
    en: {
      translation: en,
    },
    fi: {
      translation: fi,
    },
  },
  supportedLngs: SUPPORTED_LANGUAGES,
});

i18n.on("languageChanged", (language) => {
  if (!isSupportedLanguage(language)) {
    return;
  }

  try {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, language);
  } catch {
    // Local storage can be unavailable in restricted browser contexts.
  }
});

export function activeLanguage(): SupportedLanguage {
  return isSupportedLanguage(i18n.language) ? i18n.language : "en";
}

export function activeDateLocale() {
  return DATE_LOCALES[activeLanguage()];
}

export default i18n;
