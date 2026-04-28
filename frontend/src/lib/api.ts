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
    createProperty(input: CreatePropertyInput) {
      return request<Property>("/properties", {
        body: JSON.stringify(input),
        method: "POST",
      });
    },
    listLeases() {
      return request<ListResponse<Lease>>("/leases");
    },
    listProperties() {
      return request<ListResponse<Property>>("/properties");
    },
    updateLease(leaseId: string, input: UpdateLeaseInput) {
      return request<Lease>(`/leases/${encodeURIComponent(leaseId)}`, {
        body: JSON.stringify(input),
        method: "PATCH",
      });
    },
    updateProperty(propertyId: string, input: UpdatePropertyInput) {
      return request<Property>(`/properties/${encodeURIComponent(propertyId)}`, {
        body: JSON.stringify(input),
        method: "PATCH",
      });
    },
  };
}
