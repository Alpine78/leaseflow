import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../app/AuthContext";
import { AuthCallbackPage } from "./AuthCallbackPage";

function createAuthValue(overrides: Partial<AuthContextValue> = {}): AuthContextValue {
  return {
    completeSignIn: vi.fn(),
    isAuthenticated: false,
    markSessionExpired: vi.fn(),
    session: null,
    signIn: vi.fn(),
    signOut: vi.fn(),
    ...overrides,
  };
}

describe("AuthCallbackPage", () => {
  it("navigates to the return path after successful sign-in exchange", async () => {
    const authValue = createAuthValue({
      completeSignIn: vi.fn().mockResolvedValue("/leases"),
    });

    window.history.pushState({}, "", "/auth/callback?code=abc&state=123");

    render(
      <AuthContext.Provider value={authValue}>
        <MemoryRouter initialEntries={["/auth/callback?code=abc&state=123"]}>
          <Routes>
            <Route element={<AuthCallbackPage />} path="/auth/callback" />
            <Route element={<div>Leases route</div>} path="/leases" />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByText("Leases route")).toBeInTheDocument();
    });
    expect(authValue.completeSignIn).toHaveBeenCalled();
  });

  it("renders a retry message when the callback fails", async () => {
    const authValue = createAuthValue({
      completeSignIn: vi.fn().mockRejectedValue(new Error("Callback failed")),
    });

    window.history.pushState({}, "", "/auth/callback?error=access_denied");

    render(
      <AuthContext.Provider value={authValue}>
        <MemoryRouter initialEntries={["/auth/callback?error=access_denied"]}>
          <Routes>
            <Route element={<AuthCallbackPage />} path="/auth/callback" />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByText("Callback failed")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Try sign-in again" })).toBeInTheDocument();
  });
});
