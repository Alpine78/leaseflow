import { Link } from "react-router-dom";
import { useDashboardPageState } from "../features/dashboard/useDashboardPage";

type SummaryCardProps = {
  count: number;
  label: string;
  supportingText: string;
};

function SummaryCard({ count, label, supportingText }: SummaryCardProps) {
  return (
    <article className="summary-card">
      <p className="summary-count">
        {count} {label}
      </p>
      <p className="resource-subtitle">{supportingText}</p>
    </article>
  );
}

export function DashboardPage() {
  const { error, isLoading, summary } = useDashboardPageState();

  return (
    <section className="dashboard-layout">
      <article className="panel-card">
        <div className="section-heading">
          <p className="eyebrow">Dashboard</p>
          <h2 className="section-title">Portfolio overview</h2>
        </div>
        {isLoading ? (
          <p className="supporting-copy">Loading dashboard...</p>
        ) : (
          <div className="summary-grid">
            <SummaryCard
              count={summary.propertyCount}
              label="properties"
              supportingText="Tenant-owned rental units currently captured."
            />
            <SummaryCard
              count={summary.leaseCount}
              label="leases"
              supportingText="Active lease records linked to properties."
            />
            <SummaryCard
              count={summary.dueReminderCount}
              label="due soon"
              supportingText="Lease reminder candidates in the default window."
            />
            <SummaryCard
              count={summary.unreadNotificationCount}
              label="unread"
              supportingText="Persisted notifications still awaiting acknowledgement."
            />
          </div>
        )}
        {error ? <p className="error-text">{error}</p> : null}
      </article>

      <article className="panel-card">
        <div className="section-heading">
          <p className="eyebrow">Next actions</p>
          <h2 className="section-title">Open the working areas.</h2>
        </div>
        <div className="dashboard-actions">
          <Link className="primary-button dashboard-action-link" to="/properties">
            Manage properties
          </Link>
          <Link className="ghost-button dashboard-action-link" to="/leases">
            Manage leases
          </Link>
          <Link className="ghost-button dashboard-action-link" to="/notifications">
            Review notifications
          </Link>
        </div>
      </article>
    </section>
  );
}
