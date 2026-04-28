import { Route, Routes } from "react-router-dom";
import { AppShell } from "./AppShell";
import { ProtectedRoute } from "./ProtectedRoute";
import { AuthCallbackPage } from "../pages/AuthCallbackPage";
import { LandingPage } from "../pages/LandingPage";
import { LeasesPage } from "../pages/LeasesPage";
import { NotificationsPage } from "../pages/NotificationsPage";
import { PropertiesPage } from "../pages/PropertiesPage";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route
        path="/properties"
        element={
          <ProtectedRoute>
            <AppShell>
              <PropertiesPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/leases"
        element={
          <ProtectedRoute>
            <AppShell>
              <LeasesPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/notifications"
        element={
          <ProtectedRoute>
            <AppShell>
              <NotificationsPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
