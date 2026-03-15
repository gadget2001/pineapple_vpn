from alembic import op
import sqlalchemy as sa

revision = "0008_user_receipt_email"
down_revision = "0007_payment_provider_id_unique"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("receipt_email", sa.String(length=254), nullable=True))


def downgrade():
    op.drop_column("users", "receipt_email")
