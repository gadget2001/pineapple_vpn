from alembic import op
import sqlalchemy as sa

revision = "0003_users_telegram_id_bigint"
down_revision = "0002_wallet_trial"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "users",
        "telegram_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )


def downgrade():
    op.alter_column(
        "users",
        "telegram_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )

