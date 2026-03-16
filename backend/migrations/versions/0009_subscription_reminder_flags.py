from alembic import op
import sqlalchemy as sa

revision = "0009_subscription_reminder_flags"
down_revision = "0008_user_receipt_email"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("subscriptions", sa.Column("reminder_24h_sent_at", sa.DateTime(), nullable=True))
    op.add_column("subscriptions", sa.Column("reminder_1h_sent_at", sa.DateTime(), nullable=True))
    op.add_column("subscriptions", sa.Column("expired_user_notified_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("subscriptions", "expired_user_notified_at")
    op.drop_column("subscriptions", "reminder_1h_sent_at")
    op.drop_column("subscriptions", "reminder_24h_sent_at")
