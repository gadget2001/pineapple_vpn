from alembic import op
import sqlalchemy as sa


revision = "0012_v2raytun_ios"
down_revision = "0011_vpn_profile_meta"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("vpn_profiles", sa.Column("subscription_url_v2raytun", sa.String(length=512), nullable=True))
    op.execute(
        """
        UPDATE vpn_profiles
        SET subscription_url_v2raytun = COALESCE(subscription_url_hiddify, subscription_url_clash, subscription_url)
        WHERE subscription_url_v2raytun IS NULL
        """
    )


def downgrade():
    op.drop_column("vpn_profiles", "subscription_url_v2raytun")

