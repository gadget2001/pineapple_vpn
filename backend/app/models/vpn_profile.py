from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VPNProfile(Base):
    __tablename__ = "vpn_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    uuid: Mapped[str] = mapped_column(String(64))
    vless_url: Mapped[str] = mapped_column(String(512))
    subscription_url: Mapped[str] = mapped_column(String(512))

    profile_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    profile_group: Mapped[str | None] = mapped_column(String(128), nullable=True)
    device_family: Mapped[str | None] = mapped_column(String(32), nullable=True)
    client_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    display_title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    display_subtitle: Mapped[str | None] = mapped_column(String(128), nullable=True)

    subscription_url_clash: Mapped[str | None] = mapped_column(String(512), nullable=True)
    subscription_url_hiddify: Mapped[str | None] = mapped_column(String(512), nullable=True)
    raw_vless_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    server_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    server_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transport_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    security_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reality_public_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    reality_short_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reality_sni: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    config_version: Mapped[int] = mapped_column(Integer, default=1)

    last_selected_platform: Mapped[str | None] = mapped_column(String(32), nullable=True)
    issued_platforms: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    reinstall_count: Mapped[int] = mapped_column(Integer, default=0)
    last_config_issued_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_device_flow_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    install_url_windows: Mapped[str | None] = mapped_column(String(512), nullable=True)
    install_url_android: Mapped[str | None] = mapped_column(String(512), nullable=True)
    install_url_ios: Mapped[str | None] = mapped_column(String(512), nullable=True)
    install_url_macos: Mapped[str | None] = mapped_column(String(512), nullable=True)
    install_url_linux: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_install_link_generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    install_link_version: Mapped[int] = mapped_column(Integer, default=1)
    last_install_platform: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_install_opened_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="vpn_profile")

