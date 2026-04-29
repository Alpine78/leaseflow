import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DashboardPage } from "./DashboardPage";

const mockedUseDashboardPageState = vi.fn();

vi.mock("../features/dashboard/useDashboardPage", () => ({
  useDashboardPageState: () => mockedUseDashboardPageState(),
}));

describe("DashboardPage", () => {
  beforeEach(() => {
    mockedUseDashboardPageState.mockReset();
    mockedUseDashboardPageState.mockReturnValue({
      error: null,
      isLoading: false,
      summary: {
        dueReminderCount: 0,
        leaseCount: 0,
        propertyCount: 0,
        unreadNotificationCount: 0,
      },
    });
  });

  it("renders empty summary counts and action links", () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(screen.getByText("Portfolio overview")).toBeInTheDocument();
    expect(screen.getByText("0 properties")).toBeInTheDocument();
    expect(screen.getByText("0 leases")).toBeInTheDocument();
    expect(screen.getByText("0 due soon")).toBeInTheDocument();
    expect(screen.getByText("0 unread")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Manage properties" })).toHaveAttribute(
      "href",
      "/properties"
    );
    expect(screen.getByRole("link", { name: "Manage leases" })).toHaveAttribute(
      "href",
      "/leases"
    );
    expect(screen.getByRole("link", { name: "Review notifications" })).toHaveAttribute(
      "href",
      "/notifications"
    );
  });

  it("renders populated summary counts", () => {
    mockedUseDashboardPageState.mockReturnValue({
      error: null,
      isLoading: false,
      summary: {
        dueReminderCount: 2,
        leaseCount: 4,
        propertyCount: 3,
        unreadNotificationCount: 1,
      },
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(screen.getByText("3 properties")).toBeInTheDocument();
    expect(screen.getByText("4 leases")).toBeInTheDocument();
    expect(screen.getByText("2 due soon")).toBeInTheDocument();
    expect(screen.getByText("1 unread")).toBeInTheDocument();
  });

  it("renders the existing error message path", () => {
    mockedUseDashboardPageState.mockReturnValue({
      error: "Could not load dashboard.",
      isLoading: false,
      summary: {
        dueReminderCount: 0,
        leaseCount: 0,
        propertyCount: 0,
        unreadNotificationCount: 0,
      },
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(screen.getByText("Could not load dashboard.")).toBeInTheDocument();
  });
});
