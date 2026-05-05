import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createApiClient } from "./api";

const fetchMock = vi.fn();

const clientOptions = {
  config: {
    apiBaseUrl: "https://api.example.com/dev/",
    cognitoClientId: "client-id",
    cognitoHostedUiBaseUrl: "https://auth.example.com",
  },
  onUnauthorized: vi.fn(),
  session: {
    accessToken: "access-token",
    expiresAt: Date.now() + 60_000,
    idToken: "id-token",
    tokenType: "Bearer",
  },
};

describe("createApiClient", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        headers: { "Content-Type": "application/json" },
        status: 200,
      })
    );
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("patches a property without tenant_id", async () => {
    const client = createApiClient(clientOptions);

    await client.updateProperty("property-1", {
      address: "Updated Street 2",
      name: "Updated HQ",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/dev/properties/property-1",
      expect.objectContaining({
        method: "PATCH",
      })
    );

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers).toMatchObject({
      Authorization: "Bearer id-token",
      "Content-Type": "application/json",
    });
    expect(JSON.parse(String(init.body))).toEqual({
      address: "Updated Street 2",
      name: "Updated HQ",
    });
    expect(JSON.parse(String(init.body))).not.toHaveProperty("tenant_id");
  });

  it("patches a lease without tenant_id or property_id", async () => {
    const client = createApiClient(clientOptions);

    await client.updateLease("lease-1", {
      end_date: "2026-12-31",
      rent_due_day_of_month: 9,
      resident_name: "Updated Resident",
      start_date: "2026-06-01",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/dev/leases/lease-1",
      expect.objectContaining({
        method: "PATCH",
      })
    );

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers).toMatchObject({
      Authorization: "Bearer id-token",
      "Content-Type": "application/json",
    });
    expect(JSON.parse(String(init.body))).toEqual({
      end_date: "2026-12-31",
      rent_due_day_of_month: 9,
      resident_name: "Updated Resident",
      start_date: "2026-06-01",
    });
    expect(JSON.parse(String(init.body))).not.toHaveProperty("tenant_id");
    expect(JSON.parse(String(init.body))).not.toHaveProperty("property_id");
  });

  it("lists due lease reminders without tenant query params", async () => {
    const client = createApiClient(clientOptions);

    await client.listDueLeaseReminders();

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/dev/lease-reminders/due-soon",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer id-token",
        }),
      })
    );
  });

  it("lists notifications", async () => {
    const client = createApiClient(clientOptions);

    await client.listNotifications();

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/dev/notifications",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer id-token",
        }),
      })
    );
  });

  it("marks a notification read without tenant_id or request body", async () => {
    const client = createApiClient(clientOptions);

    await client.markNotificationRead("notification-1");

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/dev/notifications/notification-1/read",
      expect.objectContaining({
        method: "PATCH",
      })
    );

    const [, init] = fetchMock.mock.calls[0];
    expect(init.body).toBeUndefined();
  });

  it("lists notification contacts without tenant query params", async () => {
    const client = createApiClient(clientOptions);

    await client.listNotificationContacts();

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/dev/notification-contacts",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer id-token",
        }),
      })
    );
  });

  it("creates a notification contact without tenant_id", async () => {
    const client = createApiClient(clientOptions);

    await client.createNotificationContact({ email: "ops@example.test" });

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/dev/notification-contacts",
      expect.objectContaining({
        method: "POST",
      })
    );

    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(String(init.body))).toEqual({ email: "ops@example.test" });
    expect(JSON.parse(String(init.body))).not.toHaveProperty("tenant_id");
  });

  it("updates a notification contact without tenant_id", async () => {
    const client = createApiClient(clientOptions);

    await client.updateNotificationContact("contact-1", { enabled: false });

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/dev/notification-contacts/contact-1",
      expect.objectContaining({
        method: "PATCH",
      })
    );

    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(String(init.body))).toEqual({ enabled: false });
    expect(JSON.parse(String(init.body))).not.toHaveProperty("tenant_id");
  });
});
