import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PropertiesPage } from "./PropertiesPage";

const createProperty = vi.fn();
const mockedUsePropertiesPageState = vi.fn();

vi.mock("../features/properties/usePropertiesPage", () => ({
  usePropertiesPageState: () => mockedUsePropertiesPageState(),
}));

describe("PropertiesPage", () => {
  beforeEach(() => {
    createProperty.mockReset();
    createProperty.mockResolvedValue(undefined);
    mockedUsePropertiesPageState.mockReset();
    mockedUsePropertiesPageState.mockReturnValue({
      createProperty,
      error: null,
      isLoading: false,
      isSubmitting: false,
      properties: [],
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
});
