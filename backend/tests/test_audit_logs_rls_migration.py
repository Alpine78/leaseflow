from __future__ import annotations

from pathlib import Path


def test_audit_logs_rls_migration_enables_force_rls_and_fail_closed_policy() -> None:
    migration = Path("migrations/versions/20260513_0011_add_audit_logs_rls.py")

    source = migration.read_text(encoding="utf-8")

    assert "ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY" in source
    assert "ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY" in source
    assert "CREATE POLICY audit_logs_tenant_isolation" in source
    assert "USING (tenant_id = current_setting('app.tenant_id', true))" in source
    assert "WITH CHECK (tenant_id = current_setting('app.tenant_id', true))" in source
    assert "ALTER TABLE audit_logs NO FORCE ROW LEVEL SECURITY" in source
    assert "ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY" in source
