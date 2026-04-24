import { useState, type FormEvent } from "react";
import { usePropertiesPageState } from "../features/properties/usePropertiesPage";

type PropertyForm = {
  address: string;
  name: string;
};

const INITIAL_FORM: PropertyForm = {
  address: "",
  name: "",
};

export function PropertiesPage() {
  const { createProperty, error, isLoading, isSubmitting, properties } =
    usePropertiesPageState();
  const [form, setForm] = useState<PropertyForm>(INITIAL_FORM);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await createProperty({
        address: form.address.trim(),
        name: form.name.trim(),
      });
      setForm(INITIAL_FORM);
    } catch {
      // The hook already exposes the user-facing error message.
    }
  }

  return (
    <section className="page-grid">
      <article className="panel-card">
        <div className="section-heading">
          <p className="eyebrow">Properties</p>
          <h2 className="section-title">Capture the physical portfolio first.</h2>
        </div>
        <form className="stack-form" onSubmit={handleSubmit}>
          <label className="field-label" htmlFor="property-name">
            Name
          </label>
          <input
            id="property-name"
            onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
            placeholder="North Yard Block A"
            required
            value={form.name}
          />
          <label className="field-label" htmlFor="property-address">
            Address
          </label>
          <input
            id="property-address"
            onChange={(event) =>
              setForm((current) => ({ ...current, address: event.target.value }))
            }
            placeholder="Fjordinkatu 12, Helsinki"
            required
            value={form.address}
          />
          <button className="primary-button" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Saving..." : "Create property"}
          </button>
        </form>
        <p className="supporting-copy">
          The browser never sends `tenant_id`. Tenant context comes from the
          Cognito ID token the backend validates.
        </p>
        {error ? <p className="error-text">{error}</p> : null}
      </article>

      <article className="panel-card">
        <div className="section-heading">
          <p className="eyebrow">Current list</p>
          <h2 className="section-title">Tenant-scoped property inventory.</h2>
        </div>
        {isLoading ? (
          <p className="supporting-copy">Loading properties...</p>
        ) : properties.length === 0 ? (
          <div className="empty-state">
            <h3>No properties yet</h3>
            <p>
              Create the first property here. Lease creation depends on a property
              existing first.
            </p>
          </div>
        ) : (
          <ul className="resource-list">
            {properties.map((property) => (
              <li className="resource-card" key={property.property_id}>
                <div>
                  <p className="resource-title">{property.name}</p>
                  <p className="resource-subtitle">{property.address}</p>
                </div>
                <time className="resource-meta" dateTime={property.created_at}>
                  {new Date(property.created_at).toLocaleDateString("en-GB")}
                </time>
              </li>
            ))}
          </ul>
        )}
      </article>
    </section>
  );
}
