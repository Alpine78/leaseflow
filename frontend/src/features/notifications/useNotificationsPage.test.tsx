import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../../app/AuthContext";
import { useNotificationsPageState } from "./useNotificationsPage";

const fetchMock = vi.fn();
const navigateMock = vi.fn();
const markSessionExpired = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom"
  );
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

function createAuthValue(overrides: Partial<AuthContextValue> = {}): AuthContextValue {
  return {
    completeSignIn: vi.fn(),
    isAuthenticated: true,
    markSessionExpired,
    session: {
      accessToken: "access-token",
      expiresAt: Date.now() + 60_000,
      idToken: "id-token",
      tokenType: "Bearer",
    },
    signIn: vi.fn(),
    signOut: vi.fn(),
    ...overrides,
  };
}

function renderHookConsumer() {
  function HookConsumer() {
    const {
      dueReminders,
      error,
      isLoading,
      markNotificationRead,
      notifications,
      readingNotificationId,
    } = useNotificationsPageState();

    async function handleMarkRead(notificationId: string) {
      try {
        await markNotificationRead(notificationId);
      } catch {
        // Page submit/click handlers consume hook rethrows after error state is set.
      }
    }

    if (isLoading) {
      return <p>Loading notifications...</p>;
    }

    return (
      <div>
        {error ? <p>{error}</p> : null}
        <p>Reminders: {dueReminders.length}</p>
        {notifications.map((notification) => (
          <article key={notification.notification_id}>
            <h2>{notification.title}</h2>
            <p>{notification.read_at ?? "Unread"}</p>
            <button
              disabled={readingNotificationId === notification.notification_id}
              onClick={() => void handleMarkRead(notification.notification_id)}
              type="button"
            >
              Mark read
            </button>
          </article>
        ))}
      </div>
    );
  }

  return render(
    <AuthContext.Provider value={createAuthValue()}>
      <MemoryRouter>
        <HookConsumer />
      </MemoryRouter>
    </AuthContext.Provider>
  );
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}

describe("useNotificationsPageState", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    markSessionExpired.mockReset();
    navigateMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.com/dev");
    vi.stubEnv("VITE_COGNITO_HOSTED_UI_BASE_URL", "https://auth.example.com");
    vi.stubEnv("VITE_COGNITO_CLIENT_ID", "client-id");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("updates local notification state after mark-read succeeds", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ items: [] }))
      .mockResolvedValueOnce(
        jsonResponse({
          items: [
            {
              created_at: "2026-04-28T10:00:00Z",
              due_date: "2026-04-30",
              lease_id: "lease-1",
              message: "Rent is due soon.",
              notification_id: "notification-1",
              read_at: null,
              title: "Rent due soon",
              type: "rent_due",
            },
          ],
        })
      )
      .mockResolvedValueOnce(
        jsonResponse({
          created_at: "2026-04-28T10:00:00Z",
          due_date: "2026-04-30",
          lease_id: "lease-1",
          message: "Rent is due soon.",
          notification_id: "notification-1",
          read_at: "2026-04-28T11:00:00Z",
          title: "Rent due soon",
          type: "rent_due",
        })
      );

    renderHookConsumer();

    await screen.findByText("Rent due soon");
    fireEvent.click(screen.getByRole("button", { name: "Mark read" }));

    await waitFor(() => {
      expect(screen.getByText("2026-04-28T11:00:00Z")).toBeInTheDocument();
    });
  });

  it("preserves visible state and exposes an error when mark-read fails", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ items: [] }))
      .mockResolvedValueOnce(
        jsonResponse({
          items: [
            {
              created_at: "2026-04-28T10:00:00Z",
              due_date: "2026-04-30",
              lease_id: "lease-1",
              message: "Rent is due soon.",
              notification_id: "notification-1",
              read_at: null,
              title: "Rent due soon",
              type: "rent_due",
            },
          ],
        })
      )
      .mockResolvedValueOnce(jsonResponse({ error: "Could not mark read." }, 500));

    renderHookConsumer();

    await screen.findByText("Rent due soon");
    fireEvent.click(screen.getByRole("button", { name: "Mark read" }));

    await waitFor(() => {
      expect(screen.getByText("Could not mark read.")).toBeInTheDocument();
    });
    expect(screen.getByText("Unread")).toBeInTheDocument();
  });
});
