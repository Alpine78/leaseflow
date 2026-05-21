import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../app/AuthContext";

export function AuthCallbackPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function completeSignIn() {
      try {
        const returnPath = await auth.completeSignIn(window.location.href);
        if (!cancelled) {
          navigate(returnPath, { replace: true });
        }
      } catch (errorValue) {
        if (!cancelled) {
          setError(
            errorValue instanceof Error
              ? errorValue.message
              : t("authCallback.fallbackError")
          );
        }
      }
    }

    void completeSignIn();

    return () => {
      cancelled = true;
    };
  }, [auth, navigate, t]);

  return (
    <main className="callback-page">
      <section className="callback-card">
        <p className="eyebrow">{t("authCallback.eyebrow")}</p>
        <h1 className="section-title">{t("authCallback.title")}</h1>
        {error ? (
          <>
            <p className="error-text">{error}</p>
            <button
              className="primary-button"
              onClick={() => auth.signIn("/dashboard")}
              type="button"
            >
              {t("authCallback.retry")}
            </button>
          </>
        ) : (
          <p className="supporting-copy">{t("authCallback.supportingCopy")}</p>
        )}
      </section>
    </main>
  );
}
