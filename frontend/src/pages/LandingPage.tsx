import { Navigate, useLocation } from "react-router-dom";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../app/AuthContext";

export function LandingPage() {
  const auth = useAuth();
  const location = useLocation();
  const { t } = useTranslation();
  const [error, setError] = useState<string | null>(null);

  if (auth.isAuthenticated) {
    return <Navigate replace to="/dashboard" />;
  }

  const returnPath =
    typeof location.state === "object" &&
    location.state !== null &&
    "from" in location.state &&
    typeof location.state.from === "string"
      ? location.state.from
      : "/dashboard";

  async function handleSignIn() {
    try {
      setError(null);
      await auth.signIn(returnPath);
    } catch (errorValue) {
      setError(errorValue instanceof Error ? errorValue.message : t("landing.error"));
    }
  }

  return (
    <main className="landing-page">
      <section className="hero-card">
        <p className="eyebrow">{t("landing.eyebrow")}</p>
        <h1 className="display-title">{t("landing.title")}</h1>
        <p className="hero-copy">{t("landing.heroCopy")}</p>
        <div className="hero-actions">
          <button className="primary-button" onClick={handleSignIn} type="button">
            {t("landing.signIn")}
          </button>
          <p className="supporting-copy">{t("landing.supportingCopy")}</p>
        </div>
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      <section className="hero-grid">
        <article className="info-card">
          <h2>{t("landing.inScope.title")}</h2>
          <ul className="info-list">
            <li>{t("landing.inScope.item1")}</li>
            <li>{t("landing.inScope.item2")}</li>
            <li>{t("landing.inScope.item3")}</li>
            <li>{t("landing.inScope.item4")}</li>
          </ul>
        </article>
        <article className="info-card">
          <h2>{t("landing.guardrails.title")}</h2>
          <ul className="info-list">
            <li>{t("landing.guardrails.item1")}</li>
            <li>{t("landing.guardrails.item2")}</li>
            <li>{t("landing.guardrails.item3")}</li>
          </ul>
        </article>
      </section>
    </main>
  );
}
