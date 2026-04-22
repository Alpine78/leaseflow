import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LeasesPage } from "./LeasesPage";

const createLease = vi.fn();
const mockedUseLeasesPageState = vi.fn();

vi.mock("../features/leases/useLeasesPage", () => ({
  useLeasesPageState: () => mockedUseLeasesPageState(),
}));

describe("LeasesPage", () => {
  beforeEach(() => {
    createLease.mockReset();
    createLease.mockResolvedValue(undefined);
  });

  it("disables lease creation until a property exists", () => {
    mockedUseLeasesPageState.mockReturnValue({
      createLease,
      error: null,
      isLoading: false,
      isSubmitting: false,
      leases: [],
      properties: [],
    });

    render(<LeasesPage />);

    expect(screen.getByRole("button", { name: "Create lease" })).toBeDisabled();
    expect(screen.getByText(/Lease creation stays disabled/i)).toBeInTheDocument();
  });

  it("uses the selected property value when creating a lease", async () => {
    mockedUseLeasesPageState.mockReturnValue({
      createLease,
      error: null,
      isLoading: false,
      isSubmitting: false,
      leases: [],
      properties: [
        {
          address: "First street",
          created_at: "2026-04-22T08:00:00Z",
          name: "First property",
          property_id: "property-1",
          tenant_id: "tenant-a",
        },
        {
          address: "Second street",
          created_at: "2026-04-22T08:00:00Z",
          name: "Second property",
          property_id: "property-2",
          tenant_id: "tenant-a",
        },
      ],
    });

    render(<LeasesPage />);

    fireEvent.change(screen.getByLabelText("Property"), {
      target: { value: "property-2" },
    });
    fireEvent.change(screen.getByLabelText("Resident name"), {
      target: { value: "Kaisa Tenant" },
    });
    fireEvent.change(screen.getByLabelText("Rent due day"), {
      target: { value: "9" },
    });
    fireEvent.change(screen.getByLabelText("Start date"), {
      target: { value: "2026-07-01" },
    });
    fireEvent.change(screen.getByLabelText("End date"), {
      target: { value: "2026-07-31" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Create lease" }).closest("form")!);

    await waitFor(() => {
      expect(createLease).toHaveBeenCalledWith({
        end_date: "2026-07-31",
        property_id: "property-2",
        rent_due_day_of_month: 9,
        resident_name: "Kaisa Tenant",
        start_date: "2026-07-01",
      });
    });

    expect(createLease.mock.calls[0][0]).not.toHaveProperty("tenant_id");
  });
});
