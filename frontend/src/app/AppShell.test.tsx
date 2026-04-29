import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "./AuthContext";
import { AppShell } from "./AppShell";

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

describe("AppShell", () => {
  it("shows dashboard and feature routes in authenticated navigation", () => {
    render(
      <AuthContext.Provider value={createAuthValue()}>
        <MemoryRouter>
          <AppShell>
            <div>Secure content</div>
          </AppShell>
        </MemoryRouter>
      </AuthContext.Provider>
    );

    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute(
      "href",
      "/dashboard"
    );
    expect(screen.getByRole("link", { name: "Properties" })).toHaveAttribute(
      "href",
      "/properties"
    );
    expect(screen.getByRole("link", { name: "Leases" })).toHaveAttribute(
      "href",
      "/leases"
    );
    expect(screen.getByRole("link", { name: "Notifications" })).toHaveAttribute(
      "href",
      "/notifications"
    );
  });
});
