import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useLeasesPageState } from "../features/leases/useLeasesPage";
import type { Lease } from "../lib/api";

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
  const { t } = useTranslation();
  const { createLease, error, isLoading, isSubmitting, leases, properties, updateLease } =
    useLeasesPageState();
  const [form, setForm] = useState<LeaseForm>(() => createInitialLeaseForm());
  const [editingLeaseId, setEditingLeaseId] = useState<string | null>(null);

  const isEditing = editingLeaseId !== null;
  const hasProperties = properties.length > 0;
  const selectedPropertyId =
    form.propertyId || (hasProperties ? properties[0].property_id : "");
  const linkedPropertyName =
    properties.find((property) => property.property_id === form.propertyId)?.name ||
    (form.propertyId
      ? t("leases.placeholderProperty", { id: form.propertyId.slice(0, 8) })
      : t("leases.unknownProperty"));
  const canSubmit = hasProperties || isEditing;

  function resetForm(propertyId = selectedPropertyId) {
    setEditingLeaseId(null);
    setForm(createInitialLeaseForm(propertyId));
  }

  function startEdit(lease: Lease) {
    setEditingLeaseId(lease.lease_id);
    setForm({
      endDate: lease.end_date,
      propertyId: lease.property_id,
      rentDueDayOfMonth: String(lease.rent_due_day_of_month ?? ""),
      residentName: lease.resident_name,
      startDate: lease.start_date,
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }

    try {
      const input = {
        end_date: form.endDate,
        rent_due_day_of_month: Number(form.rentDueDayOfMonth),
        resident_name: form.residentName.trim(),
        start_date: form.startDate,
      };

      if (editingLeaseId) {
        await updateLease(editingLeaseId, input);
      } else {
        await createLease({
          ...input,
          property_id: selectedPropertyId,
        });
      }

      resetForm(selectedPropertyId);
    } catch {
      // The hook already exposes the user-facing error message.
    }
  }

  return (
    <section className="page-grid">
      <article className="panel-card">
        <div className="section-heading">
          <p className="eyebrow">{t("appShell.nav.leases")}</p>
          <h2 className="section-title">{t("leases.title")}</h2>
        </div>
        <form className="stack-form" onSubmit={handleSubmit}>
          {isEditing ? (
            <p className="supporting-copy">
              {t("leases.linkedProperty", { name: linkedPropertyName })}
            </p>
          ) : (
            <>
              <label className="field-label" htmlFor="lease-property">
                {t("leases.property")}
              </label>
              <select
                disabled={!hasProperties}
                id="lease-property"
                onChange={(event) =>
                  setForm((current) => ({ ...current, propertyId: event.target.value }))
                }
                value={selectedPropertyId}
              >
                {hasProperties ? null : <option value="">{t("leases.createFirstProperty")}</option>}
                {properties.map((property) => (
                  <option key={property.property_id} value={property.property_id}>
                    {property.name}
                  </option>
                ))}
              </select>
            </>
          )}

          <label className="field-label" htmlFor="lease-resident-name">
            {t("leases.residentName")}
          </label>
          <input
            disabled={!canSubmit}
            id="lease-resident-name"
            onChange={(event) =>
              setForm((current) => ({ ...current, residentName: event.target.value }))
            }
            placeholder={t("leases.residentNamePlaceholder")}
            required
            value={form.residentName}
          />

          <div className="two-column-fields">
            <div>
              <label className="field-label" htmlFor="lease-rent-day">
                {t("leases.rentDueDay")}
              </label>
              <input
                disabled={!canSubmit}
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
                {t("leases.startDate")}
              </label>
              <input
                disabled={!canSubmit}
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
            {t("leases.endDate")}
          </label>
          <input
            disabled={!canSubmit}
            id="lease-end-date"
            onChange={(event) =>
              setForm((current) => ({ ...current, endDate: event.target.value }))
            }
            required
            type="date"
            value={form.endDate}
          />

          <button className="primary-button" disabled={!canSubmit || isSubmitting} type="submit">
            {isSubmitting
              ? t("properties.saving")
              : isEditing
                ? t("leases.updateLease")
                : t("leases.createLease")}
          </button>
          {isEditing ? (
            <button className="ghost-button" onClick={() => resetForm()} type="button">
              {t("leases.cancelEdit")}
            </button>
          ) : null}
        </form>
        {!hasProperties && !isEditing ? (
          <p className="supporting-copy">{t("leases.formDisabled")}</p>
        ) : null}
        {error ? <p className="error-text">{error}</p> : null}
      </article>

      <article className="panel-card">
        <div className="section-heading">
          <p className="eyebrow">{t("leases.currentList")}</p>
          <h2 className="section-title">{t("leases.listTitle")}</h2>
        </div>
        {isLoading ? (
          <p className="supporting-copy">{t("leases.loading")}</p>
        ) : leases.length === 0 ? (
          <div className="empty-state">
            <h3>{t("leases.empty.title")}</h3>
            <p>{t("leases.empty.body")}</p>
          </div>
        ) : (
          <ul className="resource-list">
            {leases.map((lease) => (
              <li className="resource-card" key={lease.lease_id}>
                <div>
                  <p className="resource-title">{lease.resident_name}</p>
                  <p className="resource-subtitle">
                    {t("leases.dueDay", {
                      day: lease.rent_due_day_of_month,
                      endDate: lease.end_date,
                      startDate: lease.start_date,
                    })}
                  </p>
                </div>
                <div className="resource-actions">
                  <code className="resource-meta">
                    {t("leases.placeholderProperty", { id: lease.property_id.slice(0, 8) })}
                  </code>
                  <button
                    aria-label={t("leases.editLabel", { name: lease.resident_name })}
                    className="ghost-button resource-edit-button"
                    onClick={() => startEdit(lease)}
                    type="button"
                  >
                    {t("leases.edit")}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </article>
    </section>
  );
}
