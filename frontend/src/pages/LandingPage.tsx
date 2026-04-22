import { Navigate, useLocation } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../app/AuthContext";

export function LandingPage() {
  const auth = useAuth();
  const location = useLocation();
  const [error, setError] = useState<string | null>(null);

  if (auth.isAuthenticated) {
    return <Navigate replace to="/properties" />;
  }

  const returnPath =
    typeof location.state === "object" &&
    location.state !== null &&
    "from" in location.state &&
    typeof location.state.from === "string"
      ? location.state.from
      : "/properties";

  async function handleSignIn() {
    try {
      setError(null);
      await auth.signIn(returnPath);
    } catch (errorValue) {
      setError(errorValue instanceof Error ? errorValue.message : "Could not start sign-in.");
    }
  }

  return (
    <main className="landing-page">
      <section className="hero-card">
        <p className="eyebrow">LeaseFlow frontend MVP</p>
        <h1 className="display-title">From Hosted UI to tenant-safe CRUD.</h1>
        <p className="hero-copy">
          This browser slice talks directly to the deployed LeaseFlow API. Cognito
          signs the user in, API Gateway enforces JWT auth, and the backend derives
          tenant context from validated claims rather than request bodies.
        </p>
        <div className="hero-actions">
          <button className="primary-button" onClick={handleSignIn} type="button">
            Sign in with Cognito
          </button>
          <p className="supporting-copy">
            Local-first browser slice. Hosted deployment comes later.
          </p>
        </div>
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      <section className="hero-grid">
        <article className="info-card">
          <h2>In scope now</h2>
          <ul className="info-list">
            <li>Hosted UI sign in and sign out</li>
            <li>Properties list and create</li>
            <li>Leases list and create</li>
          </ul>
        </article>
        <article className="info-card">
          <h2>Guardrails</h2>
          <ul className="info-list">
            <li>No admin auth APIs in the browser</li>
            <li>No client-trusted tenant context</li>
            <li>No proxy server or BFF layer</li>
          </ul>
        </article>
      </section>
    </main>
  );
}
