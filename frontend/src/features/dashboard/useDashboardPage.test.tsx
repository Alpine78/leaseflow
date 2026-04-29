import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../../app/AuthContext";
import { useDashboardPageState } from "./useDashboardPage";

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

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}

function renderHookConsumer() {
  function HookConsumer() {
    const { error, isLoading, summary } = useDashboardPageState();

    if (isLoading) {
      return <p>Loading dashboard...</p>;
    }

    return (
      <div>
        {error ? <p>{error}</p> : null}
        <p>properties={summary.propertyCount}</p>
        <p>leases={summary.leaseCount}</p>
        <p>reminders={summary.dueReminderCount}</p>
        <p>unread={summary.unreadNotificationCount}</p>
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

describe("useDashboardPageState", () => {
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

  it("loads dashboard counts from existing list APIs", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ items: [{ property_id: "property-1" }] }))
      .mockResolvedValueOnce(jsonResponse({ items: [{ lease_id: "lease-1" }] }))
      .mockResolvedValueOnce(
        jsonResponse({ items: [{ lease_id: "lease-1" }, { lease_id: "lease-2" }] })
      )
      .mockResolvedValueOnce(
        jsonResponse({
          items: [
            { notification_id: "notification-1", read_at: null },
            { notification_id: "notification-2", read_at: "2026-04-28T10:00:00Z" },
          ],
        })
      );

    renderHookConsumer();

    await waitFor(() => {
      expect(screen.getByText("properties=1")).toBeInTheDocument();
    });
    expect(screen.getByText("leases=1")).toBeInTheDocument();
    expect(screen.getByText("reminders=2")).toBeInTheDocument();
    expect(screen.getByText("unread=1")).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "https://api.example.com/dev/properties",
      "https://api.example.com/dev/leases",
      "https://api.example.com/dev/lease-reminders/due-soon",
      "https://api.example.com/dev/notifications",
    ]);
  });

  it("expires the session and redirects home on unauthorized responses", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ error: "Unauthorized" }, 401))
      .mockResolvedValueOnce(jsonResponse({ error: "Unauthorized" }, 401))
      .mockResolvedValueOnce(jsonResponse({ error: "Unauthorized" }, 401))
      .mockResolvedValueOnce(jsonResponse({ error: "Unauthorized" }, 401));

    renderHookConsumer();

    await waitFor(() => {
      expect(markSessionExpired).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith("/", { replace: true });
    });
  });
});
