from alembic import op
import sqlalchemy as sa

revision = "0006_legal_docs_version"
down_revision = "0005_onboarding_state"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("legal_docs_version_accepted", sa.String(length=32), nullable=True))


def downgrade():
    op.drop_column("users", "legal_docs_version_accepted")
