import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../app/AuthContext";
import { ApiError, createApiClient, UnauthorizedApiError } from "../../lib/api";
import { getRuntimeConfig } from "../../lib/config";

type DashboardSummary = {
  dueReminderCount: number;
  leaseCount: number;
  propertyCount: number;
  unreadNotificationCount: number;
};

type DashboardPageState = {
  error: string | null;
  isLoading: boolean;
  summary: DashboardSummary;
};

const EMPTY_SUMMARY: DashboardSummary = {
  dueReminderCount: 0,
  leaseCount: 0,
  propertyCount: 0,
  unreadNotificationCount: 0,
};

export function useDashboardPageState(): DashboardPageState {
  const auth = useAuth();
  const navigate = useNavigate();
  const [summary, setSummary] = useState<DashboardSummary>(EMPTY_SUMMARY);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      if (!auth.session) {
        return;
      }

      try {
        setIsLoading(true);
        setError(null);
        const client = createApiClient({
          config: getRuntimeConfig(),
          onUnauthorized: auth.markSessionExpired,
          session: auth.session,
        });
        const [properties, leases, dueReminders, notifications] = await Promise.all([
          client.listProperties(),
          client.listLeases(),
          client.listDueLeaseReminders(),
          client.listNotifications(),
        ]);

        if (!cancelled) {
          setSummary({
            dueReminderCount: dueReminders.items.length,
            leaseCount: leases.items.length,
            propertyCount: properties.items.length,
            unreadNotificationCount: notifications.items.filter(
              (notification) => notification.read_at === null
            ).length,
          });
        }
      } catch (errorValue) {
        if (cancelled) {
          return;
        }
        if (errorValue instanceof UnauthorizedApiError) {
          navigate("/", { replace: true });
          return;
        }
        setError(
          errorValue instanceof ApiError
            ? errorValue.message
            : "Could not load dashboard."
        );
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadDashboard();

    return () => {
      cancelled = true;
    };
  }, [auth.markSessionExpired, auth.session, navigate]);

  return {
    error,
    isLoading,
    summary,
  };
}
