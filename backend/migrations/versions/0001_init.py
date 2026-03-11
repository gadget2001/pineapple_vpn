from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("telegram_id", sa.Integer, nullable=False, unique=True, index=True),
        sa.Column("username", sa.String(length=64)),
        sa.Column("first_name", sa.String(length=64)),
        sa.Column("last_name", sa.String(length=64)),
        sa.Column("is_admin", sa.Boolean, server_default=sa.text("false")),
        sa.Column("referral_code", sa.String(length=32), nullable=False, unique=True),
        sa.Column("referred_by_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("trial_days", sa.Integer, server_default="3"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), index=True),
        sa.Column("plan", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("price_rub", sa.Integer, nullable=False),
        sa.Column("starts_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("ends_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), index=True),
        sa.Column("amount_rub", sa.Integer, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_payment_id", sa.String(length=128)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("paid_at", sa.DateTime),
        sa.Column("meta", sa.JSON),
    )

    op.create_table(
        "referrals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("inviter_id", sa.Integer, sa.ForeignKey("users.id"), index=True),
        sa.Column("invitee_id", sa.Integer, sa.ForeignKey("users.id"), index=True),
        sa.Column("commission_percent", sa.Integer, server_default="10"),
        sa.Column("total_earned_rub", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "devices",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), index=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("last_seen_at", sa.DateTime),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("details", sa.JSON),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "vpn_profiles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), index=True),
        sa.Column("uuid", sa.String(length=64), nullable=False),
        sa.Column("vless_url", sa.String(length=512), nullable=False),
        sa.Column("subscription_url", sa.String(length=512), nullable=False),
        sa.Column("reality_public_key", sa.String(length=256)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "connection_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), index=True),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("connected_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("connection_logs")
    op.drop_table("vpn_profiles")
    op.drop_table("audit_logs")
    op.drop_table("devices")
    op.drop_table("referrals")
    op.drop_table("payments")
    op.drop_table("subscriptions")
    op.drop_table("users")
