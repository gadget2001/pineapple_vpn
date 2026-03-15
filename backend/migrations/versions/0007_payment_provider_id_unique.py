from alembic import op
import sqlalchemy as sa

revision = "0007_payment_provider_id_unique"
down_revision = "0006_legal_docs_version"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_payments_provider_payment_id_unique",
        "payments",
        ["provider_payment_id"],
        unique=True,
        postgresql_where=sa.text("provider_payment_id IS NOT NULL"),
    )


def downgrade():
    op.drop_index("ix_payments_provider_payment_id_unique", table_name="payments")
