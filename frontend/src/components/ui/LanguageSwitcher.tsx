import { useTranslation } from "react-i18next";

import { SUPPORTED_LANGUAGES, rememberLanguage, type LanguageCode } from "../../i18n";
import "./language-switcher.css";

export function LanguageSwitcher() {
  const { t, i18n } = useTranslation();
  const active = i18n.language as LanguageCode;

  const select = (code: LanguageCode) => {
    rememberLanguage(code);
    void i18n.changeLanguage(code);
  };

  return (
    <div className="language" role="group" aria-label={t("app.language")}>
      {SUPPORTED_LANGUAGES.map((language) => (
        <button
          key={language.code}
          type="button"
          className={`language__option${language.code === active ? " language__option--active" : ""}`}
          aria-pressed={language.code === active}
          lang={language.code}
          onClick={() => select(language.code)}
        >
          {language.label}
        </button>
      ))}
    </div>
  );
}
