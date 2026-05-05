import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../app/AuthContext";
import {
  ApiError,
  createApiClient,
  type CreateNotificationContactInput,
  type LeaseReminderCandidate,
  type NotificationContact,
  type NotificationItem,
  UnauthorizedApiError,
  type UpdateNotificationContactInput,
} from "../../lib/api";
import { getRuntimeConfig } from "../../lib/config";

type NotificationsPageState = {
  createNotificationContact: (input: CreateNotificationContactInput) => Promise<void>;
  dueReminders: LeaseReminderCandidate[];
  error: string | null;
  isLoading: boolean;
  markNotificationRead: (notificationId: string) => Promise<void>;
  notificationContacts: NotificationContact[];
  notifications: NotificationItem[];
  readingNotificationId: string | null;
  updatingContactId: string | null;
  updateNotificationContact: (
    contactId: string,
    input: UpdateNotificationContactInput
  ) => Promise<void>;
};

export function useNotificationsPageState(): NotificationsPageState {
  const auth = useAuth();
  const navigate = useNavigate();
  const [dueReminders, setDueReminders] = useState<LeaseReminderCandidate[]>([]);
  const [notificationContacts, setNotificationContacts] = useState<NotificationContact[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [readingNotificationId, setReadingNotificationId] = useState<string | null>(null);
  const [updatingContactId, setUpdatingContactId] = useState<string | null>(null);
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
        const [remindersResponse, notificationsResponse, contactsResponse] = await Promise.all([
          client.listDueLeaseReminders(),
          client.listNotifications(),
          client.listNotificationContacts(),
        ]);
        if (!cancelled) {
          setDueReminders(remindersResponse.items);
          setNotifications(notificationsResponse.items);
          setNotificationContacts(contactsResponse.items);
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

  async function createNotificationContact(input: CreateNotificationContactInput) {
    if (!auth.session) {
      navigate("/", { replace: true });
      return;
    }

    setError(null);

    try {
      const client = createApiClient({
        config: getRuntimeConfig(),
        onUnauthorized: auth.markSessionExpired,
        session: auth.session,
      });
      const created = await client.createNotificationContact(input);
      setNotificationContacts((current) => upsertContact(current, created));
    } catch (errorValue) {
      if (errorValue instanceof UnauthorizedApiError) {
        navigate("/", { replace: true });
        return;
      }
      setError(
        errorValue instanceof ApiError
          ? errorValue.message
          : "Could not create notification contact."
      );
      throw errorValue;
    }
  }

  async function updateNotificationContact(
    contactId: string,
    input: UpdateNotificationContactInput
  ) {
    if (!auth.session) {
      navigate("/", { replace: true });
      return;
    }

    setUpdatingContactId(contactId);
    setError(null);

    try {
      const client = createApiClient({
        config: getRuntimeConfig(),
        onUnauthorized: auth.markSessionExpired,
        session: auth.session,
      });
      const updated = await client.updateNotificationContact(contactId, input);
      setNotificationContacts((current) => upsertContact(current, updated));
    } catch (errorValue) {
      if (errorValue instanceof UnauthorizedApiError) {
        navigate("/", { replace: true });
        return;
      }
      setError(
        errorValue instanceof ApiError
          ? errorValue.message
          : "Could not update notification contact."
      );
      throw errorValue;
    } finally {
      setUpdatingContactId(null);
    }
  }

  return {
    createNotificationContact,
    dueReminders,
    error,
    isLoading,
    markNotificationRead,
    notificationContacts,
    notifications,
    readingNotificationId,
    updatingContactId,
    updateNotificationContact,
  };
}

function upsertContact(
  current: NotificationContact[],
  updated: NotificationContact
): NotificationContact[] {
  const existingIndex = current.findIndex(
    (contact) => contact.contact_id === updated.contact_id
  );
  if (existingIndex === -1) {
    return [updated, ...current];
  }

  return current.map((contact) =>
    contact.contact_id === updated.contact_id ? updated : contact
  );
}
