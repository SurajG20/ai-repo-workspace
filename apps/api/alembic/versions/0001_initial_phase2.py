"""Phase 2: Repository ingestion core tables

Revision ID: 0001
Revises:
Create Date: 2026-05-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROVIDER_TYPES = ("github", "gitlab", "local", "gitea", "bitbucket")
REPO_STATUSES = ("pending", "cloning", "active", "indexing", "error", "archived")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\"")

    _safe_create_enum("provider_type", PROVIDER_TYPES)
    _safe_create_enum("repo_status", REPO_STATUSES)
    _safe_create_enum("job_status", ("queued", "running", "completed", "failed", "cancelled"))
    _safe_create_enum("job_type", (
        "clone", "sync", "parse", "graph_sync", "embed", "vector_sync",
        "dead_code", "pr_analysis", "onboarding_gen", "snapshot",
    ))
    _safe_create_enum("event_type", ("push", "pull_request", "pull_request_review", "create", "delete", "repository"))

    _create_users()
    _create_repositories()
    _create_repository_languages()
    _create_repository_snapshots()
    _create_repository_files()
    _create_indexing_workflows()
    _create_indexing_jobs()
    _create_indexing_errors()
    _create_worker_heartbeats()
    _create_webhook_events()


def downgrade() -> None:
    op.drop_table("webhook_events")
    op.drop_table("worker_heartbeats")
    op.drop_table("indexing_errors")
    op.drop_table("indexing_jobs")
    op.drop_table("indexing_workflows")
    op.drop_table("repository_files")
    op.drop_table("repository_snapshots")
    op.drop_table("repository_languages")
    op.drop_table("repositories")
    op.drop_table("users")

    for name in ("event_type", "job_type", "job_status", "repo_status", "provider_type"):
        op.execute(f"DROP TYPE IF EXISTS {name}")


def _safe_create_enum(name: str, values: tuple[str, ...]) -> None:
    vals = ", ".join(f"'{v}'" for v in values)
    op.execute(f"DO $$ BEGIN CREATE TYPE {name} AS ENUM ({vals}); EXCEPTION WHEN duplicate_object THEN NULL; END $$;")


def _create_users() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider", sa.String(32), nullable=False, server_default="github"),
        sa.Column("provider_id", sa.String(64), nullable=False),
        sa.Column("login", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("email", sa.String(255)),
        sa.Column("avatar_url", sa.Text),
        sa.Column("access_token", postgresql.BYTEA),
        sa.Column("token_expires", sa.DateTime(timezone=True)),
        sa.Column("refresh_token", postgresql.BYTEA),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"], postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_unique_constraint("uq_users_provider", "users", ["provider", "provider_id"])
    op.create_unique_constraint("uq_users_login", "users", ["login"])


def _create_repositories() -> None:
    op.create_table(
        "repositories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default="github"),
        sa.Column("provider_id", sa.String(64)),
        sa.Column("full_name", sa.String(512), nullable=False),
        sa.Column("clone_url", sa.Text),
        sa.Column("local_path", sa.Text, nullable=False),
        sa.Column("default_branch", sa.String(255), server_default="main"),
        sa.Column("language", sa.String(64)),
        sa.Column("description", sa.Text),
        sa.Column("is_private", sa.Boolean, server_default=sa.text("false")),
        sa.Column("size_bytes", sa.BigInteger, server_default=sa.text("0")),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("last_synced_sha", sa.String(40)),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_repos_owner", "repositories", ["owner_id"], postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("ix_repos_status", "repositories", ["status"], postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("ix_repos_provider", "repositories", ["provider", "provider_id"], postgresql_where=sa.text("provider_id IS NOT NULL"))
    op.create_unique_constraint("uq_repos_full_name", "repositories", ["owner_id", "full_name"])


def _create_repository_languages() -> None:
    op.create_table(
        "repository_languages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("language", sa.String(64), nullable=False),
        sa.Column("percentage", sa.Float, server_default=sa.text("0.0")),
    )
    op.create_index("ix_repo_langs_repo", "repository_languages", ["repository_id"])


def _create_repository_snapshots() -> None:
    op.create_table(
        "repository_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("commit_sha", sa.String(40), nullable=False),
        sa.Column("branch", sa.String(255), server_default="main"),
        sa.Column("parent_shas", postgresql.ARRAY(sa.Text), server_default=sa.text("'{}'::text[]")),
        sa.Column("file_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("total_size_bytes", sa.BigInteger, server_default=sa.text("0")),
        sa.Column("files_added", sa.Integer, server_default=sa.text("0")),
        sa.Column("files_removed", sa.Integer, server_default=sa.text("0")),
        sa.Column("files_modified", sa.Integer, server_default=sa.text("0")),
        sa.Column("symbols_added", sa.Integer, server_default=sa.text("0")),
        sa.Column("symbols_removed", sa.Integer, server_default=sa.text("0")),
        sa.Column("indexed", sa.Boolean, server_default=sa.text("false")),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_snapshots_commit", "repository_snapshots", ["repository_id", "commit_sha"])
    op.create_index("ix_snapshots_repo", "repository_snapshots", [sa.text("repository_id, created_at DESC")])
    op.create_index("ix_snapshots_indexed", "repository_snapshots", ["indexed"], postgresql_where=sa.text("NOT indexed"))


def _create_repository_files() -> None:
    op.create_table(
        "repository_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("path", sa.Text, nullable=False),
        sa.Column("file_type", sa.String(32), server_default="unknown"),
        sa.Column("language", sa.String(64)),
        sa.Column("module_path", sa.Text),
        sa.Column("package_name", sa.String(255)),
        sa.Column("last_sha", sa.String(64)),
        sa.Column("last_parsed_at", sa.DateTime(timezone=True)),
        sa.Column("last_changed_snapshot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repository_snapshots.id")),
        sa.Column("is_deleted", sa.Boolean, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_files_path", "repository_files", ["repository_id", "path"])
    op.create_index("ix_files_language", "repository_files", ["repository_id", "language"], postgresql_where=sa.text("NOT is_deleted"))
    op.create_index("ix_files_unparsed", "repository_files", ["repository_id", "last_parsed_at"],
                    postgresql_where=sa.text("NOT is_deleted AND (last_parsed_at IS NULL OR updated_at > last_parsed_at)"))


def _create_indexing_workflows() -> None:
    op.create_table(
        "indexing_workflows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("workflow_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), server_default="queued"),
        sa.Column("total_steps", sa.SmallInteger, server_default=sa.text("0")),
        sa.Column("completed_steps", sa.SmallInteger, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_workflows_repo", "indexing_workflows", [sa.text("repository_id, created_at DESC")])


def _create_indexing_jobs() -> None:
    op.create_table(
        "indexing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repository_snapshots.id")),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("indexing_workflows.id")),
        sa.Column("job_type", sa.String(32), nullable=False),
        sa.Column("parent_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("indexing_jobs.id")),
        sa.Column("status", sa.String(32), server_default="queued"),
        sa.Column("priority", sa.SmallInteger, server_default=sa.text("0")),
        sa.Column("progress", sa.Float, server_default=sa.text("0.0")),
        sa.Column("total_files", sa.Integer),
        sa.Column("processed_files", sa.Integer, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text),
        sa.Column("retry_count", sa.SmallInteger, server_default=sa.text("0")),
        sa.Column("max_retries", sa.SmallInteger, server_default=sa.text("3")),
        sa.Column("locked_by", sa.String(128)),
        sa.Column("locked_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("celery_task_id", sa.String(128)),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_jobs_status", "indexing_jobs", ["status"], postgresql_where=sa.text("status IN ('queued', 'running')"))
    op.create_index("ix_jobs_repo", "indexing_jobs", [sa.text("repository_id, created_at DESC")])
    op.create_index("ix_jobs_type", "indexing_jobs", ["job_type", "status"])
    op.create_index("ix_jobs_locked", "indexing_jobs", ["locked_by"], postgresql_where=sa.text("locked_by IS NOT NULL"))
    op.create_index("ix_jobs_parent", "indexing_jobs", ["parent_job_id"])


def _create_indexing_errors() -> None:
    op.create_table(
        "indexing_errors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("indexing_jobs.id"), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repository_files.id")),
        sa.Column("error_type", sa.String(64), nullable=False),
        sa.Column("error_message", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_errors_job", "indexing_errors", ["job_id"])


def _create_worker_heartbeats() -> None:
    op.create_table(
        "worker_heartbeats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("worker_id", sa.String(128), nullable=False),
        sa.Column("current_job_id", postgresql.UUID(as_uuid=True)),
        sa.Column("status", sa.String(32), server_default="idle"),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_worker_id", "worker_heartbeats", ["worker_id"])


def _create_webhook_events() -> None:
    op.create_table(
        "webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(128)),
        sa.Column("signature_valid", sa.Boolean),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("payload_size_bytes", sa.Integer, server_default=sa.text("0")),
        sa.Column("processed", sa.Boolean, server_default=sa.text("false")),
        sa.Column("processing_job_id", postgresql.UUID(as_uuid=True)),
        sa.Column("error_message", sa.Text),
        sa.Column("replay_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("last_replayed_at", sa.DateTime(timezone=True)),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_webhook_idempotency", "webhook_events", ["provider", "idempotency_key"])
    op.create_index("ix_webhook_idempotency_partial", "webhook_events", ["provider", "idempotency_key"],
                    unique=True, postgresql_where=sa.text("idempotency_key IS NOT NULL"))
    op.create_index("ix_webhook_repo", "webhook_events", [sa.text("repository_id, created_at DESC")])
    op.create_index("ix_webhook_unprocessed", "webhook_events", ["processed"], postgresql_where=sa.text("NOT processed"))
