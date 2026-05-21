import type { PropsWithChildren } from "react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";
import { SUPPORTED_LANGUAGES, type SupportedLanguage } from "../i18n";
import { useAuth } from "./AuthContext";

export function AppShell({ children }: PropsWithChildren) {
  const auth = useAuth();
  const { i18n, t } = useTranslation();

  function handleLanguageChange(language: SupportedLanguage) {
    void i18n.changeLanguage(language);
  }

  return (
    <div className="app-shell">
      <header className="shell-header">
        <div>
          <p className="eyebrow">{t("appShell.eyebrow")}</p>
          <h1 className="shell-title">{t("appShell.title")}</h1>
        </div>
        <div className="shell-actions">
          <div aria-label={t("appShell.languageLabel")} className="language-switcher">
            {SUPPORTED_LANGUAGES.map((language) => (
              <button
                aria-pressed={i18n.resolvedLanguage === language}
                className={
                  i18n.resolvedLanguage === language
                    ? "language-button language-button-active"
                    : "language-button"
                }
                key={language}
                onClick={() => handleLanguageChange(language)}
                type="button"
              >
                {language.toUpperCase()}
              </button>
            ))}
          </div>
          <button className="ghost-button" onClick={auth.signOut} type="button">
            {t("appShell.signOut")}
          </button>
        </div>
      </header>
      <nav className="shell-nav" aria-label={t("appShell.navLabel")}>
        <NavLink
          className={({ isActive }) =>
            isActive ? "nav-link nav-link-active" : "nav-link"
          }
          to="/dashboard"
        >
          {t("appShell.nav.dashboard")}
        </NavLink>
        <NavLink
          className={({ isActive }) =>
            isActive ? "nav-link nav-link-active" : "nav-link"
          }
          to="/properties"
        >
          {t("appShell.nav.properties")}
        </NavLink>
        <NavLink
          className={({ isActive }) =>
            isActive ? "nav-link nav-link-active" : "nav-link"
          }
          to="/leases"
        >
          {t("appShell.nav.leases")}
        </NavLink>
        <NavLink
          className={({ isActive }) =>
            isActive ? "nav-link nav-link-active" : "nav-link"
          }
          to="/notifications"
        >
          {t("appShell.nav.notifications")}
        </NavLink>
      </nav>
      <main>{children}</main>
    </div>
  );
}
