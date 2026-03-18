from alembic import op
import sqlalchemy as sa

revision = "0011_vpn_profile_meta"
down_revision = "0010_vpn_limits_and_access_logs"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("vpn_profiles", sa.Column("profile_name", sa.String(length=128), nullable=True))
    op.add_column("vpn_profiles", sa.Column("profile_group", sa.String(length=128), nullable=True))
    op.add_column("vpn_profiles", sa.Column("device_family", sa.String(length=32), nullable=True))
    op.add_column("vpn_profiles", sa.Column("client_type", sa.String(length=32), nullable=True))
    op.add_column("vpn_profiles", sa.Column("display_title", sa.String(length=128), nullable=True))
    op.add_column("vpn_profiles", sa.Column("display_subtitle", sa.String(length=128), nullable=True))

    op.add_column("vpn_profiles", sa.Column("subscription_url_clash", sa.String(length=512), nullable=True))
    op.add_column("vpn_profiles", sa.Column("subscription_url_hiddify", sa.String(length=512), nullable=True))
    op.add_column("vpn_profiles", sa.Column("raw_vless_url", sa.String(length=512), nullable=True))

    op.add_column("vpn_profiles", sa.Column("server_host", sa.String(length=255), nullable=True))
    op.add_column("vpn_profiles", sa.Column("server_port", sa.Integer(), nullable=True))
    op.add_column("vpn_profiles", sa.Column("transport_type", sa.String(length=32), nullable=True))
    op.add_column("vpn_profiles", sa.Column("security_type", sa.String(length=32), nullable=True))
    op.add_column("vpn_profiles", sa.Column("reality_short_id", sa.String(length=64), nullable=True))
    op.add_column("vpn_profiles", sa.Column("reality_sni", sa.String(length=255), nullable=True))

    op.add_column("vpn_profiles", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("vpn_profiles", sa.Column("last_synced_at", sa.DateTime(), nullable=True))
    op.add_column("vpn_profiles", sa.Column("config_version", sa.Integer(), nullable=False, server_default="1"))

    op.add_column("vpn_profiles", sa.Column("last_selected_platform", sa.String(length=32), nullable=True))
    op.add_column("vpn_profiles", sa.Column("issued_platforms", sa.JSON(), nullable=True))
    op.add_column("vpn_profiles", sa.Column("reinstall_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("vpn_profiles", sa.Column("last_config_issued_at", sa.DateTime(), nullable=True))
    op.add_column("vpn_profiles", sa.Column("last_device_flow_at", sa.DateTime(), nullable=True))

    op.add_column("vpn_profiles", sa.Column("install_url_windows", sa.String(length=512), nullable=True))
    op.add_column("vpn_profiles", sa.Column("install_url_android", sa.String(length=512), nullable=True))
    op.add_column("vpn_profiles", sa.Column("install_url_ios", sa.String(length=512), nullable=True))
    op.add_column("vpn_profiles", sa.Column("install_url_macos", sa.String(length=512), nullable=True))
    op.add_column("vpn_profiles", sa.Column("install_url_linux", sa.String(length=512), nullable=True))
    op.add_column("vpn_profiles", sa.Column("last_install_link_generated_at", sa.DateTime(), nullable=True))
    op.add_column("vpn_profiles", sa.Column("install_link_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("vpn_profiles", sa.Column("last_install_platform", sa.String(length=32), nullable=True))
    op.add_column("vpn_profiles", sa.Column("last_install_opened_at", sa.DateTime(), nullable=True))

    op.execute("UPDATE vpn_profiles SET raw_vless_url = vless_url WHERE raw_vless_url IS NULL")
    op.execute("UPDATE vpn_profiles SET subscription_url_clash = subscription_url WHERE subscription_url_clash IS NULL")
    op.execute("UPDATE vpn_profiles SET profile_name = 'Pineapple VPN' WHERE profile_name IS NULL")
    op.execute("UPDATE vpn_profiles SET profile_group = 'Pineapple' WHERE profile_group IS NULL")
    op.execute("UPDATE vpn_profiles SET display_title = 'Pineapple VPN' WHERE display_title IS NULL")
    op.execute("UPDATE vpn_profiles SET display_subtitle = 'Premium RU' WHERE display_subtitle IS NULL")
    op.execute("UPDATE vpn_profiles SET issued_platforms = '[]'::json WHERE issued_platforms IS NULL")
    op.execute("UPDATE vpn_profiles SET last_synced_at = created_at WHERE last_synced_at IS NULL")

    op.alter_column("vpn_profiles", "is_active", server_default=None)
    op.alter_column("vpn_profiles", "config_version", server_default=None)
    op.alter_column("vpn_profiles", "reinstall_count", server_default=None)
    op.alter_column("vpn_profiles", "install_link_version", server_default=None)


def downgrade():
    op.drop_column("vpn_profiles", "last_install_opened_at")
    op.drop_column("vpn_profiles", "last_install_platform")
    op.drop_column("vpn_profiles", "install_link_version")
    op.drop_column("vpn_profiles", "last_install_link_generated_at")
    op.drop_column("vpn_profiles", "install_url_linux")
    op.drop_column("vpn_profiles", "install_url_macos")
    op.drop_column("vpn_profiles", "install_url_ios")
    op.drop_column("vpn_profiles", "install_url_android")
    op.drop_column("vpn_profiles", "install_url_windows")

    op.drop_column("vpn_profiles", "last_device_flow_at")
    op.drop_column("vpn_profiles", "last_config_issued_at")
    op.drop_column("vpn_profiles", "reinstall_count")
    op.drop_column("vpn_profiles", "issued_platforms")
    op.drop_column("vpn_profiles", "last_selected_platform")

    op.drop_column("vpn_profiles", "config_version")
    op.drop_column("vpn_profiles", "last_synced_at")
    op.drop_column("vpn_profiles", "is_active")

    op.drop_column("vpn_profiles", "reality_sni")
    op.drop_column("vpn_profiles", "reality_short_id")
    op.drop_column("vpn_profiles", "security_type")
    op.drop_column("vpn_profiles", "transport_type")
    op.drop_column("vpn_profiles", "server_port")
    op.drop_column("vpn_profiles", "server_host")

    op.drop_column("vpn_profiles", "raw_vless_url")
    op.drop_column("vpn_profiles", "subscription_url_hiddify")
    op.drop_column("vpn_profiles", "subscription_url_clash")

    op.drop_column("vpn_profiles", "display_subtitle")
    op.drop_column("vpn_profiles", "display_title")
    op.drop_column("vpn_profiles", "client_type")
    op.drop_column("vpn_profiles", "device_family")
    op.drop_column("vpn_profiles", "profile_group")
    op.drop_column("vpn_profiles", "profile_name")

