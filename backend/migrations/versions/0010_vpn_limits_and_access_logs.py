from alembic import op
import sqlalchemy as sa

revision = "0010_vpn_limits_and_access_logs"
down_revision = "0009_subscription_reminder_flags"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("connection_logs", "user_id", existing_type=sa.Integer(), nullable=True)

    op.add_column("connection_logs", sa.Column("telegram_id", sa.BigInteger(), nullable=True))
    op.add_column("connection_logs", sa.Column("panel_username", sa.String(length=64), nullable=True))
    op.add_column("connection_logs", sa.Column("source_path", sa.String(length=512), nullable=True))
    op.add_column("connection_logs", sa.Column("source_offset", sa.BigInteger(), nullable=True))
    op.add_column("connection_logs", sa.Column("event_hash", sa.String(length=64), nullable=True))
    op.add_column("connection_logs", sa.Column("raw_event", sa.Text(), nullable=True))
    op.add_column("connection_logs", sa.Column("created_at", sa.DateTime(), nullable=True))

    op.create_index("ix_connection_logs_telegram_id", "connection_logs", ["telegram_id"], unique=False)
    op.create_index("ix_connection_logs_panel_username", "connection_logs", ["panel_username"], unique=False)
    op.create_index("ix_connection_logs_connected_at", "connection_logs", ["connected_at"], unique=False)
    op.create_index("ix_connection_logs_event_hash", "connection_logs", ["event_hash"], unique=True)

    op.execute("UPDATE connection_logs SET created_at = connected_at WHERE created_at IS NULL")
    op.alter_column("connection_logs", "created_at", nullable=False)

    op.create_table(
        "ingestion_cursors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cursor_key", sa.String(length=64), nullable=False),
        sa.Column("source_path", sa.String(length=512), nullable=False),
        sa.Column("inode", sa.String(length=128), nullable=True),
        sa.Column("offset", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingestion_cursors_cursor_key", "ingestion_cursors", ["cursor_key"], unique=True)


def downgrade():
    op.drop_index("ix_ingestion_cursors_cursor_key", table_name="ingestion_cursors")
    op.drop_table("ingestion_cursors")

    op.drop_index("ix_connection_logs_event_hash", table_name="connection_logs")
    op.drop_index("ix_connection_logs_connected_at", table_name="connection_logs")
    op.drop_index("ix_connection_logs_panel_username", table_name="connection_logs")
    op.drop_index("ix_connection_logs_telegram_id", table_name="connection_logs")

    op.drop_column("connection_logs", "created_at")
    op.drop_column("connection_logs", "raw_event")
    op.drop_column("connection_logs", "event_hash")
    op.drop_column("connection_logs", "source_offset")
    op.drop_column("connection_logs", "source_path")
    op.drop_column("connection_logs", "panel_username")
    op.drop_column("connection_logs", "telegram_id")

    op.alter_column("connection_logs", "user_id", existing_type=sa.Integer(), nullable=False)
