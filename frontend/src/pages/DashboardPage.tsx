import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useDashboardPageState } from "../features/dashboard/useDashboardPage";

type SummaryCardProps = {
  summaryText: string;
  supportingText: string;
};

function SummaryCard({ summaryText, supportingText }: SummaryCardProps) {
  return (
    <article className="summary-card">
      <p className="summary-count">{summaryText}</p>
      <p className="resource-subtitle">{supportingText}</p>
    </article>
  );
}

export function DashboardPage() {
  const { t } = useTranslation();
  const { error, isLoading, summary } = useDashboardPageState();

  return (
    <section className="dashboard-layout">
      <article className="panel-card">
        <div className="section-heading">
          <p className="eyebrow">{t("dashboard.eyebrow")}</p>
          <h2 className="section-title">{t("dashboard.title")}</h2>
        </div>
        {isLoading ? (
          <p className="supporting-copy">{t("dashboard.loading")}</p>
        ) : (
          <div className="summary-grid">
            <SummaryCard
              summaryText={t("dashboard.cards.properties", { count: summary.propertyCount })}
              supportingText={t("dashboard.cards.propertiesSupporting")}
            />
            <SummaryCard
              summaryText={t("dashboard.cards.leases", { count: summary.leaseCount })}
              supportingText={t("dashboard.cards.leasesSupporting")}
            />
            <SummaryCard
              summaryText={t("dashboard.cards.dueSoon", { count: summary.dueReminderCount })}
              supportingText={t("dashboard.cards.dueSoonSupporting")}
            />
            <SummaryCard
              summaryText={t("dashboard.cards.unread", { count: summary.unreadNotificationCount })}
              supportingText={t("dashboard.cards.unreadSupporting")}
            />
          </div>
        )}
        {error ? <p className="error-text">{error}</p> : null}
      </article>

      <article className="panel-card">
        <div className="section-heading">
          <p className="eyebrow">{t("dashboard.nextActionsEyebrow")}</p>
          <h2 className="section-title">{t("dashboard.nextActionsTitle")}</h2>
        </div>
        <div className="dashboard-actions">
          <Link className="primary-button dashboard-action-link" to="/properties">
            {t("dashboard.actions.properties")}
          </Link>
          <Link className="ghost-button dashboard-action-link" to="/leases">
            {t("dashboard.actions.leases")}
          </Link>
          <Link className="ghost-button dashboard-action-link" to="/notifications">
            {t("dashboard.actions.notifications")}
          </Link>
        </div>
      </article>
    </section>
  );
}
