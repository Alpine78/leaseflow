import { useState } from "react";
import { useNotificationsPageState } from "../features/notifications/useNotificationsPage";
import type { NotificationContact, NotificationItem } from "../lib/api";

function formatDaysUntilDue(days: number) {
  if (days === 0) {
    return "today";
  }
  if (days === 1) {
    return "1 day from now";
  }
  return `${days} days from now`;
}

export function NotificationsPage() {
  const {
    createNotificationContact,
    dueReminders,
    error,
    isLoading,
    markNotificationRead,
    notificationContacts,
    notifications,
    readingNotificationId,
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
          <p className="eyebrow">Email recipients</p>
          <h2 className="section-title">Notification contacts.</h2>
        </div>
        <form className="stack-form" onSubmit={handleCreateContact}>
          <label className="field-label" htmlFor="notification-contact-email">
            Contact email
          </label>
          <input
            id="notification-contact-email"
            name="email"
            onChange={(event) => setContactEmail(event.target.value)}
            placeholder="recipient@example.com"
            type="email"
            value={contactEmail}
          />
          <button className="primary-button" disabled={!contactEmail.trim()} type="submit">
            Add contact
          </button>
        </form>
        {isLoading ? (
          <p className="supporting-copy">Loading notification contacts...</p>
        ) : notificationContacts.length === 0 ? (
          <div className="empty-state">
            <h3>No notification contacts yet</h3>
            <p>Add an enabled recipient before running SES delivery smoke.</p>
          </div>
        ) : (
          <ul className="resource-list">
            {notificationContacts.map((contact) => (
              <li className="resource-card" key={contact.contact_id}>
                <div>
                  <p className="resource-title">{contact.email}</p>
                  <p className="resource-meta">
                    Created {new Date(contact.created_at).toLocaleDateString("en-GB")}
                  </p>
                </div>
                <div className="resource-actions">
                  <span className={contact.enabled ? "status-pill" : "status-pill status-pill-unread"}>
                    {contact.enabled ? "Enabled" : "Disabled"}
                  </span>
                  <button
                    aria-label={`${contact.enabled ? "Disable" : "Enable"} ${contact.email}`}
                    className="ghost-button resource-edit-button"
                    disabled={updatingContactId === contact.contact_id}
                    onClick={() => void handleToggleContact(contact)}
                    type="button"
                  >
                    {contact.enabled ? "Disable" : "Enable"}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </article>

      <article className="panel-card">
        <div className="section-heading">
          <p className="eyebrow">Due reminders</p>
          <h2 className="section-title">Rent coming due soon.</h2>
        </div>
        {isLoading ? (
          <p className="supporting-copy">Loading reminders...</p>
        ) : dueReminders.length === 0 ? (
          <div className="empty-state">
            <h3>No rent due soon</h3>
            <p>The backend default 7-day reminder window has no matching leases.</p>
          </div>
        ) : (
          <ul className="resource-list">
            {dueReminders.map((reminder) => (
              <li className="resource-card" key={reminder.lease_id}>
                <div>
                  <p className="resource-title">{reminder.resident_name}</p>
                  <p className="resource-subtitle">
                    Due {reminder.due_date} | {formatDaysUntilDue(reminder.days_until_due)}
                  </p>
                </div>
                <div className="resource-actions">
                  <code className="resource-meta">
                    rent due day {reminder.rent_due_day_of_month}
                  </code>
                  <code className="resource-meta">
                    property {reminder.property_id.slice(0, 8)}
                  </code>
                </div>
              </li>
            ))}
          </ul>
        )}
      </article>

      <article className="panel-card">
        <div className="section-heading">
          <p className="eyebrow">Notifications</p>
          <h2 className="section-title">Persisted tenant notifications.</h2>
        </div>
        {isLoading ? (
          <p className="supporting-copy">Loading notifications...</p>
        ) : notifications.length === 0 ? (
          <div className="empty-state">
            <h3>No persisted notifications yet</h3>
            <p>Notification rows appear here after backend reminder processing creates them.</p>
          </div>
        ) : (
          <ul className="resource-list">
            {notifications.map((notification) => {
              const isRead = notification.read_at !== null;

              return (
                <li className="resource-card notification-card" key={notification.notification_id}>
                  <div>
                    <div className="notification-title-row">
                      <p className="resource-title">{notification.title}</p>
                      <span className={isRead ? "status-pill" : "status-pill status-pill-unread"}>
                        {isRead ? "Read" : "Unread"}
                      </span>
                    </div>
                    <p className="resource-subtitle">{notification.message}</p>
                    <p className="resource-meta">
                      Due {notification.due_date} | Created{" "}
                      {new Date(notification.created_at).toLocaleDateString("en-GB")}
                    </p>
                  </div>
                  <div className="resource-actions">
                    {isRead ? (
                      <time className="resource-meta" dateTime={notification.read_at ?? undefined}>
                        Read {new Date(notification.read_at ?? "").toLocaleDateString("en-GB")}
                      </time>
                    ) : (
                      <button
                        aria-label={`Mark ${notification.title} read`}
                        className="ghost-button resource-edit-button"
                        disabled={readingNotificationId === notification.notification_id}
                        onClick={() => void handleMarkRead(notification)}
                        type="button"
                      >
                        Mark read
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
