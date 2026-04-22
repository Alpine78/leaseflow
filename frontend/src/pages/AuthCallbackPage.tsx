import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../app/AuthContext";

export function AuthCallbackPage() {
  const auth = useAuth();
  const navigate = useNavigate();
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
              : "Could not complete browser sign-in."
          );
        }
      }
    }

    void completeSignIn();

    return () => {
      cancelled = true;
    };
  }, [auth, navigate]);

  return (
    <main className="callback-page">
      <section className="callback-card">
        <p className="eyebrow">Completing sign-in</p>
        <h1 className="section-title">Handing the browser session back to LeaseFlow.</h1>
        {error ? (
          <>
            <p className="error-text">{error}</p>
            <button
              className="primary-button"
              onClick={() => auth.signIn("/properties")}
              type="button"
            >
              Try sign-in again
            </button>
          </>
        ) : (
          <p className="supporting-copy">Exchanging the authorization code with Cognito.</p>
        )}
      </section>
    </main>
  );
}
