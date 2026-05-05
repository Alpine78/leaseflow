import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NotificationsPage } from "./NotificationsPage";

const markNotificationRead = vi.fn();
const mockedUseNotificationsPageState = vi.fn();

vi.mock("../features/notifications/useNotificationsPage", () => ({
  useNotificationsPageState: () => mockedUseNotificationsPageState(),
}));

describe("NotificationsPage", () => {
  beforeEach(() => {
    markNotificationRead.mockReset();
    markNotificationRead.mockResolvedValue(undefined);
    mockedUseNotificationsPageState.mockReset();
    mockedUseNotificationsPageState.mockReturnValue({
      createNotificationContact: vi.fn(),
      dueReminders: [],
      error: null,
      isLoading: false,
      markNotificationRead,
      notificationContacts: [],
      notifications: [],
      readingNotificationId: null,
      updatingContactId: null,
      updateNotificationContact: vi.fn(),
    });
  });

  it("renders the due reminder empty state", () => {
    render(<NotificationsPage />);

    expect(screen.getByText("No rent due soon")).toBeInTheDocument();
  });

  it("renders due reminder candidates", () => {
    mockedUseNotificationsPageState.mockReturnValue({
      dueReminders: [
        {
          days_until_due: 2,
          due_date: "2026-04-30",
          lease_id: "lease-1",
          property_id: "property-1",
          rent_due_day_of_month: 30,
          resident_name: "Kaisa Tenant",
        },
      ],
      error: null,
      isLoading: false,
      markNotificationRead,
      notificationContacts: [],
      notifications: [],
      readingNotificationId: null,
      updatingContactId: null,
      updateNotificationContact: vi.fn(),
    });

    render(<NotificationsPage />);

    expect(screen.getByText("Kaisa Tenant")).toBeInTheDocument();
    expect(screen.getByText("Due 2026-04-30 | 2 days from now")).toBeInTheDocument();
    expect(screen.getByText("rent due day 30")).toBeInTheDocument();
  });

  it("renders the notification empty state", () => {
    render(<NotificationsPage />);

    expect(screen.getByText("No persisted notifications yet")).toBeInTheDocument();
  });

  it("renders unread notifications with a mark-read action", async () => {
    mockedUseNotificationsPageState.mockReturnValue({
      dueReminders: [],
      error: null,
      isLoading: false,
      markNotificationRead,
      notificationContacts: [],
      notifications: [
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
      readingNotificationId: null,
      updatingContactId: null,
      updateNotificationContact: vi.fn(),
    });

    render(<NotificationsPage />);

    expect(screen.getByText("Rent due soon")).toBeInTheDocument();
    expect(screen.getByText("Unread")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Mark Rent due soon read" }));

    await waitFor(() => {
      expect(markNotificationRead).toHaveBeenCalledWith("notification-1");
    });
  });

  it("renders read notifications without a mark-read action", () => {
    mockedUseNotificationsPageState.mockReturnValue({
      dueReminders: [],
      error: null,
      isLoading: false,
      markNotificationRead,
      notificationContacts: [],
      notifications: [
        {
          created_at: "2026-04-28T10:00:00Z",
          due_date: "2026-04-30",
          lease_id: "lease-1",
          message: "Rent is due soon.",
          notification_id: "notification-1",
          read_at: "2026-04-28T11:00:00Z",
          title: "Rent due soon",
          type: "rent_due",
        },
      ],
      readingNotificationId: null,
      updatingContactId: null,
      updateNotificationContact: vi.fn(),
    });

    render(<NotificationsPage />);

    expect(screen.getByText("Read")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Mark Rent due soon read/i })).not.toBeInTheDocument();
  });

  it("preserves visible notification state when mark-read fails", async () => {
    markNotificationRead.mockRejectedValue(new Error("Mark read failed"));
    mockedUseNotificationsPageState.mockReturnValue({
      dueReminders: [],
      error: "Could not mark notification as read.",
      isLoading: false,
      markNotificationRead,
      notificationContacts: [],
      notifications: [
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
      readingNotificationId: null,
      updatingContactId: null,
      updateNotificationContact: vi.fn(),
    });

    render(<NotificationsPage />);
    fireEvent.click(screen.getByRole("button", { name: "Mark Rent due soon read" }));

    await waitFor(() => {
      expect(markNotificationRead).toHaveBeenCalledTimes(1);
    });

    expect(screen.getByText("Rent due soon")).toBeInTheDocument();
    expect(screen.getByText("Unread")).toBeInTheDocument();
    expect(screen.getByText("Could not mark notification as read.")).toBeInTheDocument();
  });

  it("renders the notification contact empty state", () => {
    render(<NotificationsPage />);

    expect(screen.getByText("No notification contacts yet")).toBeInTheDocument();
  });

  it("renders enabled and disabled notification contacts with actions", () => {
    mockedUseNotificationsPageState.mockReturnValue({
      createNotificationContact: vi.fn(),
      dueReminders: [],
      error: null,
      isLoading: false,
      markNotificationRead,
      notificationContacts: [
        {
          contact_id: "contact-1",
          created_at: "2026-05-05T10:00:00Z",
          email: "enabled@example.test",
          enabled: true,
        },
        {
          contact_id: "contact-2",
          created_at: "2026-05-05T11:00:00Z",
          email: "disabled@example.test",
          enabled: false,
        },
      ],
      notifications: [],
      readingNotificationId: null,
      updatingContactId: null,
      updateNotificationContact: vi.fn(),
    });

    render(<NotificationsPage />);

    expect(screen.getByText("enabled@example.test")).toBeInTheDocument();
    expect(screen.getByText("disabled@example.test")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Disable enabled@example.test" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enable disabled@example.test" })).toBeInTheDocument();
  });

  it("submits a new notification contact and clears the input on success", async () => {
    const createNotificationContact = vi.fn().mockResolvedValue(undefined);
    mockedUseNotificationsPageState.mockReturnValue({
      createNotificationContact,
      dueReminders: [],
      error: null,
      isLoading: false,
      markNotificationRead,
      notificationContacts: [],
      notifications: [],
      readingNotificationId: null,
      updatingContactId: null,
      updateNotificationContact: vi.fn(),
    });

    render(<NotificationsPage />);

    const input = screen.getByLabelText("Contact email");
    fireEvent.change(input, { target: { value: "ops@example.test" } });
    fireEvent.click(screen.getByRole("button", { name: "Add contact" }));

    await waitFor(() => {
      expect(createNotificationContact).toHaveBeenCalledWith({
        email: "ops@example.test",
      });
    });
    expect(input).toHaveValue("");
  });

  it("preserves contact email input when create fails", async () => {
    const createNotificationContact = vi.fn().mockRejectedValue(new Error("Create failed"));
    mockedUseNotificationsPageState.mockReturnValue({
      createNotificationContact,
      dueReminders: [],
      error: "Could not create notification contact.",
      isLoading: false,
      markNotificationRead,
      notificationContacts: [],
      notifications: [],
      readingNotificationId: null,
      updatingContactId: null,
      updateNotificationContact: vi.fn(),
    });

    render(<NotificationsPage />);

    const input = screen.getByLabelText("Contact email");
    fireEvent.change(input, { target: { value: "ops@example.test" } });
    fireEvent.click(screen.getByRole("button", { name: "Add contact" }));

    await waitFor(() => {
      expect(createNotificationContact).toHaveBeenCalledTimes(1);
    });
    expect(input).toHaveValue("ops@example.test");
    expect(screen.getByText("Could not create notification contact.")).toBeInTheDocument();
  });

  it("toggles a notification contact enabled state", async () => {
    const updateNotificationContact = vi.fn().mockResolvedValue(undefined);
    mockedUseNotificationsPageState.mockReturnValue({
      createNotificationContact: vi.fn(),
      dueReminders: [],
      error: null,
      isLoading: false,
      markNotificationRead,
      notificationContacts: [
        {
          contact_id: "contact-1",
          created_at: "2026-05-05T10:00:00Z",
          email: "enabled@example.test",
          enabled: true,
        },
      ],
      notifications: [],
      readingNotificationId: null,
      updatingContactId: null,
      updateNotificationContact,
    });

    render(<NotificationsPage />);
    fireEvent.click(screen.getByRole("button", { name: "Disable enabled@example.test" }));

    await waitFor(() => {
      expect(updateNotificationContact).toHaveBeenCalledWith("contact-1", {
        enabled: false,
      });
    });
  });
});
