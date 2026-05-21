import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { activeDateLocale } from "../i18n";
import { usePropertiesPageState } from "../features/properties/usePropertiesPage";
import type { Property } from "../lib/api";

type PropertyForm = {
  address: string;
  name: string;
};

const INITIAL_FORM: PropertyForm = {
  address: "",
  name: "",
};

export function PropertiesPage() {
  const { t } = useTranslation();
  const { createProperty, error, isLoading, isSubmitting, properties, updateProperty } =
    usePropertiesPageState();
  const [form, setForm] = useState<PropertyForm>(INITIAL_FORM);
  const [editingPropertyId, setEditingPropertyId] = useState<string | null>(null);

  const isEditing = editingPropertyId !== null;

  function resetForm() {
    setEditingPropertyId(null);
    setForm(INITIAL_FORM);
  }

  function startEdit(property: Property) {
    setEditingPropertyId(property.property_id);
    setForm({
      address: property.address,
      name: property.name,
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = {
      address: form.address.trim(),
      name: form.name.trim(),
    };

    try {
      if (editingPropertyId) {
        await updateProperty(editingPropertyId, input);
      } else {
        await createProperty(input);
      }
      resetForm();
    } catch {
      // The hook already exposes the user-facing error message.
    }
  }

  return (
    <section className="page-grid">
      <article className="panel-card">
        <div className="section-heading">
          <p className="eyebrow">{t("appShell.nav.properties")}</p>
          <h2 className="section-title">{t("properties.title")}</h2>
        </div>
        <form className="stack-form" onSubmit={handleSubmit}>
          <label className="field-label" htmlFor="property-name">
            {t("properties.name")}
          </label>
          <input
            id="property-name"
            onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
            placeholder={t("properties.namePlaceholder")}
            required
            value={form.name}
          />
          <label className="field-label" htmlFor="property-address">
            {t("properties.address")}
          </label>
          <input
            id="property-address"
            onChange={(event) =>
              setForm((current) => ({ ...current, address: event.target.value }))
            }
            placeholder={t("properties.addressPlaceholder")}
            required
            value={form.address}
          />
          <button className="primary-button" disabled={isSubmitting} type="submit">
            {isSubmitting
              ? t("properties.saving")
              : isEditing
                ? t("properties.updateProperty")
                : t("properties.createProperty")}
          </button>
          {isEditing ? (
            <button className="ghost-button" onClick={resetForm} type="button">
              {t("properties.cancelEdit")}
            </button>
          ) : null}
        </form>
        <p className="supporting-copy">{t("properties.tenantNote")}</p>
        {error ? <p className="error-text">{error}</p> : null}
      </article>

      <article className="panel-card">
        <div className="section-heading">
          <p className="eyebrow">{t("properties.currentList")}</p>
          <h2 className="section-title">{t("properties.listTitle")}</h2>
        </div>
        {isLoading ? (
          <p className="supporting-copy">{t("properties.loading")}</p>
        ) : properties.length === 0 ? (
          <div className="empty-state">
            <h3>{t("properties.empty.title")}</h3>
            <p>{t("properties.empty.body")}</p>
          </div>
        ) : (
          <ul className="resource-list">
            {properties.map((property) => (
              <li className="resource-card" key={property.property_id}>
                <div>
                  <p className="resource-title">{property.name}</p>
                  <p className="resource-subtitle">{property.address}</p>
                </div>
                <div className="resource-actions">
                  <time className="resource-meta" dateTime={property.created_at}>
                    {new Date(property.created_at).toLocaleDateString(activeDateLocale())}
                  </time>
                  <button
                    aria-label={t("properties.editLabel", { name: property.name })}
                    className="ghost-button resource-edit-button"
                    onClick={() => startEdit(property)}
                    type="button"
                  >
                    {t("properties.edit")}
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
