from alembic import op
import sqlalchemy as sa

revision = "0002_wallet_trial"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("trial_activated_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("wallet_balance_rub", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("payments", sa.Column("kind", sa.String(length=32), nullable=False, server_default="topup"))


def downgrade():
    op.drop_column("payments", "kind")
    op.drop_column("users", "wallet_balance_rub")
    op.drop_column("users", "trial_activated_at")