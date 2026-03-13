from alembic import op
import sqlalchemy as sa

revision = "0004_user_consent_onboarding"
down_revision = "0003_users_telegram_id_bigint"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("terms_accepted_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("onboarding_os", sa.String(length=32), nullable=True))


def downgrade():
    op.drop_column("users", "onboarding_os")
    op.drop_column("users", "terms_accepted_at")
