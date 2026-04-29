import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../app/AuthContext";
import { LandingPage } from "./LandingPage";

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

describe("LandingPage", () => {
  it("redirects authenticated users to the dashboard", () => {
    render(
      <AuthContext.Provider value={createAuthValue({ isAuthenticated: true })}>
        <MemoryRouter initialEntries={["/"]}>
          <Routes>
            <Route element={<LandingPage />} path="/" />
            <Route element={<div>Dashboard route</div>} path="/dashboard" />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    );

    expect(screen.getByText("Dashboard route")).toBeInTheDocument();
  });

  it("starts sign-in with the dashboard as the default return path", () => {
    const authValue = createAuthValue();

    render(
      <AuthContext.Provider value={authValue}>
        <MemoryRouter>
          <LandingPage />
        </MemoryRouter>
      </AuthContext.Provider>
    );

    fireEvent.click(screen.getByRole("button", { name: "Sign in with Cognito" }));

    expect(authValue.signIn).toHaveBeenCalledWith("/dashboard");
  });
});
