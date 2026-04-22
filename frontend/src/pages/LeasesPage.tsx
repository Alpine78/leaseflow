import { useState, type FormEvent } from "react";
import { useLeasesPageState } from "../features/leases/useLeasesPage";

type LeaseForm = {
  endDate: string;
  propertyId: string;
  rentDueDayOfMonth: string;
  residentName: string;
  startDate: string;
};

function createInitialLeaseForm(propertyId = ""): LeaseForm {
  const now = new Date();
  const startDate = now.toISOString().slice(0, 10);
  const endDate = new Date(now);
  endDate.setUTCDate(endDate.getUTCDate() + 30);

  return {
    endDate: endDate.toISOString().slice(0, 10),
    propertyId,
    rentDueDayOfMonth: String(now.getUTCDate()),
    residentName: "",
    startDate,
  };
}

export function LeasesPage() {
  const { createLease, error, isLoading, isSubmitting, leases, properties } =
    useLeasesPageState();
  const [form, setForm] = useState<LeaseForm>(() => createInitialLeaseForm());

  const hasProperties = properties.length > 0;
  const selectedPropertyId =
    form.propertyId || (hasProperties ? properties[0].property_id : "");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!hasProperties) {
      return;
    }

    await createLease({
      end_date: form.endDate,
      property_id: selectedPropertyId,
      rent_due_day_of_month: Number(form.rentDueDayOfMonth),
      resident_name: form.residentName.trim(),
      start_date: form.startDate,
    });

    setForm(createInitialLeaseForm(selectedPropertyId));
  }

  return (
    <section className="page-grid">
      <article className="panel-card">
        <div className="section-heading">
          <p className="eyebrow">Leases</p>
          <h2 className="section-title">Attach live residents to real properties.</h2>
        </div>
        <form className="stack-form" onSubmit={handleSubmit}>
          <label className="field-label" htmlFor="lease-property">
            Property
          </label>
          <select
            disabled={!hasProperties}
            id="lease-property"
            onChange={(event) =>
              setForm((current) => ({ ...current, propertyId: event.target.value }))
            }
            value={selectedPropertyId}
          >
            {hasProperties ? null : <option value="">Create a property first</option>}
            {properties.map((property) => (
              <option key={property.property_id} value={property.property_id}>
                {property.name}
              </option>
            ))}
          </select>

          <label className="field-label" htmlFor="lease-resident-name">
            Resident name
          </label>
          <input
            disabled={!hasProperties}
            id="lease-resident-name"
            onChange={(event) =>
              setForm((current) => ({ ...current, residentName: event.target.value }))
            }
            placeholder="Kaisa Tenant"
            required
            value={form.residentName}
          />

          <div className="two-column-fields">
            <div>
              <label className="field-label" htmlFor="lease-rent-day">
                Rent due day
              </label>
              <input
                disabled={!hasProperties}
                id="lease-rent-day"
                max="31"
                min="1"
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    rentDueDayOfMonth: event.target.value,
                  }))
                }
                required
                type="number"
                value={form.rentDueDayOfMonth}
              />
            </div>
            <div>
              <label className="field-label" htmlFor="lease-start-date">
                Start date
              </label>
              <input
                disabled={!hasProperties}
                id="lease-start-date"
                onChange={(event) =>
                  setForm((current) => ({ ...current, startDate: event.target.value }))
                }
                required
                type="date"
                value={form.startDate}
              />
            </div>
          </div>

          <label className="field-label" htmlFor="lease-end-date">
            End date
          </label>
          <input
            disabled={!hasProperties}
            id="lease-end-date"
            onChange={(event) =>
              setForm((current) => ({ ...current, endDate: event.target.value }))
            }
            required
            type="date"
            value={form.endDate}
          />

          <button className="primary-button" disabled={!hasProperties || isSubmitting} type="submit">
            {isSubmitting ? "Saving..." : "Create lease"}
          </button>
        </form>
        {!hasProperties ? (
          <p className="supporting-copy">
            Lease creation stays disabled until the tenant has at least one property.
          </p>
        ) : null}
        {error ? <p className="error-text">{error}</p> : null}
      </article>

      <article className="panel-card">
        <div className="section-heading">
          <p className="eyebrow">Current list</p>
          <h2 className="section-title">Tenant-scoped lease portfolio.</h2>
        </div>
        {isLoading ? (
          <p className="supporting-copy">Loading leases...</p>
        ) : leases.length === 0 ? (
          <div className="empty-state">
            <h3>No leases yet</h3>
            <p>
              Once a property exists, you can create the first lease from the form on
              this page.
            </p>
          </div>
        ) : (
          <ul className="resource-list">
            {leases.map((lease) => (
              <li className="resource-card" key={lease.lease_id}>
                <div>
                  <p className="resource-title">{lease.resident_name}</p>
                  <p className="resource-subtitle">
                    Due day {lease.rent_due_day_of_month} · {lease.start_date} to {lease.end_date}
                  </p>
                </div>
                <code className="resource-meta">property {lease.property_id.slice(0, 8)}</code>
              </li>
            ))}
          </ul>
        )}
      </article>
    </section>
  );
}
