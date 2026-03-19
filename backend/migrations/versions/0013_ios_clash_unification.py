from alembic import op


revision = "0013_ios_clash_unification"
down_revision = "0012_v2raytun_ios"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE vpn_profiles DROP COLUMN IF EXISTS subscription_url_v2raytun")


def downgrade():
    op.execute("ALTER TABLE vpn_profiles ADD COLUMN IF NOT EXISTS subscription_url_v2raytun VARCHAR(512)")

