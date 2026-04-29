import type { PropsWithChildren } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "./AuthContext";

export function AppShell({ children }: PropsWithChildren) {
  const auth = useAuth();

  return (
    <div className="app-shell">
      <header className="shell-header">
        <div>
          <p className="eyebrow">LeaseFlow browser slice</p>
          <h1 className="shell-title">Tenant-safe rent operations</h1>
        </div>
        <button className="ghost-button" onClick={auth.signOut} type="button">
          Sign out
        </button>
      </header>
      <nav className="shell-nav" aria-label="Primary">
        <NavLink
          className={({ isActive }) =>
            isActive ? "nav-link nav-link-active" : "nav-link"
          }
          to="/dashboard"
        >
          Dashboard
        </NavLink>
        <NavLink
          className={({ isActive }) =>
            isActive ? "nav-link nav-link-active" : "nav-link"
          }
          to="/properties"
        >
          Properties
        </NavLink>
        <NavLink
          className={({ isActive }) =>
            isActive ? "nav-link nav-link-active" : "nav-link"
          }
          to="/leases"
        >
          Leases
        </NavLink>
        <NavLink
          className={({ isActive }) =>
            isActive ? "nav-link nav-link-active" : "nav-link"
          }
          to="/notifications"
        >
          Notifications
        </NavLink>
      </nav>
      <main>{children}</main>
    </div>
  );
}
