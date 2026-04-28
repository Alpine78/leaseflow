import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PropertiesPage } from "./PropertiesPage";

const createProperty = vi.fn();
const updateProperty = vi.fn();
const mockedUsePropertiesPageState = vi.fn();

vi.mock("../features/properties/usePropertiesPage", () => ({
  usePropertiesPageState: () => mockedUsePropertiesPageState(),
}));

describe("PropertiesPage", () => {
  beforeEach(() => {
    createProperty.mockReset();
    createProperty.mockResolvedValue(undefined);
    updateProperty.mockReset();
    updateProperty.mockResolvedValue(undefined);
    mockedUsePropertiesPageState.mockReset();
    mockedUsePropertiesPageState.mockReturnValue({
      createProperty,
      error: null,
      isLoading: false,
      isSubmitting: false,
      properties: [],
      updateProperty,
    });
  });

  it("submits a property payload without tenant_id", async () => {
    render(<PropertiesPage />);

    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "North Yard Block A" },
    });
    fireEvent.change(screen.getByLabelText("Address"), {
      target: { value: "Fjordinkatu 12, Helsinki" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Create property" }).closest("form")!);

    await waitFor(() => {
      expect(createProperty).toHaveBeenCalledWith({
        address: "Fjordinkatu 12, Helsinki",
        name: "North Yard Block A",
      });
    });

    expect(createProperty.mock.calls[0][0]).not.toHaveProperty("tenant_id");
  });

  it("keeps form values when property creation fails", async () => {
    createProperty.mockRejectedValue(new Error("Create failed"));

    render(<PropertiesPage />);

    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "North Yard Block A" },
    });
    fireEvent.change(screen.getByLabelText("Address"), {
      target: { value: "Fjordinkatu 12, Helsinki" },
    });

    fireEvent.submit(screen.getByRole("button", { name: "Create property" }).closest("form")!);

    await waitFor(() => {
      expect(createProperty).toHaveBeenCalledTimes(1);
    });

    expect(screen.getByLabelText("Name")).toHaveValue("North Yard Block A");
    expect(screen.getByLabelText("Address")).toHaveValue("Fjordinkatu 12, Helsinki");
  });

  it("fills the form from a property and submits an update without tenant_id", async () => {
    mockedUsePropertiesPageState.mockReturnValue({
      createProperty,
      error: null,
      isLoading: false,
      isSubmitting: false,
      properties: [
        {
          address: "Main Street 1",
          created_at: "2026-04-22T08:00:00Z",
          name: "HQ",
          property_id: "property-1",
          tenant_id: "tenant-a",
        },
      ],
      updateProperty,
    });

    render(<PropertiesPage />);

    fireEvent.click(screen.getByRole("button", { name: "Edit HQ" }));

    expect(screen.getByLabelText("Name")).toHaveValue("HQ");
    expect(screen.getByLabelText("Address")).toHaveValue("Main Street 1");

    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "Updated HQ" },
    });
    fireEvent.change(screen.getByLabelText("Address"), {
      target: { value: "Updated Street 2" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Update property" }).closest("form")!);

    await waitFor(() => {
      expect(updateProperty).toHaveBeenCalledWith("property-1", {
        address: "Updated Street 2",
        name: "Updated HQ",
      });
    });

    expect(updateProperty.mock.calls[0][1]).not.toHaveProperty("tenant_id");
    expect(createProperty).not.toHaveBeenCalled();
  });

  it("resets property edit mode after a successful update", async () => {
    mockedUsePropertiesPageState.mockReturnValue({
      createProperty,
      error: null,
      isLoading: false,
      isSubmitting: false,
      properties: [
        {
          address: "Main Street 1",
          created_at: "2026-04-22T08:00:00Z",
          name: "HQ",
          property_id: "property-1",
          tenant_id: "tenant-a",
        },
      ],
      updateProperty,
    });

    render(<PropertiesPage />);

    fireEvent.click(screen.getByRole("button", { name: "Edit HQ" }));
    fireEvent.submit(screen.getByRole("button", { name: "Update property" }).closest("form")!);

    await waitFor(() => {
      expect(updateProperty).toHaveBeenCalledTimes(1);
    });

    expect(screen.getByRole("button", { name: "Create property" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel edit" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Name")).toHaveValue("");
    expect(screen.getByLabelText("Address")).toHaveValue("");
  });

  it("cancels property edit mode without submitting", () => {
    mockedUsePropertiesPageState.mockReturnValue({
      createProperty,
      error: null,
      isLoading: false,
      isSubmitting: false,
      properties: [
        {
          address: "Main Street 1",
          created_at: "2026-04-22T08:00:00Z",
          name: "HQ",
          property_id: "property-1",
          tenant_id: "tenant-a",
        },
      ],
      updateProperty,
    });

    render(<PropertiesPage />);

    fireEvent.click(screen.getByRole("button", { name: "Edit HQ" }));
    fireEvent.click(screen.getByRole("button", { name: "Cancel edit" }));

    expect(updateProperty).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Create property" })).toBeInTheDocument();
    expect(screen.getByLabelText("Name")).toHaveValue("");
    expect(screen.getByLabelText("Address")).toHaveValue("");
  });

  it("keeps form values when property update fails", async () => {
    updateProperty.mockRejectedValue(new Error("Update failed"));
    mockedUsePropertiesPageState.mockReturnValue({
      createProperty,
      error: null,
      isLoading: false,
      isSubmitting: false,
      properties: [
        {
          address: "Main Street 1",
          created_at: "2026-04-22T08:00:00Z",
          name: "HQ",
          property_id: "property-1",
          tenant_id: "tenant-a",
        },
      ],
      updateProperty,
    });

    render(<PropertiesPage />);

    fireEvent.click(screen.getByRole("button", { name: "Edit HQ" }));
    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "Updated HQ" },
    });
    fireEvent.change(screen.getByLabelText("Address"), {
      target: { value: "Updated Street 2" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Update property" }).closest("form")!);

    await waitFor(() => {
      expect(updateProperty).toHaveBeenCalledTimes(1);
    });

    expect(screen.getByRole("button", { name: "Update property" })).toBeInTheDocument();
    expect(screen.getByLabelText("Name")).toHaveValue("Updated HQ");
    expect(screen.getByLabelText("Address")).toHaveValue("Updated Street 2");
  });
});
