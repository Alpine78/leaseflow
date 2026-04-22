import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "./AuthContext";
import { ProtectedRoute } from "./ProtectedRoute";

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

describe("ProtectedRoute", () => {
  it("redirects unauthenticated users back to the landing route", () => {
    render(
      <AuthContext.Provider value={createAuthValue()}>
        <MemoryRouter initialEntries={["/properties"]}>
          <Routes>
            <Route element={<div>Landing page</div>} path="/" />
            <Route
              element={
                <ProtectedRoute>
                  <div>Secure properties</div>
                </ProtectedRoute>
              }
              path="/properties"
            />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    );

    expect(screen.getByText("Landing page")).toBeInTheDocument();
    expect(screen.queryByText("Secure properties")).not.toBeInTheDocument();
  });
});
