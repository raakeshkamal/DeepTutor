import i18n, { type Resource } from "i18next";
import { initReactI18next } from "react-i18next";

import enApp from "@/locales/en/app.json";
import { normalizeLanguage, type AppLanguage } from "./languages";

export { APP_LANGUAGES, isAppLanguage, normalizeLanguage } from "./languages";
export type { AppLanguage } from "./languages";

let _initialized = false;

export function initI18n(language?: unknown) {
  if (_initialized) return i18n;

  // Mastery-only cleanup: English is the only shipped locale. No lazy bundles,
  // no Chinese fallback, no per-language resource loading.
  const resources: Resource = {
    en: { app: enApp },
  };

  i18n.use(initReactI18next).init({
    resources,
    lng: "en",
    fallbackLng: "en",
    defaultNS: "app",
    ns: ["app"],
    keySeparator: false,
    nsSeparator: false,
    interpolation: { escapeValue: false },
    returnEmptyString: false,
    returnNull: false,
  });

  void normalizeLanguage(language);
  _initialized = true;
  return i18n;
}

export async function ensureLanguage(_language: AppLanguage) {
  // English is already loaded at init; there is nothing left to fetch.
  return;
}
