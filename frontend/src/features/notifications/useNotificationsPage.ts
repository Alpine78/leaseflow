import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../app/AuthContext";
import {
  ApiError,
  createApiClient,
  type LeaseReminderCandidate,
  type NotificationItem,
  UnauthorizedApiError,
} from "../../lib/api";
import { getRuntimeConfig } from "../../lib/config";

type NotificationsPageState = {
  dueReminders: LeaseReminderCandidate[];
  error: string | null;
  isLoading: boolean;
  markNotificationRead: (notificationId: string) => Promise<void>;
  notifications: NotificationItem[];
  readingNotificationId: string | null;
};

export function useNotificationsPageState(): NotificationsPageState {
  const auth = useAuth();
  const navigate = useNavigate();
  const [dueReminders, setDueReminders] = useState<LeaseReminderCandidate[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [readingNotificationId, setReadingNotificationId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadPageData() {
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
        const [remindersResponse, notificationsResponse] = await Promise.all([
          client.listDueLeaseReminders(),
          client.listNotifications(),
        ]);
        if (!cancelled) {
          setDueReminders(remindersResponse.items);
          setNotifications(notificationsResponse.items);
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
            : "Could not load notifications."
        );
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadPageData();

    return () => {
      cancelled = true;
    };
  }, [auth.markSessionExpired, auth.session, navigate]);

  async function markNotificationRead(notificationId: string) {
    if (!auth.session) {
      navigate("/", { replace: true });
      return;
    }

    setReadingNotificationId(notificationId);
    setError(null);

    try {
      const client = createApiClient({
        config: getRuntimeConfig(),
        onUnauthorized: auth.markSessionExpired,
        session: auth.session,
      });
      const updated = await client.markNotificationRead(notificationId);
      setNotifications((current) =>
        current.map((notification) =>
          notification.notification_id === updated.notification_id
            ? updated
            : notification
        )
      );
    } catch (errorValue) {
      if (errorValue instanceof UnauthorizedApiError) {
        navigate("/", { replace: true });
        return;
      }
      setError(
        errorValue instanceof ApiError
          ? errorValue.message
          : "Could not mark notification as read."
      );
      throw errorValue;
    } finally {
      setReadingNotificationId(null);
    }
  }

  return {
    dueReminders,
    error,
    isLoading,
    markNotificationRead,
    notifications,
    readingNotificationId,
  };
}
