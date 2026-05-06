import type { StoredAuthSession } from "./auth";
import type { RuntimeConfig } from "./config";

export type Property = {
  address: string;
  created_at: string;
  name: string;
  property_id: string;
  tenant_id: string;
};

export type Lease = {
  created_at: string;
  end_date: string;
  lease_id: string;
  property_id: string;
  rent_due_day_of_month: number | null;
  resident_name: string;
  start_date: string;
  tenant_id: string;
};

export type LeaseReminderCandidate = {
  days_until_due: number;
  due_date: string;
  lease_id: string;
  property_id: string;
  rent_due_day_of_month: number;
  resident_name: string;
};

export type NotificationItem = {
  created_at: string;
  delivery_summary?: NotificationEmailDeliverySummary;
  due_date: string;
  lease_id: string;
  message: string;
  notification_id: string;
  read_at: string | null;
  title: string;
  type: string;
};

export type NotificationEmailDeliverySummary = {
  failed_count: number;
  last_error_code: string | null;
  latest_attempt_at: string | null;
  latest_sent_at: string | null;
  pending_count: number;
  sent_count: number;
  total_count: number;
};

export type NotificationContact = {
  contact_id: string;
  created_at: string;
  email: string;
  enabled: boolean;
};

export type CreatePropertyInput = {
  address: string;
  name: string;
};

export type CreateLeaseInput = {
  end_date: string;
  property_id: string;
  rent_due_day_of_month: number;
  resident_name: string;
  start_date: string;
};

export type UpdatePropertyInput = CreatePropertyInput;

export type UpdateLeaseInput = {
  end_date: string;
  rent_due_day_of_month: number;
  resident_name: string;
  start_date: string;
};

export type CreateNotificationContactInput = {
  email: string;
};

export type UpdateNotificationContactInput = {
  enabled: boolean;
};

type ListResponse<T> = {
  items: T[];
};

type ApiClientOptions = {
  config: RuntimeConfig;
  onUnauthorized: () => void;
  session: StoredAuthSession;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode: number
  ) {
    super(message);
  }
}

export class UnauthorizedApiError extends ApiError {}

function normalizeBaseUrl(url: string) {
  return url.replace(/\/+$/g, "");
}

async function parseResponseBody(response: Response) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return null;
  }
  return response.json();
}

export function createApiClient({ config, onUnauthorized, session }: ApiClientOptions) {
  async function request<T>(path: string, init?: RequestInit) {
    const response = await fetch(`${normalizeBaseUrl(config.apiBaseUrl)}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${session.idToken}`,
        "Content-Type": "application/json",
        ...(init?.headers || {}),
      },
    });

    const body = (await parseResponseBody(response)) as (Record<string, unknown> | null);

    if (response.status === 401 || response.status === 403) {
      onUnauthorized();
      throw new UnauthorizedApiError(
        "The browser session is no longer authorized. Please sign in again.",
        response.status
      );
    }

    if (!response.ok) {
      throw new ApiError(
        String(body?.error || `Request failed with status ${response.status}.`),
        response.status
      );
    }

    return body as T;
  }

  return {
    createLease(input: CreateLeaseInput) {
      return request<Lease>("/leases", {
        body: JSON.stringify(input),
        method: "POST",
      });
    },
    createNotificationContact(input: CreateNotificationContactInput) {
      return request<NotificationContact>("/notification-contacts", {
        body: JSON.stringify(input),
        method: "POST",
      });
    },
    createProperty(input: CreatePropertyInput) {
      return request<Property>("/properties", {
        body: JSON.stringify(input),
        method: "POST",
      });
    },
    listDueLeaseReminders() {
      return request<ListResponse<LeaseReminderCandidate>>("/lease-reminders/due-soon");
    },
    listLeases() {
      return request<ListResponse<Lease>>("/leases");
    },
    listNotifications() {
      return request<ListResponse<NotificationItem>>("/notifications");
    },
    listNotificationContacts() {
      return request<ListResponse<NotificationContact>>("/notification-contacts");
    },
    listProperties() {
      return request<ListResponse<Property>>("/properties");
    },
    markNotificationRead(notificationId: string) {
      return request<NotificationItem>(
        `/notifications/${encodeURIComponent(notificationId)}/read`,
        {
          method: "PATCH",
        }
      );
    },
    updateLease(leaseId: string, input: UpdateLeaseInput) {
      return request<Lease>(`/leases/${encodeURIComponent(leaseId)}`, {
        body: JSON.stringify(input),
        method: "PATCH",
      });
    },
    updateNotificationContact(contactId: string, input: UpdateNotificationContactInput) {
      return request<NotificationContact>(
        `/notification-contacts/${encodeURIComponent(contactId)}`,
        {
          body: JSON.stringify(input),
          method: "PATCH",
        }
      );
    },
    updateProperty(propertyId: string, input: UpdatePropertyInput) {
      return request<Property>(`/properties/${encodeURIComponent(propertyId)}`, {
        body: JSON.stringify(input),
        method: "PATCH",
      });
    },
  };
}
