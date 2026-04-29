import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "./AuthContext";
import { App } from "./App";

vi.mock("../pages/DashboardPage", () => ({
  DashboardPage: () => <div>Dashboard page</div>,
}));

function createAuthValue(overrides: Partial<AuthContextValue> = {}): AuthContextValue {
  return {
    completeSignIn: vi.fn(),
    isAuthenticated: true,
    markSessionExpired: vi.fn(),
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

describe("App", () => {
  it("renders the protected dashboard route for authenticated users", () => {
    render(
      <AuthContext.Provider value={createAuthValue()}>
        <MemoryRouter initialEntries={["/dashboard"]}>
          <App />
        </MemoryRouter>
      </AuthContext.Provider>
    );

    expect(screen.getByText("Dashboard page")).toBeInTheDocument();
  });

  it("protects the dashboard route from unauthenticated users", () => {
    render(
      <AuthContext.Provider
        value={createAuthValue({
          isAuthenticated: false,
          session: null,
        })}
      >
        <MemoryRouter initialEntries={["/dashboard"]}>
          <App />
        </MemoryRouter>
      </AuthContext.Provider>
    );

    expect(screen.getByRole("button", { name: "Sign in with Cognito" })).toBeInTheDocument();
    expect(screen.queryByText("Dashboard page")).not.toBeInTheDocument();
  });
});
