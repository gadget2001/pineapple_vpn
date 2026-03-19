from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

OnboardingStep = Literal[
    "welcome",
    "trial_offer",
    "device_select",
    "install_app",
    "get_config",
    "complete",
    "done",
]

DeviceOS = Literal["windows", "iphone", "android", "macos", "linux"]
ClientType = Literal["clash", "v2raytun"]


class OnboardingStateOut(BaseModel):
    step: OnboardingStep
    step_index: int = Field(ge=1)
    total_steps: int = Field(default=6, ge=1)
    terms_accepted: bool
    terms_accepted_at: datetime | None
    legal_docs_version_current: str
    legal_docs_version_accepted: str | None
    trial_available: bool
    trial_activated_at: datetime | None
    trial_days: int
    os: DeviceOS | None
    install_confirmed: bool
    has_active_subscription: bool
    vpn_ready: bool
    completed: bool
    onboarding_completed_at: datetime | None


class AcceptTermsRequest(BaseModel):
    accepted: bool
    docs_version: str | None = None


class SelectDeviceRequest(BaseModel):
    os: DeviceOS


class InstructionConfirmRequest(BaseModel):
    os: DeviceOS | None = None


class OnboardingInstructionOut(BaseModel):
    os: DeviceOS
    app_name: str
    client_type: ClientType
    download_url: str
    install_cta: str
    steps: list[str]


class OnboardingConfigOut(BaseModel):
    platform: DeviceOS
    client_type: ClientType
    client_name: str
    profile_reused: bool
    message: str
    display_title: str
    display_subtitle: str
    subscription_url: str
    subscription_url_clash: str
    subscription_url_v2raytun: str
    raw_vless_url: str
    install_url: str
    install_urls: dict[str, str]
    import_help: str


class TrialActivationOut(BaseModel):
    status: str
    ends_at: datetime
    trial_days: int

