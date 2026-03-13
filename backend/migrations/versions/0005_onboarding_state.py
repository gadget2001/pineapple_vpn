from alembic import op
import sqlalchemy as sa

revision = "0005_onboarding_state"
down_revision = "0004_user_consent_onboarding"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("onboarding_step", sa.String(length=32), nullable=False, server_default="welcome"))
    op.add_column("users", sa.Column("onboarding_install_confirmed_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("onboarding_completed_at", sa.DateTime(), nullable=True))

    op.alter_column("users", "onboarding_step", server_default=None)


def downgrade():
    op.drop_column("users", "onboarding_completed_at")
    op.drop_column("users", "onboarding_install_confirmed_at")
    op.drop_column("users", "onboarding_step")
