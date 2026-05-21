import { useState } from "react";
import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";
import { useNotificationsPageState } from "../features/notifications/useNotificationsPage";
import { activeDateLocale } from "../i18n";
import type {
  NotificationContact,
  NotificationEmailDeliverySummary,
  NotificationItem,
} from "../lib/api";

function formatDaysUntilDue(days: number, t: TFunction) {
  if (days === 0) {
    return t("notifications.timeDistance.today");
  }
  if (days === 1) {
    return t("notifications.timeDistance.oneDay");
  }
  return t("notifications.timeDistance.days", { count: days });
}

const EMPTY_DELIVERY_SUMMARY: NotificationEmailDeliverySummary = {
  failed_count: 0,
  last_error_code: null,
  latest_attempt_at: null,
  latest_sent_at: null,
  pending_count: 0,
  sent_count: 0,
  total_count: 0,
};

function notificationDeliverySummary(notification: NotificationItem) {
  return notification.delivery_summary ?? EMPTY_DELIVERY_SUMMARY;
}

function emailDeliveryLabel(
  summary: NotificationEmailDeliverySummary,
  t: TFunction
) {
  if (summary.total_count === 0) {
    return t("notifications.delivery.notPrepared");
  }
  if (summary.sent_count === summary.total_count) {
    return t("notifications.delivery.sent");
  }
  if (summary.failed_count === summary.total_count) {
    return t("notifications.delivery.failed");
  }
  if (summary.pending_count === summary.total_count) {
    return t("notifications.delivery.pending");
  }
  return t("notifications.delivery.mixed");
}

function emailDeliveryCounts(
  summary: NotificationEmailDeliverySummary,
  t: TFunction
) {
  const parts = [
    summary.sent_count > 0
      ? t("notifications.delivery.sentCount", { count: summary.sent_count })
      : null,
    summary.failed_count > 0
      ? t("notifications.delivery.failedCount", { count: summary.failed_count })
      : null,
    summary.pending_count > 0
      ? t("notifications.delivery.pendingCount", { count: summary.pending_count })
      : null,
  ].filter(Boolean);

  if (parts.length === 0) {
    return t("notifications.delivery.countsEmpty", { count: summary.total_count });
  }

  return parts.join(" | ");
}

export function NotificationsPage() {
  const { t } = useTranslation();
  const {
    createNotificationContact,
    dueReminders,
    error,
    isLoading,
    markNotificationRead,
    notificationContacts,
    notifications,
    readingNotificationId,
    removeContactSuppression,
    removingSuppressionKey,
    updatingContactId,
    updateNotificationContact,
  } = useNotificationsPageState();
  const [contactEmail, setContactEmail] = useState("");

  async function handleMarkRead(notification: NotificationItem) {
    try {
      await markNotificationRead(notification.notification_id);
    } catch {
      // The hook already exposes the user-facing error message.
    }
  }

  async function handleCreateContact(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const email = contactEmail.trim();
    if (!email) {
      return;
    }

    try {
      await createNotificationContact({ email });
      setContactEmail("");
    } catch {
      // The hook already exposes the user-facing error message.
    }
  }

  async function handleToggleContact(contact: NotificationContact) {
    try {
      await updateNotificationContact(contact.contact_id, { enabled: !contact.enabled });
    } catch {
      // The hook already exposes the user-facing error message.
    }
  }

  return (
    <section className="page-grid notifications-grid">
      <article className="panel-card">
        <div className="section-heading">
          <p className="eyebrow">{t("notifications.emailRecipients")}</p>
          <h2 className="section-title">{t("notifications.sectionContactsTitle")}</h2>
        </div>
        <form className="stack-form" onSubmit={handleCreateContact}>
          <label className="field-label" htmlFor="notification-contact-email">
            {t("notifications.contactEmail")}
          </label>
          <input
            id="notification-contact-email"
            name="email"
            onChange={(event) => setContactEmail(event.target.value)}
            placeholder={t("notifications.contactPlaceholder")}
            type="email"
            value={contactEmail}
          />
          <button className="primary-button" disabled={!contactEmail.trim()} type="submit">
            {t("notifications.addContact")}
          </button>
        </form>
        {isLoading ? (
          <p className="supporting-copy">{t("notifications.contacts.loading")}</p>
        ) : notificationContacts.length === 0 ? (
          <div className="empty-state">
            <h3>{t("notifications.contacts.emptyTitle")}</h3>
            <p>{t("notifications.contacts.emptyBody")}</p>
          </div>
        ) : (
          <ul className="resource-list">
            {notificationContacts.map((contact) => (
              <li className="resource-card" key={contact.contact_id}>
                <div>
                  <p className="resource-title">{contact.email}</p>
                  <p className="resource-meta">
                    {t("notifications.notifications.created", {
                      date: new Date(contact.created_at).toLocaleDateString(activeDateLocale()),
                    })}
                  </p>
                </div>
                <div className="resource-actions">
                  <span className={contact.enabled ? "status-pill" : "status-pill status-pill-unread"}>
                    {contact.enabled
                      ? t("notifications.contacts.enabled")
                      : t("notifications.contacts.disabled")}
                  </span>
                  {contact.suppression_reasons?.includes("bounce") && (
                    <span className="status-pill status-pill-unread">
                      {t("notifications.contacts.suppressBounce")}
                      <button
                        aria-label={t("notifications.contacts.removeBounceSuppression", {
                          email: contact.email,
                        })}
                        className="ghost-button resource-edit-button"
                        disabled={removingSuppressionKey === `${contact.contact_id}:bounce`}
                        onClick={() => void removeContactSuppression(contact.contact_id, "bounce")}
                        type="button"
                      >
                        {t("notifications.contacts.remove")}
                      </button>
                    </span>
                  )}
                  {contact.suppression_reasons?.includes("complaint") && (
                    <span className="status-pill status-pill-unread">
                      {t("notifications.contacts.suppressComplaint")}
                      <button
                        aria-label={t("notifications.contacts.removeComplaintSuppression", {
                          email: contact.email,
                        })}
                        className="ghost-button resource-edit-button"
                        disabled={removingSuppressionKey === `${contact.contact_id}:complaint`}
                        onClick={() => void removeContactSuppression(contact.contact_id, "complaint")}
                        type="button"
                      >
                        {t("notifications.contacts.remove")}
                      </button>
                    </span>
                  )}
                  <button
                    aria-label={
                      contact.enabled
                        ? t("notifications.contacts.toggleDisable", { email: contact.email })
                        : t("notifications.contacts.toggleEnable", { email: contact.email })
                    }
                    className="ghost-button resource-edit-button"
                    disabled={updatingContactId === contact.contact_id}
                    onClick={() => void handleToggleContact(contact)}
                    type="button"
                  >
                    {contact.enabled
                      ? t("notifications.contacts.toggleDisableShort")
                      : t("notifications.contacts.toggleEnableShort")}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </article>

      <article className="panel-card">
        <div className="section-heading">
          <p className="eyebrow">{t("notifications.sections.dueReminders")}</p>
          <h2 className="section-title">{t("notifications.dueReminders.title")}</h2>
        </div>
        {isLoading ? (
          <p className="supporting-copy">{t("notifications.dueReminders.loading")}</p>
        ) : dueReminders.length === 0 ? (
          <div className="empty-state">
            <h3>{t("notifications.dueReminders.emptyTitle")}</h3>
            <p>{t("notifications.dueReminders.emptyBody")}</p>
          </div>
        ) : (
          <ul className="resource-list">
            {dueReminders.map((reminder) => (
              <li className="resource-card" key={reminder.lease_id}>
                <div>
                  <p className="resource-title">{reminder.resident_name}</p>
                  <p className="resource-subtitle">
                    {t("notifications.dueReminders.dueLine", {
                      date: reminder.due_date,
                      distance: formatDaysUntilDue(reminder.days_until_due, t),
                    })}
                  </p>
                </div>
                <div className="resource-actions">
                  <code className="resource-meta">
                    {t("notifications.dueReminders.rentDueDay", {
                      day: reminder.rent_due_day_of_month,
                    })}
                  </code>
                  <code className="resource-meta">
                    {t("notifications.propertyShort", {
                      id: reminder.property_id.slice(0, 8),
                    })}
                  </code>
                </div>
              </li>
            ))}
          </ul>
        )}
      </article>

      <article className="panel-card">
        <div className="section-heading">
          <p className="eyebrow">{t("notifications.sections.notifications")}</p>
          <h2 className="section-title">{t("notifications.notifications.title")}</h2>
        </div>
        {isLoading ? (
          <p className="supporting-copy">{t("notifications.notifications.loading")}</p>
        ) : notifications.length === 0 ? (
          <div className="empty-state">
            <h3>{t("notifications.notifications.emptyTitle")}</h3>
            <p>{t("notifications.notifications.emptyBody")}</p>
          </div>
        ) : (
          <ul className="resource-list">
            {notifications.map((notification) => {
              const isRead = notification.read_at !== null;
              const deliverySummary = notificationDeliverySummary(notification);

              return (
                <li className="resource-card notification-card" key={notification.notification_id}>
                  <div>
                    <div className="notification-title-row">
                      <p className="resource-title">{notification.title}</p>
                      <span className={isRead ? "status-pill" : "status-pill status-pill-unread"}>
                        {isRead
                          ? t("notifications.notifications.read")
                          : t("notifications.notifications.unread")}
                      </span>
                    </div>
                    <p className="resource-subtitle">{notification.message}</p>
                    <p className="resource-meta">
                      {t("notifications.notifications.dueCreated", {
                        createdDate: new Date(notification.created_at).toLocaleDateString(
                          activeDateLocale()
                        ),
                        dueDate: notification.due_date,
                      })}
                    </p>
                    <p className="resource-meta">
                      {t("notifications.delivery.label", {
                        status: emailDeliveryLabel(deliverySummary, t),
                      })}
                    </p>
                    {deliverySummary.total_count > 0 ? (
                      <p className="resource-meta">
                        {emailDeliveryCounts(deliverySummary, t)}
                      </p>
                    ) : null}
                    {deliverySummary.last_error_code ? (
                      <p className="resource-meta">
                        {t("notifications.delivery.lastFailure", {
                          code: deliverySummary.last_error_code,
                        })}
                      </p>
                    ) : null}
                  </div>
                  <div className="resource-actions">
                    {isRead ? (
                      <time className="resource-meta" dateTime={notification.read_at ?? undefined}>
                        {t("notifications.notifications.readDate", {
                          date: new Date(notification.read_at ?? "").toLocaleDateString(
                            activeDateLocale()
                          ),
                        })}
                      </time>
                    ) : (
                      <button
                        aria-label={t("notifications.markReadLabel", {
                          title: notification.title,
                        })}
                        className="ghost-button resource-edit-button"
                        disabled={readingNotificationId === notification.notification_id}
                        onClick={() => void handleMarkRead(notification)}
                        type="button"
                      >
                        {t("notifications.markRead")}
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
        {error ? <p className="error-text">{error}</p> : null}
      </article>
    </section>
  );
}
